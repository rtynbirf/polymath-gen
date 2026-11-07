"""Сердце агента:.compose промптов из задания человека.

Две траектории:
  1) LLM-составление (точная, по лучшим практикам индустрии — см. prompts/patterns.json)
  2) детерминированный fallback (словарь RU->EN + шаблоны), если мозга нет.

Вдохновение и методика:
  - Reve "layout -> render": сначала структура кадра (блоки+геометрия), потом рендер
    (см. docs/REVE_METHOD.md, наша исследовательская работа по архиву Reve 2.0)
  - практики промптинга Sora/Veo/Imagen/Midjourney/SDXL — distill в system-промпте
"""
import json
import os
from .task import TaskSpec

# --- RU -> EN словарь кинематографической лексики (longest-match) ---
VOCAB = {
    "ночной": "night", "ночью": "at night", "день": "day", "закат": "sunset", "рассвет": "sunrise",
    "туман": "fog", "туманный": "foggy", "дождь": "rain", "снег": "snow", "гроза": "storm",
    "дата-центр": "data center", "серверная": "server room", "сервер": "server", "стойка": "server rack",
    "gpu": "GPU", "видеокарта": "GPU", "робот": "robot", "роботы": "robots", "город": "city",
    "мегаполис": "megacity", "неон": "neon", "неоновый": "neon", "киберпанк": "cyberpunk",
    "космос": "outer space", "звёзды": "stars", "планета": "planet", "корабль": "ship",
    "лес": "forest", "гора": "mountain", "горы": "mountains", "море": "sea", "океан": "ocean",
    "пустыня": "desert", "пещера": "cave", "замок": "castle", "машина": "car", "самолёт": "airplane",
    "человек": "a person", "мужчина": "a man", "женщина": "a woman", "ребёнок": "a child",
    "кот": "a cat", "котёнок": "a kitten", "собака": "a dog", "птица": "a bird", "дракон": "dragon",
    "цветы": "flowers", "дерево": "tree", "портрет": "portrait", "логотип": "logo",
    "плакат": "poster", "обложка": "cover art", "баннер": "banner", "иконка": "icon",
    "сидит": "sitting", "стоит": "standing", "бежит": "running", "летит": "flying",
    "идёт": "walking", "смотрит": "looking", "держит": "holding", "улыбается": "smiling",
    "светится": "glowing", "горит": "burning", "плавает": "swimming", "большой": "large",
    "маленький": "small", "старый": "old", "новый": "new", "красный": "red", "синий": "blue",
    "зелёный": "green", "оранжевый": "orange", "золотой": "golden", "чёрный": "black",
    "белый": "white", "серебряный": "silver", "кинематографично": "cinematic",
    "кинематографический": "cinematic", "фотореалистично": "photorealistic",
    "фотореализм": "photorealism", "реалистично": "realistic", "мультяшный": "cartoon",
    "аниме": "anime", "акварель": "watercolor", "маслом": "oil painting",
    "пиксель-арт": "pixel art", "минимализм": "minimalism", "нуар": "film noir",
    "тёплый свет": "warm light", "холодный свет": "cold light", "контровой свет": "rim light",
    "общий план": "wide shot", "средний план": "medium shot", "крупный план": "close-up",
    "вид сверху": "aerial view", "макро": "macro shot", "панорама": "panorama",
    "дым": "smoke", "искры": "sparks", "огонь": "fire", "вода": "water", "зеркало": "mirror",
    "стекло": "glass", "металл": "metal", "камень": "stone", "деревянный": "wooden",
}

STYLE_MAP = {
    "cinematic": "cinematic film still, anamorphic lens, volumetric light, film grain, color graded, 35mm",
    "photorealistic": "photorealistic, ultra detailed, 8k, natural skin texture, professional photography",
    "anime": "anime key visual, cel shading, vibrant colors, studio quality",
    "cyberpunk": "cyberpunk aesthetic, neon rim light, rain-slick reflections, high contrast",
    "noir": "film noir, black and white, hard shadows, venetian blind light",
    "product": "product photography, studio softbox lighting, seamless background, commercial render",
    "portrait": "studio portrait, 85mm lens, soft key light, shallow depth of field",
    "watercolor": "watercolor painting, soft washes, paper texture",
    "pixar": "3d render, pixar-style, subsurface scattering, expressive",
    "pixel": "pixel art, 16-bit, crisp pixels, limited palette",
    "poster": "graphic design poster, bold composition, flat colors, print-ready",
    "isometric": "isometric illustration, clean geometry, soft ambient occlusion",
}

