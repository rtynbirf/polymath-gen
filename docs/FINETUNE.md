# Обучение своей LoRA (дообучение «на своих данных»)

> Честно: с нуля обучение модели в сандбоксе невозможно (нет GPU-фермы и датасетов).
> Но путь «своих данных → своя LoRA → своя модель в бэкенде» собран полностью.

## Что понадобится

- GPU ≥ 12 GB VRAM (RTX 3060 12GB достаточно для SDXL-LoRA; для FLUX-LoRA — 16-24 GB)
- Windows или Linux, 50–100 GB под датасет/чекпоинты

## Вариант A: kohya_ss (классика)

```bash
git clone https://github.com/bmaltais/kohya_ss && cd kohya_ss
# Windows: setup.bat    Linux: ./setup.sh
```

1. Датасет: 20–50 изображений вашего стиля/объекта в `train_data/`,
   разрешения 512–1024, файлы с тегами (можно сгенерировать автотеггером WD14).
2. Конфиг `configs/pmg_lora_sdxl.toml` (шаблон ниже), база `sd_xl_base_1.0.safetensors`.
3. Тренировка:
   ```bash
   accelerate launch --num_cpu_threads_per_process 8 sdxl_train_network.py \
     --config_file configs/pmg_lora_sdxl.toml
   ```
4. Результат: `output/pmg_lora.safetensors` → `ComfyUI/models/loras/`.
5. В ComfyUI-workflow добавляете узел `LoraLoaderModelOnly` → ваша LoRA в цепочке агента.

## Вариант B: OneTrainer (GUI, дружелюбнее)

`https://github.com/Nerogar/OneTrainer` — выбрать шаблон SDXL LoRA / FLUX LoRA,
указать папку датасета, запустить. На выходе тот же `.safetensors`.

## Шаблон конфига kohya (SDXL LoRA)

```toml
[general]
pretrained_model_name_or_path = "ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors"
train_data_dir = "train_data"
output_dir = "output"
output_name = "pmg_lora"

[training]
network_module = "networks.lora"
network_dim = 32
network_alpha = 16
learning_rate = 1e-4
lr_scheduler = "cosine"
train_batch_size = 1
max_train_steps = 1500
mixed_precision = "bf16"
gradient_checkpointing = true
cache_latents_to_disk = true
save_model_as = "safetensors"
save_every_n_steps = 250
```

## Как «обучается» сам агент (без весов)

Каждый прогон пишет `runs/*/state.json`: промпт, layout, оценку критика, замечания.
Это готовый датасет предпочтений: `(задание, промпт, verdict)`. Два применения:
1. **Prompt-эволюция**: раз в N прогонов просим LLM проанализировать лучшие/худшие
   оценки и дополнить `prompts/patterns.json` новыми правилами.
2. **LoRA-преференс**: лучшие кадры → папка датасета → обучение LoRA стиля
   (Вариант A/B) → LoRA подключается в ComfyUI-workflow агента.
