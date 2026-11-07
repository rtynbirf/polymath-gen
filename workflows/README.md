# Workflows ComfyUI (API-формат)

Файлы отсюда передаются в агент флагом `--comfy-workflow путь.json`,
он сам подставит `{{POSITIVE}} {{NEGATIVE}} {{W}} {{H}} {{SEED}}`.

| Файл | Модель | Статус |
|---|---|---|
| `sdxl_txt2img_api.json` | SDXL 1.0 | ✅ канонический граф KSampler |
| `flux_schnell_txt2img_api.json` | FLUX.1-schnell (fp8) | ✅ скелет по официальному шаблону |
| видео (Wan 2.2 / LTX-Video) | — | ⚙️ экспортируйте из вашего ComfyUI |

## Как добавить видео-workflow за 1 минуту

1. Откройте ComfyUI → **Workflow → Browse Templates → Video** → выберите шаблон
   Wan 2.2 (i2v или t2v) или LTX-Video под объём вашей VRAM.
2. Проверьте, что он отрабатывает в UI.
3. Включите режим разработчика: **Settings → Dev mode** (галочка).
4. Кнопка **Save (API format)** сохранит workflow в API-JSON.
5. В текстовых узлах (positive/negative) впишите `{{POSITIVE}}` / `{{NEGATIVE}}`,
   в размере — `{{W}}`/`{{H}}`, в seed — `{{SEED}}`. Готово — агент умеет его вызывать.

## Где брать модели

См. `docs/MODELS.md` — команды `huggingface-cli download` для SDXL, FLUX.1-schnell,
Wan 2.2, LTX-Video + размеры и лицензии.