NEG_CORE = ("text, watermark, signature, logo, jpeg artifacts, worst quality, low quality, blurry, "
            "deformed, extra limbs, extra fingers, mutated hands, bad anatomy, duplicate, cropped, "
            "out of frame, ugly, lowres")

# aspect -> (zai size, w, h)
SIZE_MAP = {
    "16:9": ("1344x768", 1344, 768), "9:16": ("768x1344", 768, 1344),
    "1:1": ("1024x1024", 1024, 1024), "4:3": ("1152x864", 1152, 864),
    "3:4": ("864x1152", 864, 1152), "21:9": ("1440x720", 1440, 720),
}


def size_for(aspect: str):
    return SIZE_MAP.get(aspect, SIZE_MAP["16:9"])


def _translate(text: str) -> str:
    """Жадная замена русских слов на EN по VOCAB (longest match по ключам)."""
    out = text
    for ru in sorted(VOCAB, key=len, reverse=True):
        if ru in out:
            out = out.replace(ru, VOCAB[ru])
    return out


class PromptEngine:
    def __init__(self, llm=None):
        self.llm = llm  # объект с .chat/.available или None

    # ---------- детерминированный fallback ----------
    def compose_deterministic(self, spec: TaskSpec, shot_desc: str = "") -> dict:
        src = shot_desc or spec.goal or spec.raw
        en = _translate(src)
        style = STYLE_MAP.get(spec.style, spec.style)
        parts = [en]
        if spec.environment and spec.environment not in src:
            parts.append(_translate(spec.environment))
        if spec.lighting:
            parts.append(_translate(spec.lighting))
        if spec.mood:
            parts.append(_translate(spec.mood))
        parts.append(style)
        if spec.mode in ("video", "storyboard"):
            parts.append("dynamic composition, motion blur where appropriate")
        positive = ", ".join(p for p in parts if p)
        negative = ", ".join([NEG_CORE] + list(spec.negatives)) if spec.negatives else NEG_CORE
        return {"positive": positive, "negative": negative,
                "layout": _layout_fallback(spec, shot_desc), "notes": "deterministic fallback"}

    # ---------- LLM-составление ----------
    SYSTEM_PROMPT = """Ты — промпт-инженер мирового уровня автономного медиа-агента ПОЛИМАТ-ГЕН.
Твоя работа: превратить задание человека (обычно на русском) в идеальный генеративный промпт.

КОДЕКС (выжимка лучших практик индустрии — Reve 2.0, Sora, Veo, Imagen, Midjourney, SDXL/FLUX):
1. Структура положительного промпта: СУБЪЕКТ -> ДЕЙСТВИЕ -> СРЕДА -> КОМПОЗИЦИЯ/СВЕТ -> СТИЛЬ -> ТЕХНИКА.
2. Конкретные существительные и глаголы вместо абстракций ("рыжий кот спит на клавиатуре", а не "красиво").
3. Один кадр = одна идея. Не перегружай (для фотографий 25-60 слов, для видео 40-80).
4. Свет и оптика продают кадр: 35mm/85mm, volumetric light, golden hour, rim light, softbox.
5. Стиль одним блоком (например: "cinematic film still, anamorphic, 35mm, film grain").
6. В кадре НЕ должно быть текста/надписей/водяных знаков, если человек явно не попросил.
7. Video-промпт: описание сцены + движение камеры (slow dolly-in, pan left, static) + движение субъекта + атмосфера. Без монтажных склеек внутри одного промпта.
8. Negative-промпт (для SD/ComfyUI): стандартный мусор + спец-артефакты под задачу.
9. МЕТОД REVE (layout->render): дополнительно разложи кадр на 6-10 блоков-зон: block (название зоны), bbox [x,y,w,h] в долях 0..1 от кадра, content (что в зоне). Это структурный скелет кадра.
10. Никогда не упоминай в промпте, что он сгенерирован ИИ.

Ответь ТОЛЬКО валидным JSON по схеме:
{"positive": "<english prompt>", "negative": "<english negative prompt>",
 "layout": [{"block": "...", "bbox": [0.0,0.0,0.5,1.0], "content": "..."}],
 "variants": ["<короткий альтернативный вариант промпта 1>", "<вариант 2>"],
 "notes": "<1 предложение на русском: почему так составлено>"}"""

    def compose_llm(self, spec: TaskSpec, shot_desc: str = "") -> dict:
        user = (
            f"ЗАДАНИЕ ЧЕЛОВЕКА: {spec.goal or spec.raw}\n"
            f"СТИЛЬ: {spec.style}\n"
            f"ФОРМАТ КАДРА: {spec.aspect}\n"
            f"РЕЖИМ: {spec.mode}"
            + (f"\nОПИСАНИЕ ЭТОГО КАДРА РАСКАДРОВКИ: {shot_desc}" if shot_desc else "")
            + (f"\nСВЕТ: {spec.lighting}" if spec.lighting else "")
            + (f"\nНАСТРОЕНИЕ: {spec.mood}" if spec.mood else "")
            + (f"\nКАМЕРА: {spec.camera}" if spec.camera else "")
            + (f"\nДВИЖЕНИЕ: {spec.motion}" if spec.motion else "")
        )
        try:
            raw = self.llm.chat(user, system=self.SYSTEM_PROMPT, json_mode=True)
            data = self.llm.extract_json(raw) if hasattr(self.llm, "extract_json") else json.loads(raw)
            if not isinstance(data, dict) or not data.get("positive"):
                raise ValueError("bad LLM json")
            data.setdefault("negative", NEG_CORE)
            data.setdefault("layout", _layout_fallback(spec, shot_desc))
            data.setdefault("variants", [])
            data.setdefault("notes", "")
            return data
        except Exception:
            return self.compose_deterministic(spec, shot_desc)

    def compose(self, spec: TaskSpec, shot_desc: str = "") -> dict:
        if self.llm is not None and self.llm.available:
            return self.compose_llm(spec, shot_desc)
        return self.compose_deterministic(spec, shot_desc)

    # ---------- доработка по замечаниям критика ----------
    def refine(self, previous: dict, critique: dict, spec: TaskSpec) -> dict:
        hints = "; ".join(map(str, critique.get("fix_hints") or critique.get("problems") or []))
        if self.llm is None or not self.llm.available or not hints:
            merged = dict(previous)
            merged["positive"] = previous["positive"] + ", improved composition, refined details, better lighting"
            return merged
        user = (f"ЗАДАНИЕ: {spec.goal or spec.raw}\n\nПРОМПТ (предыдущая попытка):\n"
                f"{previous['positive']}\n\nКРИТИК-ГЛАЗА нашёл проблемы: {hints}\n\n"
                "Исправь промпт так, чтобы устранить эти проблемы. Сохрани замысел задания. "
                "Итоговый промпт — ТОЛЬКО на английском языке. "
                "Ответь ТОЛЬКО JSON: {\"positive\": \"...\", \"negative\": \"...\", \"notes\": \"...\"}")
        try:
            raw = self.llm.chat(user, system=self.SYSTEM_PROMPT, json_mode=True)
            data = self.llm.extract_json(raw)
            if not data.get("positive"):
                raise ValueError
            merged = dict(previous)
            merged.update({k: data[k] for k in ("positive", "negative", "notes") if k in data})
            return merged
        except Exception:
            return self.compose_deterministic(spec)


