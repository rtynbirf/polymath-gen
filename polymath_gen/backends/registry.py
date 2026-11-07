"""Реестр бэкендов: выбор «рук» по конфигу и доступности."""
from .zai_image import ZaiImageBackend
from .zai_video import ZaiVideoBackend
from .comfyui import ComfyUIBackend
from .a1111 import A1111Backend
from .ffmpeg_video import FFmpegVideoBackend

IMAGE_BACKENDS = {"zai": ZaiImageBackend, "comfy": ComfyUIBackend, "a1111": A1111Backend}
VIDEO_BACKENDS = {"zai-video": ZaiVideoBackend, "ffmpeg": FFmpegVideoBackend}


def pick(kind: str, preferred: str = "auto"):
    """kind: image | video. preferred: auto | имя бэкенда."""
    table = IMAGE_BACKENDS if kind == "image" else VIDEO_BACKENDS
    if preferred and preferred in table:
        return table[preferred]()
    if preferred == "auto" or not preferred:
        # порядок приоритета: облако работает сразу -> локальные (если подняты)
        order = ["zai", "comfy", "a1111"] if kind == "image" else ["zai-video", "ffmpeg"]
        for name in order:
            inst = table[name]()
            if kind == "video" and name == "ffmpeg":
                continue  # ffmpeg требует готовых keyframes, выбирается явно
            if inst.available:
                return inst
        raise RuntimeError(f"Нет доступного бэкенда для {kind}. "
                           f"Подняйте ComfyUI/A1111 локально (scripts/install_local_stack) "
                           f"или используйте окружение с z-ai CLI.")
    raise ValueError(f"Неизвестный бэкенд: {preferred}")
