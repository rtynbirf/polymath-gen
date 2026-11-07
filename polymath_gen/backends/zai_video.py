"""Руки-2: генерация видео через z-ai CLI (t2v и i2v, со звуком по флагу)."""
import json
import os
import subprocess
import urllib.request


class ZaiVideoBackend:
    name = "zai-video"
    kind = "video"

    @property
    def available(self) -> bool:
        import shutil
        return shutil.which("z-ai") is not None

    def generate(self, prompt: str, out_path: str, size: str = "1920x1080",
                 duration: int = 5, fps: int = 30, audio: bool = False,
                 image_url: str = None, quality: str = "speed", **kw) -> str:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        cmd = ["z-ai", "video", "-p", prompt, "--poll", "--max-polls", "80",
               "--size", size, "-d", str(duration), "--fps", str(fps)]
        if audio:
            cmd.append("--with-audio")
        if image_url:
            cmd += ["--image-url", image_url]
        if quality == "quality":
            cmd += ["-q", "quality"]
        result_json = out_path + ".result.json"
        cmd += ["-o", result_json]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=1500)
        if p.returncode != 0:
            raise RuntimeError(f"z-ai video failed: {p.stderr[-300:]}")
        url = _find_video_url(_load(result_json))
        if not url:
            raise RuntimeError("z-ai video: URL видео не найден в ответе")
        urllib.request.urlretrieve(url, out_path)
        if not os.path.exists(out_path) or os.path.getsize(out_path) < 50_000:
            raise RuntimeError("z-ai video: файл пустой")
        return out_path


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _find_video_url(obj):
    """Рекурсивный поиск первого URL, похожего на видео."""
    if isinstance(obj, dict):
        for v in obj.values():
            u = _find_video_url(v)
            if u:
                return u
    elif isinstance(obj, list):
        for v in obj:
            u = _find_video_url(v)
            if u:
                return u
    elif isinstance(obj, str) and obj.startswith("http") and \
            any(ext in obj.lower() for ext in (".mp4", "video", ".mov", ".webm")):
        return obj
    return None