def _layout_fallback(spec: TaskSpec, shot_desc: str = "") -> list:
    """Метод Reve layout->render: структурный скелет кадра из 8 зон (0..1)."""
    src = shot_desc or spec.goal or spec.raw
    return [
        {"block": "sky/background", "bbox": [0.0, 0.0, 1.0, 0.4], "content": "фон, атмосфера, дальний план"},
        {"block": "environment-left", "bbox": [0.0, 0.2, 0.45, 0.6], "content": "левая часть среды из задания"},
        {"block": "environment-right", "bbox": [0.55, 0.2, 0.45, 0.6], "content": "правая часть среды из задания"},
        {"block": "main-subject", "bbox": [0.3, 0.25, 0.4, 0.6], "content": "главный объект: " + src[:120]},
        {"block": "midground", "bbox": [0.1, 0.5, 0.8, 0.3], "content": "средний план, детали"},
        {"block": "foreground", "bbox": [0.0, 0.75, 1.0, 0.25], "content": "передний план, глубина"},
        {"block": "light-source", "bbox": [0.35, 0.0, 0.3, 0.3], "content": "ключевой источник света"},
        {"block": "atmosphere", "bbox": [0.0, 0.0, 1.0, 1.0], "content": "туман/частицы/цветокоррекция"},
    ]


def load_patterns() -> dict:
    p = os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "patterns.json")
    try:
        with open(os.path.abspath(p), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
