#!/usr/bin/env python3
"""
Quality assessment script for Qwen Image 8-Step Generation
Tests output quality, consistency, and prompt adherence
"""

import json
import requests
import os
import time
from PIL import Image
import clip
import torch
import numpy as np
from datetime import datetime
import sys

class QualityBenchmark:
    def __init__(self, base_url="http://localhost:8188"):
        self.base_url = base_url
        self.results = {
            "clip_scores": [],
            "generation_times": [],
            "test_cases": [],
            "overall_quality": 0
        }

        # Initialize CLIP model for quality assessment
        try:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.clip_model, self.clip_preprocess = clip.load("ViT-B/32", device=self.device)
            print("CLIP model loaded for quality assessment")
        except Exception as e:
            print(f"Warning: Could not load CLIP model: {e}")
            self.clip_model = None

    def load_test_workflow(self, workflow_file="example-request.json"):
        """Load the test workflow JSON"""
        try:
            with open(workflow_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading workflow: {e}")
            return None

    def calculate_clip_score(self, image_path, prompt):
        """Calculate CLIP score for image-prompt alignment"""
        if not self.clip_model:
            return None

        try:
            # Load and preprocess image
            image = Image.open(image_path).convert("RGB")
            image_tensor = self.clip_preprocess(image).unsqueeze(0).to(self.device)

            # Tokenize prompt
            text_tokens = clip.tokenize([prompt]).to(self.device)

            # Get features
            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_tensor)
                text_features = self.clip_model.encode_text(text_tokens)

                # Calculate cosine similarity
                similarity = torch.cosine_similarity(image_features, text_features)
                return similarity.item()

        except Exception as e:
            print(f"Error calculating CLIP score: {e}")
            return None

    def submit_generation(self, workflow, prompt_text=None):
        """Submit a generation request to ComfyUI"""
        try:
            # Modify prompt if provided
            if prompt_text:
                workflow["input"]["workflow"]["6"]["inputs"]["text"] = prompt_text

            # Submit request
            response = requests.post(f"{self.base_url}/prompt", json=workflow)
            if response.status_code == 200:
                return response.json()["prompt_id"]
            else:
                print(f"Error submitting request: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error submitting generation: {e}")
            return None

    def get_generation_output(self, prompt_id, output_dir="outputs"):
        """Get generated image from ComfyUI output"""
        try:
            # Check generation status
            response = requests.get(f"{self.base_url}/history/{prompt_id}")
            if response.status_code == 200:
                history = response.json()
                if prompt_id in history:
                    outputs = history[prompt_id]["outputs"]

                    # Find the generated image
                    for node_id, node_output in outputs.items():
                        if "images" in node_output:
                            for image_info in node_output["images"]:
                                # Construct image path (adjust based on your ComfyUI setup)
                                image_path = f"{output_dir}/{image_info['filename']}"
                                if os.path.exists(image_path):
                                    return image_path
                                else:
                                    # Try alternative path
                                    alt_path = f"/comfyui/output/{image_info['filename']}"
                                    if os.path.exists(alt_path):
                                        return alt_path
            return None
        except Exception as e:
            print(f"Error getting generation output: {e}")
            return None

    def wait_for_generation(self, prompt_id, timeout=60):
        """Wait for generation to complete"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            response = requests.get(f"{self.base_url}/history/{prompt_id}")
            if response.status_code == 200:
                history = response.json()
                if prompt_id in history:
                    return True
            time.sleep(1)

        return False

    def run_quality_test(self, workflow, test_case):
        """Run a single quality test"""
        prompt = test_case["prompt"]
        expected_elements = test_case.get("expected_elements", [])

        print(f"Testing: {prompt[:50]}...", end=" ")

        # Submit generation
        start_time = time.time()
        prompt_id = self.submit_generation(workflow, prompt)

        if not prompt_id:
            return None

        # Wait for completion
        if not self.wait_for_generation(prompt_id):
            print("❌ Timeout")
            return None

        generation_time = time.time() - start_time

        # Get output image
        image_path = self.get_generation_output(prompt_id)
        if not image_path:
            print("❌ No output found")
            return None

        # Calculate CLIP score
        clip_score = self.calculate_clip_score(image_path, prompt)

        result = {
            "prompt": prompt,
            "image_path": image_path,
            "generation_time": generation_time,
            "clip_score": clip_score,
            "expected_elements": expected_elements,
            "success": True
        }

        if clip_score:
            print(f"✅ CLIP: {clip_score:.3f}")
        else:
            print("✅ Generated")

        return result

    def run_quality_suite(self):
        """Run comprehensive quality test suite"""
        print("Running Qwen Image 8-Step Quality Assessment")
        print("=" * 60)

        # Load test workflow
        workflow = self.load_test_workflow()
        if not workflow:
            print("Failed to load test workflow")
            return

        # Test cases with different prompts and expected elements
        test_cases = [
            {
                "prompt": "A serene mountain landscape at sunset with snow-capped peaks",
                "expected_elements": ["mountains", "sunset", "snow"]
            },
            {
                "prompt": "A futuristic city with flying cars and neon lights",
                "expected_elements": ["city", "cars", "neon"]
            },
            {
                "prompt": "A traditional Japanese garden with cherry blossoms in spring",
                "expected_elements": ["garden", "cherry blossoms", "japanese"]
            },
            {
                "prompt": "A cyberpunk street scene with rain and neon reflections",
                "expected_elements": ["cyberpunk", "rain", "neon"]
            },
            {
                "prompt": "A cozy library filled with ancient books and warm lighting",
                "expected_elements": ["library", "books", "warm lighting"]
            },
            {
                "prompt": "A vibrant Hong Kong street with Chinese signs and lanterns",
                "expected_elements": ["hong kong", "chinese signs", "lanterns"]
            },
            {
                "prompt": "An underwater coral reef with colorful tropical fish",
                "expected_elements": ["underwater", "coral reef", "fish"]
            },
            {
                "prompt": "A medieval castle on a hill with a dragon flying overhead",
                "expected_elements": ["castle", "dragon", "medieval"]
            }
        ]

        # Run tests
        successful_tests = 0
        for i, test_case in enumerate(test_cases, 1):
            print(f"\nTest {i}/{len(test_cases)}:")

            result = self.run_quality_test(workflow, test_case)

            if result:
                self.results["test_cases"].append(result)
                if result["clip_score"]:
                    self.results["clip_scores"].append(result["clip_score"])
                self.results["generation_times"].append(result["generation_time"])
                successful_tests += 1

        # Calculate overall quality metrics
        self.calculate_quality_metrics()

    def calculate_quality_metrics(self):
        """Calculate and display quality metrics"""
        print("\n" + "=" * 60)
        print("QUALITY ASSESSMENT RESULTS")
        print("=" * 60)

        total_tests = len(self.results["test_cases"])
        successful_tests = len([t for t in self.results["test_cases"] if t["success"]])

        print(f"Total Tests: {total_tests}")
        print(f"Successful: {successful_tests}")
        print(f"Success Rate: {successful_tests/total_tests*100:.1f}%")
        print()

        # CLIP score statistics
        if self.results["clip_scores"]:
            scores = self.results["clip_scores"]
            import statistics

            print("CLIP Score Analysis:")
            print(f"  Average: {statistics.mean(scores):.3f}")
            print(f"  Median:  {statistics.median(scores):.3f}")
            print(f"  Min:     {min(scores):.3f}")
            print(f"  Max:     {max(scores):.3f}")
            print()

            # Quality assessment based on CLIP scores
            avg_score = statistics.mean(scores)
            if avg_score >= 0.30:
                quality_level = "EXCELLENT"
                quality_emoji = "🏆"
            elif avg_score >= 0.25:
                quality_level = "GOOD"
                quality_emoji = "✅"
            elif avg_score >= 0.20:
                quality_level = "ACCEPTABLE"
                quality_emoji = "⚠️"
            else:
                quality_level = "NEEDS IMPROVEMENT"
                quality_emoji = "❌"

            print(f"Overall Quality: {quality_emoji} {quality_level}")
            print(f"Average CLIP Score: {avg_score:.3f}")
            self.results["overall_quality"] = avg_score

        # Generation time statistics
        if self.results["generation_times"]:
            times = self.results["generation_times"]
            import statistics

            print(f"\nGeneration Time Analysis:")
            print(f"  Average: {statistics.mean(times):.2f}s")
            print(f"  Median:  {statistics.median(times):.2f}s")

        # Detailed test results
        print(f"\nDetailed Test Results:")
        print("-" * 40)
        for i, test in enumerate(self.results["test_cases"], 1):
            status = "✅" if test["success"] else "❌"
            clip_info = f"CLIP: {test['clip_score']:.3f}" if test["clip_score"] else "No CLIP score"
            print(f"{i}. {status} {clip_info}")
            print(f"   Prompt: {test['prompt'][:60]}...")

    def save_results(self, filename=None):
        """Save quality assessment results to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"quality_results_{timestamp}.json"

        try:
            with open(filename, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"\nResults saved to: {filename}")
        except Exception as e:
            print(f"Error saving results: {e}")

def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Qwen Image 8-Step Quality Assessment")
    parser.add_argument("--url", default="http://localhost:8188", help="ComfyUI server URL")
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument("--workflow", default="example-request.json", help="Test workflow file")

    args = parser.parse_args()

    # Create and run quality assessment
    benchmark = QualityBenchmark(args.url)
    benchmark.run_quality_suite()

    # Save results
    benchmark.save_results(args.output)

if __name__ == "__main__":
    main()