"""Задание человека -> спецификация TaskSpec."""
from dataclasses import dataclass, field, asdict
from typing import List, Optional
import re


@dataclass
class TaskSpec:
    raw: str = ""                 # исходный текст задания (как написал человек)
    goal: str = ""                # что нужно получить
    subject: str = ""             # главный объект
    action: str = ""              # что происходит
    environment: str = ""         # где / фон / обстановка
    style: str = "cinematic"      # стиль (ключ из style_library или свободный текст)
    lighting: str = ""            # свет
    mood: str = ""                # настроение
    camera: str = ""              # план/движение камеры (видео)
    motion: str = ""              # движение субъекта (видео)
    aspect: str = "16:9"          # соотношение сторон
    mode: str = "image"           # image | video | storyboard
    duration: int = 5             # длительность видео, сек (5|10)
    fps: int = 30                 # 30|60
    audio: bool = False           # AI-звук для видео
    negatives: List[str] = field(default_factory=list)
    ref_images: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


_VIDEO_HINTS = re.compile(r"\b(видео|video|ролик|анимация|клип|сцена в движении)\b", re.I)
_STORY_HINTS = re.compile(r"\b(сториборд|storyboard|раскадровка|комикс-панели)\b", re.I)


def parse_task(data) -> TaskSpec:
    """Принимает dict (yaml/json) или строку текста -> TaskSpec."""
    if isinstance(data, str):
        raw = data.strip()
        mode = "video" if _VIDEO_HINTS.search(raw) else ("storyboard" if _STORY_HINTS.search(raw) else "image")
        spec = TaskSpec(raw=raw, goal=raw, mode=mode)
        return spec
    d = dict(data)
    raw = str(d.get("goal") or d.get("task") or d.get("raw") or "").strip()
    mode = str(d.get("mode") or "").lower()
    if not mode:
        mode = "video" if _VIDEO_HINTS.search(raw) else ("storyboard" if _STORY_HINTS.search(raw) else "image")
    return TaskSpec(
        raw=str(d.get("raw") or raw),
        goal=raw,
        subject=str(d.get("subject", "")),
        action=str(d.get("action", "")),
        environment=str(d.get("environment", "")),
        style=str(d.get("style") or "cinematic"),
        lighting=str(d.get("lighting", "")),
        mood=str(d.get("mood", "")),
        camera=str(d.get("camera", "")),
        motion=str(d.get("motion", "")),
        aspect=str(d.get("aspect") or "16:9"),
        mode=mode,
        duration=int(d.get("duration") or 5),
        fps=int(d.get("fps") or 30),
        audio=bool(d.get("audio") or False),
        negatives=list(d.get("negatives") or []),
        ref_images=list(d.get("ref_images") or []),
    )
