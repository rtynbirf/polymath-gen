# =====================================================================
# ПОЛИМАТ-ГЕН: установка локального open-source стека на Windows
# КомfyUI + SDXL + FLUX.1-schnell + Ollama (мозг офлайн)
# Запуск: powershell -ExecutionPolicy Bypass -File scripts\install_local_stack.ps1
# =====================================================================
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot ? (Split-Path (Split-Path $PSScriptRoot)) : "C:\polymath"
$Stack = Join-Path $Root "stack"
New-Item -ItemType Directory -Force -Path $Stack | Out-Null
Set-Location $Stack

Write-Host "== 1/5 Python + Git + ffmpeg ==" -ForegroundColor Cyan
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { winget install -e --id Python.Python.3.12 }
if (-not (Get-Command git -ErrorAction SilentlyContinue))    { winget install -e --id Git.Git }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { winget install -e --id Gyan.FFmpeg }

Write-Host "== 2/5 ComfyUI ==" -ForegroundColor Cyan
if (-not (Test-Path "ComfyUI")) {
    git clone https://github.com/comfyanonymous/ComfyUI
    Push-Location ComfyUI
    python -m venv venv
    .\venv\Scripts\pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
    .\venv\Scripts\pip install -r requirements.txt "huggingface_hub[cli]"
    Pop-Location
}

Write-Host "== 3/5 Модели картинок: SDXL + FLUX.1-schnell ==" -ForegroundColor Cyan
$Models = "ComfyUI\models"
huggingface-cli download stabilityai/stable-diffusion-xl-base-1.0 sd_xl_base_1.0.safetensors --local-dir "$Models\checkpoints"
huggingface-cli download Comfy-Org/flux1-schnell flux1-schnell-fp8.safetensors --local-dir "$Models\unet"
huggingface-cli download black-forest-labs/FLUX.1-schnell ae.safetensors --local-dir "$Models\vae"
huggingface-cli download comfyanonymous/flux_text_encoders t5xxl_fp8_e4m3fn.safetensors --local-dir "$Models\text_encoders"
huggingface-cli download comfyanonymous/flux_text_encoders clip_l.safetensors --local-dir "$Models\text_encoders"

Write-Host "== 4/5 Мозг: Ollama + Qwen2.5 (офлайн LLM/VLM) ==" -ForegroundColor Cyan
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) { winget install -e --id Ollama.Ollama }
ollama pull qwen2.5:7b
ollama pull qwen2.5vl:7b

Write-Host "== 5/5 Видео-модели (опционально, GPU >= 12GB) ==" -ForegroundColor Cyan
Write-Host "См. docs/MODELS.md: Wan 2.2 / LTX-Video / CogVideoX (huggingface-cli download)"

Write-Host ""
Write-Host "ГОТОВО. Запуск стека:" -ForegroundColor Green
Write-Host "  cd $Stack\ComfyUI; .\venv\Scripts\python main.py --listen 127.0.0.1 --port 8188"
Write-Host "  ollama serve"
Write-Host "Затем: python -m polymath_gen.cli examples\task.demo.yaml --backend comfy --llm ollama"
