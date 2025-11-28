#!/usr/bin/env python3
"""
Performance benchmarking script for Qwen Image 8-Step Generation
Tests generation speed, memory usage, and resource utilization
"""

import time
import json
import requests
import psutil
import GPUtil
import statistics
from datetime import datetime
import sys
import os

class PerformanceBenchmark:
    def __init__(self, base_url="http://localhost:8188"):
        self.base_url = base_url
        self.results = {
            "generation_times": [],
            "memory_usage": [],
            "gpu_usage": [],
            "success_rate": 0,
            "total_requests": 0,
            "failed_requests": 0
        }

    def load_test_workflow(self, workflow_file="example-request.json"):
        """Load the test workflow JSON"""
        try:
            with open(workflow_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading workflow: {e}")
            return None

    def get_system_stats(self):
        """Get current system statistics"""
        try:
            # CPU and Memory
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()

            # GPU stats if available
            gpu_stats = {}
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    gpu_stats = {
                        "gpu_memory_used": gpu.memoryUsed,
                        "gpu_memory_total": gpu.memoryTotal,
                        "gpu_utilization": gpu.load * 100,
                        "gpu_temperature": gpu.temperature
                    }
            except:
                pass

            return {
                "cpu_percent": cpu_percent,
                "memory_used_gb": memory.used / (1024**3),
                "memory_total_gb": memory.total / (1024**3),
                "memory_percent": memory.percent,
                **gpu_stats
            }
        except Exception as e:
            print(f"Error getting system stats: {e}")
            return {}

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

    def check_generation_status(self, prompt_id):
        """Check if generation is complete"""
        try:
            response = requests.get(f"{self.base_url}/history/{prompt_id}")
            if response.status_code == 200:
                history = response.json()
                if prompt_id in history:
                    return history[prompt_id]["outputs"]
            return None
        except Exception as e:
            print(f"Error checking generation status: {e}")
            return None

    def measure_generation(self, workflow, prompt_text=None):
        """Measure a single generation with timing and resource usage"""
        start_time = time.time()
        start_stats = self.get_system_stats()

        # Submit generation
        prompt_id = self.submit_generation(workflow, prompt_text)
        if not prompt_id:
            return None

        # Poll for completion
        max_wait_time = 60  # Maximum 60 seconds wait
        poll_interval = 0.5
        elapsed = 0

        while elapsed < max_wait_time:
            result = self.check_generation_status(prompt_id)
            if result:
                end_time = time.time()
                end_stats = self.get_system_stats()

                generation_time = end_time - start_time

                # Calculate resource usage
                memory_delta = end_stats.get("memory_used_gb", 0) - start_stats.get("memory_used_gb", 0)
                gpu_memory_delta = end_stats.get("gpu_memory_used", 0) - start_stats.get("gpu_memory_used", 0)

                return {
                    "generation_time": generation_time,
                    "memory_peak": end_stats.get("memory_used_gb", 0),
                    "memory_delta": memory_delta,
                    "gpu_memory_peak": end_stats.get("gpu_memory_used", 0),
                    "gpu_utilization": end_stats.get("gpu_utilization", 0),
                    "success": True,
                    "prompt_id": prompt_id
                }

            time.sleep(poll_interval)
            elapsed += poll_interval

        # Timeout
        print(f"Generation timeout for prompt {prompt_id}")
        return {
            "generation_time": max_wait_time,
            "success": False,
            "prompt_id": prompt_id,
            "error": "timeout"
        }

    def run_benchmark_suite(self, num_tests=10):
        """Run a comprehensive benchmark suite"""
        print(f"Running Qwen Image 8-Step Performance Benchmark")
        print(f"Number of tests: {num_tests}")
        print(f"Base URL: {self.base_url}")
        print("-" * 60)

        # Load test workflow
        workflow = self.load_test_workflow()
        if not workflow:
            print("Failed to load test workflow")
            return

        # Test prompts
        test_prompts = [
            "A serene mountain landscape at sunset",
            "A futuristic city with flying cars",
            "A traditional Japanese garden in spring",
            "A cyberpunk street with neon lights",
            "A cozy library with ancient books"
        ]

        # Check server availability
        try:
            response = requests.get(f"{self.base_url}/system_stats")
            if response.status_code != 200:
                print("Error: ComfyUI server not responding")
                return
        except:
            print("Error: Cannot connect to ComfyUI server")
            return

        # Run benchmark tests
        print("Starting performance tests...")

        for i in range(num_tests):
            print(f"Test {i+1}/{num_tests}...", end=" ")

            # Rotate through test prompts
            prompt = test_prompts[i % len(test_prompts)]

            # Measure generation
            result = self.measure_generation(workflow, prompt)

            if result and result.get("success"):
                self.results["generation_times"].append(result["generation_time"])
                if result.get("memory_peak"):
                    self.results["memory_usage"].append(result["memory_peak"])
                if result.get("gpu_utilization"):
                    self.results["gpu_usage"].append(result["gpu_utilization"])
                self.results["total_requests"] += 1
                print(f"✅ {result['generation_time']:.2f}s")
            else:
                self.results["failed_requests"] += 1
                self.results["total_requests"] += 1
                print(f"❌ Failed")

        # Calculate statistics
        self.calculate_statistics()

    def calculate_statistics(self):
        """Calculate and display benchmark statistics"""
        print("\n" + "=" * 60)
        print("BENCHMARK RESULTS")
        print("=" * 60)

        # Success rate
        if self.results["total_requests"] > 0:
            self.results["success_rate"] = (self.results["total_requests"] - self.results["failed_requests"]) / self.results["total_requests"] * 100

        print(f"Total Requests: {self.results['total_requests']}")
        print(f"Successful: {self.results['total_requests'] - self.results['failed_requests']}")
        print(f"Failed: {self.results['failed_requests']}")
        print(f"Success Rate: {self.results['success_rate']:.1f}%")
        print()

        # Generation time statistics
        if self.results["generation_times"]:
            times = self.results["generation_times"]
            print("Generation Time Statistics:")
            print(f"  Average: {statistics.mean(times):.2f}s")
            print(f"  Median:  {statistics.median(times):.2f}s")
            print(f"  Min:     {min(times):.2f}s")
            print(f"  Max:     {max(times):.2f}s")
            print(f"  Std Dev: {statistics.stdev(times) if len(times) > 1 else 0:.2f}s")
            print()

        # Memory usage statistics
        if self.results["memory_usage"]:
            memory = self.results["memory_usage"]
            print("Memory Usage Statistics:")
            print(f"  Average: {statistics.mean(memory):.1f} GB")
            print(f"  Peak:    {max(memory):.1f} GB")
            print(f"  Min:     {min(memory):.1f} GB")
            print()

        # GPU utilization statistics
        if self.results["gpu_usage"]:
            gpu = self.results["gpu_usage"]
            print("GPU Utilization Statistics:")
            print(f"  Average: {statistics.mean(gpu):.1f}%")
            print(f"  Peak:    {max(gpu):.1f}%")
            print(f"  Min:     {min(gpu):.1f}%")
            print()

        # Performance assessment
        self.assess_performance()

    def assess_performance(self):
        """Assess performance against benchmarks"""
        print("Performance Assessment:")
        print("-" * 30)

        if self.results["generation_times"]:
            avg_time = statistics.mean(self.results["generation_times"])

            # Time assessment
            if avg_time < 3:
                print("⚡ Generation Speed: EXCELLENT (<3s)")
            elif avg_time < 5:
                print("✅ Generation Speed: GOOD (3-5s)")
            elif avg_time < 8:
                print("⚠️  Generation Speed: ACCEPTABLE (5-8s)")
            else:
                print("❌ Generation Speed: NEEDS IMPROVEMENT (>8s)")

            # Success rate assessment
            if self.results["success_rate"] >= 95:
                print("✅ Success Rate: EXCELLENT (≥95%)")
            elif self.results["success_rate"] >= 90:
                print("✅ Success Rate: GOOD (90-95%)")
            elif self.results["success_rate"] >= 80:
                print("⚠️  Success Rate: ACCEPTABLE (80-90%)")
            else:
                print("❌ Success Rate: NEEDS IMPROVEMENT (<80%)")

        # Overall assessment
        print()
        if (self.results["generation_times"] and
            statistics.mean(self.results["generation_times"]) < 5 and
            self.results["success_rate"] >= 90):
            print("🎉 OVERALL: READY FOR PRODUCTION")
        else:
            print("⚠️  OVERALL: NEEDS OPTIMIZATION")

    def save_results(self, filename=None):
        """Save benchmark results to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.json"

        try:
            with open(filename, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"\nResults saved to: {filename}")
        except Exception as e:
            print(f"Error saving results: {e}")

def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Qwen Image 8-Step Performance Benchmark")
    parser.add_argument("--url", default="http://localhost:8188", help="ComfyUI server URL")
    parser.add_argument("--tests", type=int, default=10, help="Number of tests to run")
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument("--workflow", default="example-request.json", help="Test workflow file")

    args = parser.parse_args()

    # Create and run benchmark
    benchmark = PerformanceBenchmark(args.url)
    benchmark.run_benchmark_suite(args.tests)

    # Save results
    benchmark.save_results(args.output)

if __name__ == "__main__":
    main()