#!/usr/bin/env python3
"""
Quick Start Example for Qwen Image 8-Step Generation
Basic API integration example for rapid image generation
"""

import requests
import json
import time
import os
from datetime import datetime

class QwenImageGenerator:
    def __init__(self, base_url="http://localhost:8188", timeout=60):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()

    def load_workflow(self, workflow_file="../example-request.json"):
        """Load the ComfyUI workflow"""
        try:
            with open(workflow_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Workflow file {workflow_file} not found")
            return None
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in workflow file {workflow_file}")
            return None

    def generate_image(self, prompt, seed=None, workflow_file="../example-request.json"):
        """Generate an image from text prompt"""
        print(f"🎨 Generating image: {prompt[:50]}...")

        # Load workflow
        workflow = self.load_workflow(workflow_file)
        if not workflow:
            return None

        # Modify prompt
        workflow["input"]["workflow"]["6"]["inputs"]["text"] = prompt

        # Set seed if provided
        if seed:
            workflow["input"]["workflow"]["3"]["inputs"]["seed"] = seed

        # Submit generation request
        try:
            response = self.session.post(
                f"{self.base_url}/prompt",
                json=workflow,
                timeout=10
            )

            if response.status_code == 200:
                prompt_id = response.json()["prompt_id"]
                print(f"✅ Generation started with ID: {prompt_id}")
                return self.wait_for_completion(prompt_id)
            else:
                print(f"❌ Error submitting request: {response.status_code}")
                print(f"Response: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
            return None

    def wait_for_completion(self, prompt_id):
        """Wait for generation to complete and return result"""
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
                        for node_id, node_output in outputs.items():
                            if "images" in node_output:
                                images = node_output["images"]
                                if images:
                                    generation_time = time.time() - start_time
                                    return {
                                        "prompt_id": prompt_id,
                                        "images": images,
                                        "generation_time": generation_time,
                                        "success": True
                                    }

                time.sleep(1)  # Poll every second

            except requests.exceptions.RequestException as e:
                print(f"❌ Error checking status: {e}")
                break

        print(f"⏰ Generation timeout after {self.timeout} seconds")
        return {
            "prompt_id": prompt_id,
            "generation_time": self.timeout,
            "success": False,
            "error": "timeout"
        }

    def get_image_info(self, result):
        """Get information about generated images"""
        if not result or not result["success"]:
            return None

        images = []
        for image_info in result["images"]:
            # Common output paths (adjust based on your ComfyUI setup)
            possible_paths = [
                f"../output/{image_info['filename']}",
                f"output/{image_info['filename']}",
                f"/comfyui/output/{image_info['filename']}",
                image_info['filename']
            ]

            image_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    image_path = path
                    break

            images.append({
                "filename": image_info["filename"],
                "path": image_path,
                "size": image_info.get("size", {}),
                "subfolder": image_info.get("subfolder", ""),
                "type": image_info.get("type", "output")
            })

        return {
            "prompt_id": result["prompt_id"],
            "generation_time": result["generation_time"],
            "images": images
        }

def main():
    """Quick start example"""
    print("🚀 Qwen Image 8-Step Quick Start")
    print("=" * 50)

    # Initialize generator
    generator = QwenImageGenerator()

    # Example prompts
    example_prompts = [
        "A serene mountain landscape at sunset with golden light",
        "A futuristic cyberpunk city with neon lights and flying cars",
        "A traditional Japanese garden with cherry blossoms in spring",
        "A cozy library with ancient books and warm lighting",
        "A vibrant Hong Kong street with Chinese signs and lanterns"
    ]

    # Generate images
    for i, prompt in enumerate(example_prompts, 1):
        print(f"\n--- Example {i} ---")
        result = generator.generate_image(prompt, seed=42 + i)

        if result and result["success"]:
            image_info = generator.get_image_info(result)
            if image_info:
                print(f"✅ Generated {len(image_info['images'])} image(s) in {result['generation_time']:.2f}s")
                for img in image_info['images']:
                    if img['path']:
                        print(f"   📁 {img['filename']} -> {img['path']}")
                    else:
                        print(f"   📁 {img['filename']} (path not found)")
            else:
                print("❌ No images found in output")
        else:
            print(f"❌ Generation failed: {result.get('error', 'Unknown error')}")

    print(f"\n🎉 Quick start completed!")
    print("Check your output directory for generated images.")

if __name__ == "__main__":
    main()