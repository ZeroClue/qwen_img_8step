#!/usr/bin/env bash
# Model validation and downloading script for ComfyUI (Parallel)

set -euo pipefail

# Logging function
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [check-models-parallel] [$level] $message" >&2
}

# Model validation function
validate_model() {
    local model_path="$1"
    local model_name="$2"
    local full_path="/comfyui/models/${model_path}"

    if [[ -f "$full_path" ]]; then
        local file_size=$(stat -c%s "$full_path" 2>/dev/null)
        if [[ $file_size -gt 0 ]]; then
            log "INFO" "✓ Model verified: $model_name ($(numfmt --to=iec $file_size))"
            return 0
        else
            log "ERROR" "✗ Model file exists but is empty: $model_name"
            return 1
        fi
    else
        log "WARN" "✗ Model missing: $model_name"
        return 1
    fi
}

# Download model function with retry logic (parallel-safe)
download_model() {
    local url="$1"
    local relative_path="$2"
    local filename="$3"
    local model_name="$4"
    local max_retries=3
    local retry_count=0

    log "INFO" "Downloading $model_name (parallel job)..."

    while [[ $retry_count -lt $max_retries ]]; do
        if comfy model download --url "$url" --relative-path "models/$relative_path" --filename "$filename"; then
            log "INFO" "✓ Successfully downloaded $model_name"
            echo "SUCCESS:$model_name" > "/tmp/download_result_$$.txt"
            return 0
        else
            retry_count=$((retry_count + 1))
            if [[ $retry_count -lt $max_retries ]]; then
                log "WARN" "Download failed for $model_name (attempt $retry_count/$max_retries). Retrying in 5 seconds..."
                sleep 5
            fi
        fi
    done

    log "ERROR" "✗ Failed to download $model_name after $max_retries attempts"
    echo "FAILED:$model_name" > "/tmp/download_result_$$.txt"
    return 1
}

# Model configuration (same as sequential)
declare -A MODELS=(
    ["diffusion_models/qwen_image_fp8_e4m3fn.safetensors"]="https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_fp8_e4m3fn.safetensors|diffusion_models|qwen_image_fp8_e4m3fn.safetensors|Qwen Diffusion Model"
    ["clip/qwen_2.5_vl_7b_fp8_scaled.safetensors"]="https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors|clip|qwen_2.5_vl_7b_fp8_scaled.safetensors|Qwen CLIP Model"
    ["vae/qwen_image_vae.safetensors"]="https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors|vae|qwen_image_vae.safetensors|Qwen VAE Model"
    ["loras/Qwen-Image-Lightning-8steps-V1.0.safetensors"]="https://huggingface.co/lightx2v/Qwen-Image-Lightning/resolve/main/Qwen-Image-Lightning-8steps-V1.0.safetensors|loras|Qwen-Image-Lightning-8steps-V1.0.safetensors|Qwen Lightning LoRA"
)

# Parallel download function
download_models_parallel() {
    local missing_models=("$@")
    local pids=()
    local temp_files=()

    log "INFO" "Starting parallel downloads for ${#missing_models[@]} models..."

    # Start downloads in parallel
    for model_path in "${missing_models[@]}"; do
        local model_info="${MODELS[$model_path]}"
        local url=$(echo "$model_info" | cut -d'|' -f1)
        local relative_path=$(echo "$model_info" | cut -d'|' -f2)
        local filename=$(echo "$model_info" | cut -d'|' -f3)
        local model_name=$(echo "$model_info" | cut -d'|' -f4)

        # Create temp file for this download's result
        local temp_file="/tmp/download_result_${model_name//[^a-zA-Z0-9]/_}.txt"
        temp_files+=("$temp_file")

        # Start download in background
        (
            if download_model "$url" "$relative_path" "$filename" "$model_name"; then
                echo "SUCCESS:$model_name" > "$temp_file"
            else
                echo "FAILED:$model_name" > "$temp_file"
            fi
        ) &
        pids+=($!)
    done

    # Wait for all downloads to complete
    log "INFO" "Waiting for ${#pids[@]} parallel downloads to complete..."
    for pid in "${pids[@]}"; do
        wait "$pid"
    done

    # Collect results
    local failed_downloads=()
    for temp_file in "${temp_files[@]}"; do
        if [[ -f "$temp_file" ]]; then
            local result=$(cat "$temp_file")
            local status=$(echo "$result" | cut -d':' -f1)
            local model_name=$(echo "$result" | cut -d':' -f2)

            if [[ "$status" == "FAILED" ]]; then
                failed_downloads+=("$model_name")
            fi
            rm -f "$temp_file"
        fi
    done

    # Clean up any remaining temp files
    rm -f /tmp/download_result_*.txt

    echo "${failed_downloads[@]}"
}

# Main validation function
main() {
    local missing_models=()

    log "INFO" "Starting model validation (parallel mode)..."

    # Check each model
    for model_path in "${!MODELS[@]}"; do
        local model_info="${MODELS[$model_path]}"
        local model_name=$(echo "$model_info" | cut -d'|' -f4)

        if ! validate_model "$model_path" "$model_name"; then
            missing_models+=("$model_path")
        fi
    done

    # Download missing models in parallel
    if [[ ${#missing_models[@]} -gt 0 ]]; then
        log "INFO" "Found ${#missing_models[@]} missing models. Starting parallel download process..."

        local failed_downloads_str
        failed_downloads_str=$(download_models_parallel "${missing_models[@]}")
        read -ra failed_downloads <<< "$failed_downloads_str"

        # Warn about failed downloads but continue (optional mode)
        if [[ ${#failed_downloads[@]} -gt 0 ]]; then
            log "WARN" "Failed to download ${#failed_downloads[@]} models: ${failed_downloads[*]}"
            log "WARN" "ComfyUI will continue but some features may not work properly"
        fi

        # Final verification for successful downloads
        log "INFO" "Verifying downloaded models..."
        for model_path in "${missing_models[@]}"; do
            local model_info="${MODELS[$model_path]}"
            local model_name=$(echo "$model_info" | cut -d'|' -f4)

            # Skip verification for models that failed to download
            if [[ ! " ${failed_downloads[*]} " =~ " ${model_name} " ]]; then
                if ! validate_model "$model_path" "$model_name"; then
                    log "ERROR" "Download verification failed for $model_name"
                    failed_downloads+=("$model_name")
                fi
            fi
        done
    else
        log "INFO" "All required models are present and validated"
    fi

    # Always return success in optional mode
    log "INFO" "Model validation completed"
    return 0
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi