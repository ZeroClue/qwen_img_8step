# clean base image containing only comfyui, comfy-cli and comfyui-manager
FROM runpod/worker-comfyui:5.5.0-base

ARG HF_TOKEN

# install custom nodes into comfyui
RUN comfy node install --exit-on-fail comfyui-image-saver@1.16.0

# download models into comfyui
#RUN comfy model download --url https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_fp8_e4m3fn.safetensors --relative-path models/diffusion_models --filename qwen_image_fp8_e4m3fn.safetensors
#RUN comfy model download --url https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors --relative-path models/clip --filename qwen_2.5_vl_7b_fp8_scaled.safetensors
#RUN comfy model download --url https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors --relative-path models/vae --filename qwen_image_vae.safetensors
#RUN comfy model download --url https://huggingface.co/lightx2v/Qwen-Image-Lightning/resolve/main/Qwen-Image-Lightning-8steps-V1.0.safetensors --relative-path models/loras --filename Qwen-Image-Lightning-8steps-V1.0.safetensors

# Models are now downloaded at runtime by check-models.sh script
# This makes the Docker build faster and images smaller

# copy custom scripts to root directory to override base image
COPY /scripts/check-models.sh /check-models.sh
COPY /scripts/check-models-parallel.sh /check-models-parallel.sh
COPY /scripts/start.sh /start.sh
COPY handler.py /handler.py

# make scripts executable (REQUIRED for execution)
RUN chmod +x /check-models.sh /check-models-parallel.sh /start.sh

# copy all input data (like images or videos) into comfyui (uncomment and adjust if needed)
# COPY input/ /comfyui/input/
