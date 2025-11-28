# API Integration Examples

This directory contains comprehensive examples for integrating with the Qwen Image 8-Step Generation API. Each example demonstrates different integration patterns and use cases.

## 📁 Available Examples

### 1. Quick Start (`quick_start.py`)
**Purpose**: Basic API integration for rapid prototyping
**Best for**: Getting started quickly, simple use cases

**Features**:
- Simple prompt-based generation
- Basic error handling
- Output file detection
- Example prompts for testing

**Usage**:
```bash
# Run the quick start example
python quick_start.py

# Requirements: requests
```

**Expected Output**: 5 sample images generated from example prompts

### 2. API Integration (`api_integration.py`)
**Purpose**: Production-ready integration with advanced features
**Best for**: Applications, production systems, robust implementations

**Features**:
- Comprehensive error handling and retries
- Custom generation parameters (size, seed, steps)
- Batch processing capabilities
- Health checks and connection management
- Request/Response data classes
- Detailed logging
- Metadata saving

**Usage**:
```bash
# Run with default settings
python api_integration.py

# Requirements: requests, dataclasses, typing

# Example usage in your code:
from api_integration import QwenImageAPI, GenerationRequest

api = QwenImageAPI("http://localhost:8188")
request = GenerationRequest(
    prompt="A beautiful landscape",
    seed=12345,
    width=1024,
    height=1024
)
result = api.generate_image(request)
```

### 3. Batch Generation (`batch_generation.py`)
**Purpose**: High-volume parallel image generation
**Best for**: Large-scale processing, datasets, automation

**Features**:
- Parallel processing with ThreadPoolExecutor
- Bulk prompt loading from text files
- Progress tracking and statistics
- CSV/JSON result export
- Failed request retry logic
- Performance monitoring
- Memory-efficient processing

**Usage**:
```bash
# Create sample prompts file (runs automatically if none exists)
python batch_generation.py

# Custom prompts file format:
# prompt|seed (seed is optional)
# A beautiful sunset|1001
# A futuristic city|1002

# Requirements: requests, concurrent.futures, csv
```

## 🛠️ Setup and Requirements

### Prerequisites
1. **ComfyUI Server**: Running on port 8188 with Qwen workflow loaded
2. **Python 3.8+**: For running the example scripts
3. **Required Models**: All Qwen models downloaded and accessible

### Python Dependencies
```bash
# Install required packages
pip install requests

# For batch generation (additional dependencies)
pip install requests dataclasses typing concurrent.futures csv

# For advanced features (optional)
pip install pillow numpy tqdm
```

### Environment Setup
```bash
# Ensure ComfyUI is running
# Navigate to your ComfyUI installation
python main.py --listen 0.0.0.0 --port 8188

# Verify the server is responding
curl http://localhost:8188/system_stats
```

## 📋 Integration Patterns

### 1. Simple Integration (Quick Start)
```python
import requests
import json

# Load workflow
with open("../example-request.json") as f:
    workflow = json.load(f)

# Modify prompt
workflow["input"]["workflow"]["6"]["inputs"]["text"] = "Your prompt here"

# Submit generation
response = requests.post("http://localhost:8188/prompt", json=workflow)
prompt_id = response.json()["prompt_id"]
```

### 2. Robust Integration (API Client)
```python
from api_integration import QwenImageAPI, GenerationRequest

# Initialize client
api = QwenImageAPI("http://localhost:8188")

# Create request
request = GenerationRequest(
    prompt="A beautiful landscape",
    seed=12345,
    width=1024,
    height=1024
)

# Generate image
result = api.generate_image(request)
if result.success:
    print(f"Generated {len(result.images)} images")
```

### 3. Batch Processing
```python
from batch_generation import BatchGenerator, BatchConfig

# Configure batch processing
config = BatchConfig(
    prompts_file="your_prompts.txt",
    output_dir="output",
    max_workers=3
)

# Run batch generation
generator = BatchGenerator(config)
prompts = generator.load_prompts("your_prompts.txt")
results = generator.run_batch(prompts)
```

## 🔧 Configuration Options

### Generation Parameters
- **prompt**: Text description for image generation
- **seed**: Random seed for reproducible results
- **width/height**: Image dimensions (default: 1328x1328)
- **steps**: Number of generation steps (fixed at 8 for speed)
- **cfg_scale**: Prompt adherence scale (default: 1.0)
- **batch_size**: Number of images per generation (default: 1)

### API Settings
- **base_url**: ComfyUI server URL (default: http://localhost:8188)
- **timeout**: Request timeout in seconds
- **max_retries**: Number of retry attempts for failed requests
- **retry_delay**: Delay between retries in seconds

### Batch Processing Settings
- **max_workers**: Number of parallel generations
- **output_dir**: Directory for generated images and metadata
- **save_metadata**: Whether to save generation metadata

## 📊 Performance Optimization

### Speed Optimization
1. **Parallel Processing**: Use batch generation with multiple workers
2. **Seed Reuse**: Fix seeds for reproducible results
3. **Batch Requests**: Generate multiple images per request
4. **Connection Pooling**: Reuse HTTP connections

### Memory Optimization
1. **Streaming Results**: Process results as they complete
2. **Cleanup**: Clean up temporary files and data
3. **Limit Workers**: Don't exceed GPU memory limits
4. **Monitor Usage**: Track GPU and system memory

### Reliability Optimization
1. **Health Checks**: Verify API availability before processing
2. **Retry Logic**: Implement exponential backoff for retries
3. **Error Handling**: Graceful handling of failures
4. **Logging**: Comprehensive logging for debugging

## 🚨 Troubleshooting

### Common Issues

**1. Connection Errors**
```bash
# Check if ComfyUI is running
curl http://localhost:8188/system_stats

# Verify port and firewall settings
netstat -tlnp | grep 8188
```

**2. Model Loading Errors**
- Verify all models are downloaded
- Check model file paths in ComfyUI
- Restart ComfyUI to reload models

**3. Generation Timeouts**
- Increase timeout values in configuration
- Check GPU memory usage
- Reduce batch size or worker count

**4. Memory Issues**
- Reduce max_workers in batch generation
- Monitor GPU memory usage
- Use smaller image dimensions

**5. Quality Issues**
- Review prompt engineering
- Check model configurations
- Verify workflow parameters

### Debug Mode
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check system status
response = requests.get("http://localhost:8188/system_stats")
print(response.json())
```

## 📚 Advanced Usage

### Custom Workflow Modifications
```python
# Modify workflow for custom needs
def customize_workflow(workflow, custom_params):
    # Adjust LoRA strength
    workflow["input"]["workflow"]["66"]["inputs"]["value"] = custom_params["lora_strength"]

    # Modify sampler settings
    workflow["input"]["workflow"]["3"]["inputs"]["sampler_name"] = custom_params["sampler"]

    return workflow
```

### Result Processing
```python
# Process generated images
def process_results(result):
    if result.success:
        for image_info in result.images:
            # Save to different location
            # Apply post-processing
            # Generate thumbnails
            pass
```

### Integration with Other Services
```python
# Database integration
def save_to_database(result):
    # Save generation metadata
    # Track usage statistics
    # Manage user credits
    pass

# CDN integration
def upload_to_cdn(image_path):
    # Upload generated images
    # Generate public URLs
    # Cache frequently used images
    pass
```

## 📄 License and Usage

These examples are provided under the same license as the main Qwen Image 8-Step repository. Feel free to modify and adapt them for your specific use cases.

For production deployments, consider:
- Adding authentication and rate limiting
- Implementing user management and billing
- Setting up monitoring and alerting
- Creating custom user interfaces
- Integrating with storage and CDN services