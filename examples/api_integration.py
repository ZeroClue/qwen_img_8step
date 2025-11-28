#!/usr/bin/env python3
"""
API Integration Example for Qwen Image 8-Step Generation
Advanced integration with error handling, retries, and batch processing
"""

import requests
import json
import time
import os
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class GenerationRequest:
    """Data class for generation requests"""
    prompt: str
    seed: Optional[int] = None
    width: int = 1328
    height: int = 1328
    steps: int = 8
    cfg_scale: float = 1.0
    batch_size: int = 1

@dataclass
class GenerationResult:
    """Data class for generation results"""
    success: bool
    prompt_id: Optional[str] = None
    generation_time: Optional[float] = None
    images: Optional[List[Dict]] = None
    error: Optional[str] = None

class QwenImageAPI:
    """Advanced API client for Qwen Image 8-Step Generation"""

    def __init__(
        self,
        base_url: str = "http://localhost:8188",
        timeout: int = 60,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = requests.Session()

        # Connection settings
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'QwenImageAPIClient/1.0'
        })

    def health_check(self) -> bool:
        """Check if the API is healthy and responsive"""
        try:
            response = self.session.get(
                f"{self.base_url}/system_stats",
                timeout=5
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def load_workflow(self, workflow_file: str = "../example-request.json") -> Optional[Dict]:
        """Load and validate the ComfyUI workflow"""
        try:
            with open(workflow_file, 'r') as f:
                workflow = json.load(f)

            # Validate workflow structure
            if "input" not in workflow or "workflow" not in workflow["input"]:
                raise ValueError("Invalid workflow structure")

            return workflow
        except FileNotFoundError:
            logger.error(f"Workflow file {workflow_file} not found")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in workflow file: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading workflow: {e}")
            return None

    def prepare_workflow(
        self,
        base_workflow: Dict,
        request: GenerationRequest
    ) -> Dict:
        """Prepare workflow with request parameters"""
        workflow = json.loads(json.dumps(base_workflow))  # Deep copy

        # Update prompt
        workflow["input"]["workflow"]["6"]["inputs"]["text"] = request.prompt

        # Update generation parameters
        workflow["input"]["workflow"]["3"]["inputs"].update({
            "seed": request.seed if request.seed else int(time.time() * 1000) % 2**32,
            "steps": request.steps,
            "cfg": request.cfg_scale
        })

        # Update image dimensions
        workflow["input"]["workflow"]["58"]["inputs"].update({
            "width": request.width,
            "height": request.height,
            "batch_size": request.batch_size
        })

        return workflow

    def submit_generation(self, workflow: Dict) -> Optional[str]:
        """Submit generation request with retry logic"""
        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    f"{self.base_url}/prompt",
                    json=workflow,
                    timeout=10
                )

                if response.status_code == 200:
                    return response.json()["prompt_id"]
                elif response.status_code == 429:  # Rate limited
                    logger.warning(f"Rate limited, retrying in {self.retry_delay}s...")
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"Submit failed: {response.status_code} - {response.text}")

            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))

        return None

    def wait_for_completion(self, prompt_id: str) -> GenerationResult:
        """Wait for generation completion with timeout"""
        start_time = time.time()

        while time.time() - start_time < self.timeout:
            try:
                response = self.session.get(
                    f"{self.base_url}/history/{prompt_id}",
                    timeout=5
                )

                if response.status_code == 200:
                    history = response.json()

                    if prompt_id in history:
                        generation_data = history[prompt_id]
                        outputs = generation_data.get("outputs", {})

                        # Extract image information
                        images = []
                        for node_id, node_output in outputs.items():
                            if "images" in node_output:
                                images.extend(node_output["images"])

                        generation_time = time.time() - start_time
                        return GenerationResult(
                            success=True,
                            prompt_id=prompt_id,
                            generation_time=generation_time,
                            images=images
                        )

                time.sleep(1)  # Poll every second

            except requests.exceptions.RequestException as e:
                logger.error(f"Error checking generation status: {e}")
                break

        return GenerationResult(
            success=False,
            prompt_id=prompt_id,
            generation_time=self.timeout,
            error="timeout"
        )

    def generate_image(self, request: GenerationRequest) -> GenerationResult:
        """Generate a single image with full error handling"""
        logger.info(f"Generating image: {request.prompt[:50]}...")

        # Load workflow
        workflow = self.load_workflow()
        if not workflow:
            return GenerationResult(
                success=False,
                error="Failed to load workflow"
            )

        # Prepare workflow
        prepared_workflow = self.prepare_workflow(workflow, request)

        # Submit generation
        prompt_id = self.submit_generation(prepared_workflow)
        if not prompt_id:
            return GenerationResult(
                success=False,
                error="Failed to submit generation request"
            )

        # Wait for completion
        logger.info(f"Generation submitted with ID: {prompt_id}")
        return self.wait_for_completion(prompt_id)

    def batch_generate(self, requests: List[GenerationRequest]) -> List[GenerationResult]:
        """Generate multiple images in sequence"""
        logger.info(f"Starting batch generation of {len(requests)} images")

        results = []
        for i, request in enumerate(requests, 1):
            logger.info(f"Processing request {i}/{len(requests)}")
            result = self.generate_image(request)
            results.append(result)

            # Small delay between requests to prevent overwhelming
            time.sleep(0.5)

        successful = sum(1 for r in results if r.success)
        logger.info(f"Batch completed: {successful}/{len(requests)} successful")

        return results

    def save_generation_info(self, result: GenerationResult, filename: str = None) -> str:
        """Save generation result information to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"generation_{timestamp}.json"

        result_data = {
            "success": result.success,
            "prompt_id": result.prompt_id,
            "generation_time": result.generation_time,
            "images": result.images,
            "error": result.error,
            "timestamp": datetime.now().isoformat()
        }

        with open(filename, 'w') as f:
            json.dump(result_data, f, indent=2)

        return filename

def main():
    """API integration example"""
    print("🔌 Qwen Image 8-Step API Integration Example")
    print("=" * 60)

    # Initialize API client
    api = QwenImageAPI()

    # Health check
    if not api.health_check():
        print("❌ API is not responding. Please ensure ComfyUI is running.")
        return

    print("✅ API is healthy and responsive")

    # Example 1: Single generation
    print("\n--- Single Generation Example ---")
    request = GenerationRequest(
        prompt="A majestic dragon soaring through ancient mountains at dawn",
        seed=12345,
        width=1024,
        height=1024
    )

    result = api.generate_image(request)

    if result.success:
        print(f"✅ Generated in {result.generation_time:.2f}s")
        if result.images:
            print(f"📁 {len(result.images)} image(s) generated")
            for img in result.images:
                print(f"   - {img['filename']}")

        # Save generation info
        info_file = api.save_generation_info(result)
        print(f"💾 Generation info saved to: {info_file}")
    else:
        print(f"❌ Generation failed: {result.error}")

    # Example 2: Batch generation
    print("\n--- Batch Generation Example ---")
    batch_requests = [
        GenerationRequest(
            prompt="A cyberpunk city street with neon signs and flying cars",
            seed=1001
        ),
        GenerationRequest(
            prompt="A serene Japanese garden with cherry blossoms and a tea house",
            seed=1002
        ),
        GenerationRequest(
            prompt="A futuristic space station with Earth in the background",
            seed=1003
        )
    ]

    batch_results = api.batch_generate(batch_requests)

    # Batch results summary
    successful = sum(1 for r in batch_results if r.success)
    total_time = sum(r.generation_time for r in batch_results if r.success)

    print(f"\n📊 Batch Summary:")
    print(f"   Successful: {successful}/{len(batch_results)}")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Average time: {total_time/successful:.2f}s per image" if successful > 0 else "   Average time: N/A")

    print("\n🎉 API integration example completed!")

if __name__ == "__main__":
    main()