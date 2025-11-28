#!/usr/bin/env python3
"""
Batch Generation Example for Qwen Image 8-Step Generation
Optimized for high-volume image generation with parallel processing
"""

import requests
import json
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import csv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class BatchConfig:
    """Configuration for batch generation"""
    prompts_file: str
    output_dir: str = "batch_output"
    max_workers: int = 3  # Parallel generations
    timeout: int = 120
    base_url: str = "http://localhost:8188"
    save_metadata: bool = True
    retry_failed: bool = True

class BatchGenerator:
    """High-performance batch image generator"""

    def __init__(self, config: BatchConfig):
        self.config = config
        self.session = requests.Session()
        self.results = []
        self.stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "total_time": 0,
            "start_time": None,
            "end_time": None
        }

        # Create output directory
        os.makedirs(config.output_dir, exist_ok=True)

    def load_prompts(self, prompts_file: str) -> List[Tuple[str, int]]:
        """Load prompts from file with optional seeds"""
        prompts = []

        try:
            with open(prompts_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):  # Skip empty lines and comments
                        # Parse prompt and optional seed (format: "prompt|seed")
                        parts = line.split('|')
                        prompt = parts[0].strip()
                        seed = int(parts[1].strip()) if len(parts) > 1 else None
                        prompts.append((prompt, seed))

            logger.info(f"Loaded {len(prompts)} prompts from {prompts_file}")
            return prompts

        except FileNotFoundError:
            logger.error(f"Prompts file {prompts_file} not found")
            return []
        except Exception as e:
            logger.error(f"Error loading prompts: {e}")
            return []

    def load_workflow(self) -> Optional[Dict]:
        """Load the ComfyUI workflow"""
        try:
            with open("../example-request.json", 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading workflow: {e}")
            return None

    def generate_single(self, prompt_data: Tuple[str, int], index: int) -> Dict:
        """Generate a single image"""
        prompt, seed = prompt_data
        start_time = time.time()

        result = {
            "index": index,
            "prompt": prompt,
            "seed": seed,
            "success": False,
            "filename": None,
            "generation_time": 0,
            "error": None
        }

        try:
            # Load workflow
            workflow = self.load_workflow()
            if not workflow:
                result["error"] = "Failed to load workflow"
                return result

            # Prepare workflow
            workflow["input"]["workflow"]["6"]["inputs"]["text"] = prompt
            if seed:
                workflow["input"]["workflow"]["3"]["inputs"]["seed"] = seed

            # Submit generation
            response = self.session.post(
                f"{self.config.base_url}/prompt",
                json=workflow,
                timeout=10
            )

            if response.status_code != 200:
                result["error"] = f"Submit failed: {response.status_code}"
                return result

            prompt_id = response.json()["prompt_id"]

            # Wait for completion
            generation_start = time.time()
            while time.time() - generation_start < self.config.timeout:
                history_response = self.session.get(
                    f"{self.config.base_url}/history/{prompt_id}",
                    timeout=5
                )

                if history_response.status_code == 200:
                    history = history_response.json()
                    if prompt_id in history:
                        outputs = history[prompt_id].get("outputs", {})

                        # Extract image info
                        for node_id, node_output in outputs.items():
                            if "images" in node_output:
                                images = node_output["images"]
                                if images:
                                    image_info = images[0]  # Take first image
                                    filename = image_info["filename"]

                                    result.update({
                                        "success": True,
                                        "filename": filename,
                                        "generation_time": time.time() - start_time,
                                        "prompt_id": prompt_id
                                    })

                                    logger.info(f"✅ [{index}] {prompt[:50]}... -> {filename}")
                                    return result

                time.sleep(1)

            result["error"] = "Generation timeout"
            logger.warning(f"⏰ [{index}] Timeout for: {prompt[:50]}...")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"❌ [{index}] Error: {e}")

        return result

    def run_batch(self, prompts: List[Tuple[str, int]]) -> List[Dict]:
        """Run batch generation with parallel processing"""
        logger.info(f"Starting batch generation of {len(prompts)} images")
        logger.info(f"Using {self.config.max_workers} parallel workers")

        self.stats["start_time"] = datetime.now()
        self.stats["total"] = len(prompts)

        # Process prompts in parallel
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all tasks
            future_to_index = {
                executor.submit(self.generate_single, prompt_data, i): i
                for i, prompt_data in enumerate(prompts)
            }

            # Collect results as they complete
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    self.results.append(result)

                    if result["success"]:
                        self.stats["successful"] += 1
                    else:
                        self.stats["failed"] += 1

                except Exception as e:
                    logger.error(f"Future {index} failed: {e}")
                    self.stats["failed"] += 1

        self.stats["end_time"] = datetime.now()
        self.stats["total_time"] = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()

        return self.results

    def save_results(self):
        """Save batch results and metadata"""
        if not self.config.save_metadata:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save detailed results as JSON
        results_file = os.path.join(self.config.output_dir, f"batch_results_{timestamp}.json")
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                "config": {
                    "total_prompts": self.stats["total"],
                    "max_workers": self.config.max_workers,
                    "timeout": self.config.timeout
                },
                "statistics": self.stats,
                "results": self.results
            }, f, indent=2, ensure_ascii=False)

        # Save CSV summary
        csv_file = os.path.join(self.config.output_dir, f"batch_summary_{timestamp}.csv")
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Index", "Success", "Prompt", "Seed", "Filename",
                "Generation_Time", "Error"
            ])

            for result in self.results:
                writer.writerow([
                    result["index"],
                    result["success"],
                    result["prompt"],
                    result.get("seed", ""),
                    result.get("filename", ""),
                    f"{result.get('generation_time', 0):.2f}",
                    result.get("error", "")
                ])

        logger.info(f"💾 Results saved to {results_file} and {csv_file}")

    def print_summary(self):
        """Print batch generation summary"""
        print("\n" + "=" * 60)
        print("BATCH GENERATION SUMMARY")
        print("=" * 60)

        print(f"📊 Statistics:")
        print(f"   Total Prompts:     {self.stats['total']}")
        print(f"   Successful:        {self.stats['successful']}")
        print(f"   Failed:           {self.stats['failed']}")
        print(f"   Success Rate:     {self.stats['successful']/self.stats['total']*100:.1f}%")
        print()

        print(f"⏱️  Timing:")
        print(f"   Start Time:       {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   End Time:         {self.stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Total Duration:   {self.stats['total_time']:.1f}s")
        print(f"   Avg per Image:    {self.stats['total_time']/self.stats['total']:.2f}s")
        print()

        if self.stats['successful'] > 0:
            successful_times = [r['generation_time'] for r in self.results if r['success']]
            import statistics
            print(f"📈 Generation Times (Successful):")
            print(f"   Average:          {statistics.mean(successful_times):.2f}s")
            print(f"   Median:           {statistics.median(successful_times):.2f}s")
            print(f"   Min:              {min(successful_times):.2f}s")
            print(f"   Max:              {max(successful_times):.2f}s")

        # Failed generations
        failed_results = [r for r in self.results if not r['success']]
        if failed_results:
            print(f"\n❌ Failed Generations ({len(failed_results)}):")
            for result in failed_results[:5]:  # Show first 5
                print(f"   [{result['index']}] {result['prompt'][:40]}... -> {result['error']}")
            if len(failed_results) > 5:
                print(f"   ... and {len(failed_results) - 5} more")

