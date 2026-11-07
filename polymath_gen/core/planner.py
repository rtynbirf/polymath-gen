"""Планировщик: разбивает задание на шоты (кадры/сцены).

image      -> 1 шот
storyboard -> 3-4 ключевых кадра (LLM или шаблон)
video      -> 1 шот с описанием движения (прямая генерация видео)
"""
import json
from .task import TaskSpec

_KEYFRAME_TMPL = [
    ("установочный кадр, общий план", "wide establishing shot"),
    ("средний план, развитие действия", "medium shot, action develops"),
    ("крупный план, кульминация", "close-up, climax"),
    ("финальный кадр, развязка", "final shot, resolution"),
]


class Planner:
    def __init__(self, llm=None):
        self.llm = llm

    def plan(self, spec: TaskSpec):
        if spec.mode == "storyboard":
            return self._keyframes(spec)
        return [{"idx": 1, "desc": spec.goal or spec.raw, "motion": spec.motion or ""}]

    def _keyframes(self, spec: TaskSpec):
        n = 4
        if self.llm is not None and self.llm.available:
            try:
                sys = ("Ты режиссёр-постановщик. Разбей задание на {} ключевых кадра раскадровки. "
                       "Ответь ТОЛЬКО валидным JSON без markdown: "
                       '{{"keyframes":[{{"ru":"краткое описание кадра на русском",'
                       '"en":"detailed english shot description, camera, lighting"}},...]}}').format(n)
                out = self.llm.chat(
                    f"ЗАДАНИЕ: {spec.goal or spec.raw}\nСТИЛЬ: {spec.style}",
                    system=sys, json_mode=True)
                data = json.loads(out)
                kf = data.get("keyframes") or []
                shots = []
                for i, k in enumerate(kf[:n]):
                    shots.append({"idx": i + 1, "desc": k.get("ru", ""), "motion": k.get("en", "")})
                if shots:
                    return shots
            except Exception:
                pass  # тихо падаем на шаблон
        return [{"idx": i + 1, "desc": f"{spec.goal or spec.raw} — {ru}", "motion": en}
                for i, (ru, en) in enumerate(_KEYFRAME_TMPL[:n])]
