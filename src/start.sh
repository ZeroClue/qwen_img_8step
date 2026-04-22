#!/usr/bin/env bash

# SYMLINK MODEL DIRS TO NETWORK VOLUME IF PRESENT
if mountpoint -q /runpod-volume 2>/dev/null; then
    echo "worker-comfyui: Network volume detected, symlinking model dirs to /runpod-volume"
    for dir in diffusion_models clip vae loras; do
        mkdir -p "/runpod-volume/comfyui/models/$dir"
        # Seed volume from baked-in models on first run (avoids re-downloading)
        if [ -z "$(ls -A /runpod-volume/comfyui/models/$dir/ 2>/dev/null)" ] && \
           [ -n "$(ls -A /comfyui/models/$dir/ 2>/dev/null)" ]; then
            echo "worker-comfyui: Copying baked-in $dir to network volume..."
            cp /comfyui/models/$dir/* /runpod-volume/comfyui/models/$dir/
        fi
        ln -sfn "/runpod-volume/comfyui/models/$dir" "/comfyui/models/$dir"
    done
else
    echo "worker-comfyui: No network volume detected, using local model storage"
fi

# PRE-FETCH MODELS IN BACKGROUND (non-blocking)
# The handler will download any still-missing models on-demand when a job arrives.
# This background pass helps pre-populate models to reduce first-job latency.
echo "worker-comfyui: Pre-fetching models in background..."
/usr/local/bin/check-models.sh &

# Use libtcmalloc for better memory management
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
export LD_PRELOAD="${TCMALLOC}"

# Ensure ComfyUI-Manager runs in offline network mode inside the container
comfy-manager-set-mode offline || echo "worker-comfyui - Could not set ComfyUI-Manager network_mode" >&2

echo "worker-comfyui: Starting ComfyUI"

# Allow operators to tweak verbosity; default is DEBUG.
: "${COMFY_LOG_LEVEL:=DEBUG}"

# Serve the API and don't shutdown the container
if [ "$SERVE_API_LOCALLY" == "true" ]; then
    python -u /comfyui/main.py --disable-auto-launch --disable-metadata --listen --verbose "${COMFY_LOG_LEVEL}" --log-stdout &

    echo "worker-comfyui: Starting RunPod Handler"
    python -u /handler.py --rp_serve_api --rp_api_host=0.0.0.0
else
    python -u /comfyui/main.py --disable-auto-launch --disable-metadata --verbose "${COMFY_LOG_LEVEL}" --log-stdout &

    echo "worker-comfyui: Starting RunPod Handler"
    python -u /handler.py
fi