def create_sample_prompts():
    """Create a sample prompts file for testing"""
    sample_prompts = [
        "A serene mountain landscape at sunset with golden light filtering through clouds|1001",
        "A futuristic cyberpunk city with neon signs, flying cars, and towering skyscrapers|1002",
        "A traditional Japanese garden with cherry blossoms, a tea house, and a koi pond|1003",
        "A majestic dragon soaring through ancient mountains at dawn|1004",
        "A cozy library filled with ancient books, warm lighting, and comfortable reading chairs|1005",
        "A vibrant Hong Kong street scene with Chinese lanterns and busy market stalls|1006",
        "An underwater coral reef teeming with colorful tropical fish and marine life|1007",
        "A medieval castle on a hill with a wizard's tower and magical glow|1008",
        "A space station orbiting Earth with the planet visible in the background|1009",
        "A mystical forest with bioluminescent plants and ethereal creatures|1010"
    ]

    with open("sample_prompts.txt", "w", encoding="utf-8") as f:
        f.write("# Sample prompts for Qwen Image 8-Step batch generation\n")
        f.write("# Format: prompt|seed (seed is optional)\n\n")
        for prompt in sample_prompts:
            f.write(f"{prompt}\n")

    print("📝 Created sample_prompts.txt with example prompts")

def main():
    """Main batch generation example"""
    print("🚀 Qwen Image 8-Step Batch Generation")
    print("=" * 50)

    # Check if prompts file exists, create sample if not
    if not os.path.exists("sample_prompts.txt"):
        create_sample_prompts()
        print("\nEdit sample_prompts.txt with your own prompts, then run again.")
        return

    # Configuration
    config = BatchConfig(
        prompts_file="sample_prompts.txt",
        output_dir="batch_output",
        max_workers=3,
        timeout=120,
        save_metadata=True
    )

    # Initialize batch generator
    generator = BatchGenerator(config)

    # Load prompts
    prompts = generator.load_prompts(config.prompts_file)
    if not prompts:
        print("❌ No prompts loaded. Check the prompts file.")
        return

    print(f"📋 Loaded {len(prompts)} prompts for batch generation")

    # Health check
    try:
        response = requests.get(f"{config.base_url}/system_stats", timeout=5)
        if response.status_code != 200:
            print("❌ API is not responding. Please ensure ComfyUI is running.")
            return
        print("✅ API is healthy and ready")
    except:
        print("❌ Cannot connect to ComfyUI server")
        return

    # Run batch generation
    try:
        results = generator.run_batch(prompts)

        # Save results
        generator.save_results()

        # Print summary
        generator.print_summary()

    except KeyboardInterrupt:
        print("\n⏹️  Batch generation interrupted by user")
    except Exception as e:
        print(f"\n❌ Batch generation failed: {e}")

if __name__ == "__main__":
    main()