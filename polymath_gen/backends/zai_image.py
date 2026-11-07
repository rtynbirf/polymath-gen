"""Руки-1: генерация картинок через z-ai CLI (облако, работает из коробки)."""
import os
import subprocess


class ZaiImageBackend:
    name = "zai"
    kind = "image"

    @property
    def available(self) -> bool:
        import shutil
        return shutil.which("z-ai") is not None

    def generate(self, prompt: str, out_path: str, size: str = "1344x768",
                 negative: str = None, **kw) -> str:
        # у z-ai нет отдельного negative — мягкая инструкция в хвост промпта
        full = prompt if not negative else f"{prompt}. Avoid: {negative.split(',')[0:4]}"
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        cmd = ["z-ai", "image", "-p", full, "-o", out_path, "-s", size]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if p.returncode != 0:
            raise RuntimeError(f"z-ai image failed: {p.stderr[-300:]}")
        if not os.path.exists(out_path) or os.path.getsize(out_path) < 10_000:
            raise RuntimeError("z-ai image: файл не создан/пустой")
        return out_path
