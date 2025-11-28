# Performance and Quality Benchmarks

This directory contains benchmarking scripts to validate the performance and quality of the Qwen Image 8-Step generation pipeline.

## 📋 Available Benchmarks

### 1. Performance Testing (`test_performance.py`)
Measures generation speed, resource usage, and system performance.

**Metrics Measured:**
- Generation time per image
- Memory usage (RAM and GPU VRAM)
- GPU utilization
- Success rate
- Resource efficiency

**Usage:**
```bash
# Run with default settings (10 tests)
python test_performance.py

# Run with custom parameters
python test_performance.py --tests 20 --url http://localhost:8188

# Save results to file
python test_performance.py --output performance_results.json

# Use custom workflow
python test_performance.py --workflow custom-workflow.json
```

**Expected Results:**
- Average generation time: 2-4 seconds
- Success rate: >95%
- Memory usage: ~16GB GPU VRAM
- GPU utilization: 85-95%

### 2. Quality Testing (`test_quality.py`)
Assesses output quality and prompt adherence using CLIP scores.

**Metrics Measured:**
- CLIP similarity scores (prompt-image alignment)
- Generation consistency
- Quality across different prompt types
- Overall quality assessment

**Usage:**
```bash
# Run quality assessment
python test_quality.py

# Save results
python test_quality.py --output quality_results.json

# Use custom workflow
python test_quality.py --workflow custom-workflow.json
```

**Expected Results:**
- Average CLIP score: >0.25
- Success rate: >90%
- Consistent quality across prompt types

## 🎯 Performance Targets

### Generation Speed
- **Excellent**: <3 seconds per generation
- **Good**: 3-5 seconds per generation
- **Acceptable**: 5-8 seconds per generation
- **Needs Improvement**: >8 seconds per generation

### Quality Assessment
- **Excellent**: CLIP score ≥0.30
- **Good**: CLIP score ≥0.25
- **Acceptable**: CLIP score ≥0.20
- **Needs Improvement**: CLIP score <0.20

### Reliability
- **Excellent**: Success rate ≥95%
- **Good**: Success rate ≥90%
- **Acceptable**: Success rate ≥80%
- **Needs Improvement**: Success rate <80%

## 📊 Benchmark Categories

### Test Prompts
The quality tests use diverse prompts to assess different capabilities:

1. **Landscapes**: Natural scenes and environments
2. **Urban**: Cities, buildings, and architecture
3. **Cultural**: Traditional and cultural elements
4. **Fantasy**: Imaginative and creative scenarios
5. **Technical**: Specific objects and requirements

### Resource Types
Performance tests measure:

1. **Computational**: CPU/GPU utilization and efficiency
2. **Memory**: RAM and VRAM usage patterns
3. **Network**: API response times and reliability
4. **Storage**: Disk I/O and model loading times

## 🔧 Running Benchmarks

### Prerequisites
- ComfyUI server running on port 8188
- Python 3.8+ with required packages:
  ```bash
  pip install requests psutil GPUtil pillow torch torchvision clip-by-openai
  ```

### Environment Setup
1. Start ComfyUI with the Qwen workflow loaded
2. Ensure models are downloaded and accessible
3. Verify GPU availability and CUDA setup

### Test Execution
1. **Performance Testing**: Run first to validate speed and resource usage
2. **Quality Testing**: Run after performance validation
3. **Combined Analysis**: Review both sets of results together

## 📈 Interpreting Results

### Performance Indicators
- **Consistent Times**: Low standard deviation indicates stable performance
- **High Success Rate**: Reliability of the generation pipeline
- **Efficient Resource Use**: Optimal GPU and memory utilization

### Quality Indicators
- **High CLIP Scores**: Better prompt adherence and understanding
- **Consistent Quality**: Similar scores across different prompt types
- **Low Failure Rate**: Robust generation capabilities

### Optimization Opportunities
- **Slow Generation**: Consider GPU upgrades or model optimizations
- **High Memory Usage**: Model quantization or batch processing
- **Low Quality**: Prompt engineering or model fine-tuning

## 🚨 Troubleshooting

### Common Issues
1. **Server Not Responding**: Ensure ComfyUI is running on port 8188
2. **Model Loading Errors**: Verify all models are properly downloaded
3. **GPU Memory Issues**: Check VRAM availability and model size
4. **CLIP Model Errors**: Install required CLIP dependencies

### Debug Mode
Run benchmarks with verbose output:
```bash
python test_performance.py --verbose
python test_quality.py --verbose
```

## 📋 Benchmark Checklist

Before submitting to RunPod Hub:

- [ ] Performance tests meet target metrics
- [ ] Quality tests achieve acceptable CLIP scores
- [ ] Success rate is above 90%
- [ ] Resource usage is within GPU limits
- [ ] Results are documented and saved
- [ ] Any performance issues are identified and addressed

## 📄 Result Files

Benchmark results are saved as JSON files with timestamps:
- `performance_results_YYYYMMDD_HHMMSS.json`
- `quality_results_YYYYMMDD_HHMMSS.json`

These files contain:
- Individual test results
- Statistical analysis
- Performance metrics
- Quality assessments
- System configuration details

Use these files for:
- Performance tracking over time
- RunPod Hub submission requirements
- Optimization planning
- Quality assurance documentation