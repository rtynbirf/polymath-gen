"""Мозг-1: LLM через z-ai CLI (облако, работает сразу) — chat + vision."""
import json
import os
import re
import shutil
import subprocess
import tempfile


class ZaiLLM:
    name = "zai"

    def __init__(self):
        self._bin = shutil.which("z-ai")

    @property
    def available(self) -> bool:
        return self._bin is not None

    def _run(self, args):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            out_path = f.name
        try:
            cmd = [self._bin] + args + ["--output", out_path]
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if p.returncode != 0 or not os.path.exists(out_path):
                raise RuntimeError(f"z-ai failed: {p.stderr[-400:]}")
            with open(out_path, encoding="utf-8") as f:
                data = json.load(f)
            return data["choices"][0]["message"]["content"]
        finally:
            try:
                os.unlink(out_path)
            except OSError:
                pass

    def chat(self, prompt: str, system: str = None, json_mode: bool = False) -> str:
        args = ["chat", "-p", prompt]
        if system:
            if json_mode:
                system = system + "\nВЕРХОВНОЕ ПРАВИЛО: ответ — ТОЛЬКО валидный JSON, без markdown, без ```."
            args += ["--system", system]
        elif json_mode:
            args += ["--system", "Ответь ТОЛЬКО валидным JSON, без markdown, без ```."]
        return self._run(args)

    def vision(self, image_path: str, prompt: str) -> str:
        return self._run(["vision", "-p", prompt, "-i", image_path])

    def extract_json(self, text: str):
        return extract_json(text)


def extract_json(text: str):
    """Достаёт первый валидный JSON-объект из ответа LLM (устойчиво к ``` и мусору)."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    return json.loads(text[start:i + 1])
                except Exception:
                    start = None
    raise ValueError("JSON не найден в ответе модели")
