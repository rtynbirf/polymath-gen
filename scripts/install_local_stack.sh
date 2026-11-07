#!/usr/bin/env bash
# ПОЛИМАТ-ГЕН: установка локального open-source стека (Linux)
set -e
STACK="${POLYMATH_STACK:-$HOME/polymath-stack}"
mkdir -p "$STACK"; cd "$STACK"

echo "== 1/5 Python + Git + ffmpeg =="
command -v python3 || sudo apt install -y python3 python3-venv
command -v git || sudo apt install -y git
command -v ffmpeg || sudo apt install -y ffmpeg

echo "== 2/5 ComfyUI =="
if [ ! -d ComfyUI ]; then
  git clone https://github.com/comfyanonymous/ComfyUI
  cd ComfyUI && python3 -m venv venv
  ./venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
  ./venv/bin/pip install -r requirements.txt "huggingface_hub[cli]"
  cd ..
fi

echo "== 3/5 Модели: SDXL + FLUX.1-schnell =="
M=ComfyUI/models
huggingface-cli download stabilityai/stable-diffusion-xl-base-1.0 sd_xl_base_1.0.safetensors --local-dir $M/checkpoints
huggingface-cli download Comfy-Org/flux1-schnell flux1-schnell-fp8.safetensors --local-dir $M/unet
huggingface-cli download black-forest-labs/FLUX.1-schnell ae.safetensors --local-dir $M/vae
huggingface-cli download comfyanonymous/flux_text_encoders t5xxl_fp8_e4m3fn.safetensors --local-dir $M/text_encoders
huggingface-cli download comfyanonymous/flux_text_encoders clip_l.safetensors --local-dir $M/text_encoders

echo "== 4/5 Мозг: Ollama + Qwen2.5 =="
if ! command -v ollama; then curl -fsSL https://ollama.com/install.sh | sh; fi
ollama pull qwen2.5:7b
ollama pull qwen2.5vl:7b

echo "ГОТОВО. Запуск:"
echo "  cd $STACK/ComfyUI && ./venv/bin/python main.py --listen 127.0.0.1 --port 8188"
echo "  ollama serve"
echo "  python -m polymath_gen.cli examples/task.demo.yaml --backend comfy --llm ollama"
