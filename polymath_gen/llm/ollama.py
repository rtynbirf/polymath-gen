"""Мозг-2: локальная LLM через Ollama (полная автономность без облака).

pip/установка: https://ollama.com  ->  ollama pull qwen2.5:7b  (текст)
             ollama pull qwen2.5vl:7b (глаза-критик)
"""
import base64
import json
import os
import urllib.request


class OllamaLLM:
    name = "ollama"

    def __init__(self, model="qwen2.5:7b", vision_model="qwen2.5vl:7b", base_url=None):
        self.model = model
        self.vision_model = vision_model
        self.base = base_url or os.environ.get("PMG_OLLAMA_URL", "http://127.0.0.1:11434")

    @property
    def available(self) -> bool:
        try:
            with urllib.request.urlopen(self.base + "/api/tags", timeout=1.5) as r:
                return r.status == 200
        except Exception:
            return False

    def _chat(self, model, messages):
        payload = json.dumps({"model": model, "messages": messages, "stream": False}).encode()
        req = urllib.request.Request(self.base + "/api/chat", data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=600) as r:
            data = json.loads(r.read().decode())
        return data["message"]["content"]

    def chat(self, prompt: str, system: str = None, json_mode: bool = False) -> str:
        if json_mode:
            system = (system or "") + "\nВЕРХОВНОЕ ПРАВИЛО: ответ — ТОЛЬКО валидный JSON, без markdown."
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
        return self._chat(self.model, msgs)

    def vision(self, image_path: str, prompt: str) -> str:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        msgs = [{"role": "user", "content": prompt, "images": [b64]}]
        return self._chat(self.vision_model, msgs)

    def extract_json(self, text):
        from .zai import extract_json
        return extract_json(text)
