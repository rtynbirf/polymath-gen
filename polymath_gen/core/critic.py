"""Мозг-2: критик-«глаза». VLM смотрит на результат и оценивает соответствие заданию.

Без VLM возвращает нейтрально-положительную оценку (можно выключить: --no-critic).
"""
import json
from ..llm.zai import extract_json

CRITIC_PROMPT = """Ты — строгий арт-директор и контролёр качества генеративного медиа-агента.
Сравни изображение с заданием человека.

ЗАДАНИЕ: {task}
ПРОМПТ, по которому сгенерировано: {prompt}

Оцени по критериям: соответствие заданию, композиция, свет, анатомия/геометрия, артефакты, текст-в-кадре (должен отсутствовать, если не просили).

Ответь ТОЛЬКО валидным JSON:
{{"score": <целое 1-10>, "ok": <true если score>=7>,
  "problems": ["конкретная проблема 1", "..."],
  "fix_hints": ["что исправить в промпте 1", "..."]}}"""


class Critic:
    def __init__(self, llm=None, enabled=True, threshold=7):
        self.llm = llm          # объект с .vision() или None
        self.enabled = enabled and llm is not None
        self.threshold = threshold

    def judge(self, image_path: str, task_text: str, prompt_text: str) -> dict:
        if not self.enabled or not getattr(self.llm, "available", False):
            return {"score": 10, "ok": True, "problems": [], "fix_hints": [], "reviewer": "disabled"}
        try:
            raw = self.llm.vision(image_path, CRITIC_PROMPT.format(task=task_text, prompt=prompt_text))
            data = extract_json(raw)
            data.setdefault("score", 5)
            data["ok"] = bool(data.get("ok", data["score"] >= self.threshold))
            data["reviewer"] = getattr(self.llm, "name", "vlm")
            return data
        except Exception as e:
            return {"score": 8, "ok": True, "problems": [f"критик недоступен: {e}"],
                    "fix_hints": [], "reviewer": "error-fallback"}
