# Open-source модели: что грузить локально (команды + лицензии)

> ⚠️ Лицензии меняются — сверяйтесь с карточкой модели на HuggingFace перед
> коммерческим использованием. Ниже — проверенные repo id и файлы.

## Быстрый старт картинок (GPU ≥ 8 GB VRAM)

```bash
pip install "huggingface_hub[cli]"
# SDXL 1.0 (~6.9 GB) — база с тысячами LoRA
huggingface-cli download stabilityai/stable-diffusion-xl-base-1.0 sd_xl_base_1.0.safetensors --local-dir ComfyUI/models/checkpoints
# FLUX.1-schnell fp8 (~11.7 GB суммарно) — быстрое SOTA-качество, 4 шага
huggingface-cli download Comfy-Org/flux1-schnell flux1-schnell-fp8.safetensors --local-dir ComfyUI/models/unet
huggingface-cli download black-forest-labs/FLUX.1-schnell ae.safetensors --local-dir ComfyUI/models/vae
huggingface-cli download comfyanonymous/flux_text_encoders t5xxl_fp8_e4m3fn.safetensors --local-dir ComfyUI/models/text_encoders
huggingface-cli download comfyanonymous/flux_text_encoders clip_l.safetensors --local-dir ComfyUI/models/text_encoders
```

## Видео (GPU ≥ 12 GB VRAM)

| Модель | Repo | Лицензия | Комментарий |
|---|---|---|---|
| Wan 2.2 T2V/I2V A14B | `Wan-AI/Wan2.2-T2V-A14B`, `Wan-AI/Wan2.2-I2V-A14B`; repackage: `Comfy-Org/Wan_2.2_ComfyUI_Repackaged` | Apache-2.0 | SOTA open-source видео; fp8-варианты для 12–24 GB |
| Wan 2.2 5B | `Wan-AI/Wan2.2-TI2V-5B` | Apache-2.0 | идёт на 8–12 GB, t2v+i2v в одной |
| LTX-Video | `Lightricks/LTX-Video` | LTXV Open Weights (см. карточку) | самое быстрое, «в реальном времени» |
| CogVideoX-5b | `THUDM/CogVideoX-5b` | Apache-2.0 | простой запуск, t2v/i2v |
| HunyuanVideo | `Tencent/HunyuanVideo` | Tencent community (см. карточку) | качество 13B, нужна серьёзная VRAM |

```bash
# пример: Wan 2.2 5B (единая t2v+i2v модель)
huggingface-cli download Comfy-Org/Wan_2.2_ComfyUI_Repackaged --local-dir ComfyUI/models
```

## Мозг агента (LLM/VLM через Ollama, CPU/any GPU)

```bash
ollama pull qwen2.5:7b      # мозг-составитель промптов (Apache-2.0)
ollama pull qwen2.5vl:7b    # глаза-критик (Apache-2.0)
```

## Восстановление и апскейл

| Модель | Repo | Лицензия |
|---|---|---|
| Real-ESRGAN | `xinntao/Real-ESRGAN` | BSD-3 |
| GFPGAN | `TencentARC/GFPGAN` | Apache-2.0 |
| RIFE (интерполяция кадров) | `hzwer/Practical-RIFE` | MIT |
| FILM (интерполяция кадров) | `google-research/frame-interpolation` | Apache-2.0 |

## Памятка лицензий (на 08.11.2026)

- **Apache-2.0 / MIT / BSD** — можно коммерчески: FLUX.1-schnell, Wan 2.2,
  CogVideoX, Qwen-Image, Qwen2.5(-VL), Ollama, RIFE, Real-ESRGAN, GFPGAN.
- **Некоммерческие / community**: FLUX.1-dev, SD 3.5 Large (community-лицензия),
  HunyuanVideo, CodeFormer (S-Lab), LTX-Video (отдельная open-weights лицензия).
- **OpenRAIL++-M (SDXL)** — можно коммерчески с ограничениями по использованию.
