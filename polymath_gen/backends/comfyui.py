"""Руки-3: локальный ComfyUI — FLUX.1-schnell / SDXL / Wan 2.2 (100% open-source, офлайн).

Запуск ComfyUI: python main.py --listen 127.0.0.1 --port 8188
Workflows (API-формат) лежат в /workflows, плейсхолдеры: {{POSITIVE}} {{NEGATIVE}} {{W}} {{H}} {{SEED}} {{IMAGE_URL_B64}}
"""
import copy
import json
import time
import urllib.request
import urllib.parse

DEFAULT_URL = "http://127.0.0.1:8188"


class ComfyUIBackend:
    name = "comfy"
    kind = "image+video"

    def __init__(self, url=None, timeout=900):
        self.url = (url or DEFAULT_URL).rstrip("/")
        self.timeout = timeout

    @property
    def available(self) -> bool:
        try:
            with urllib.request.urlopen(self.url + "/system_stats", timeout=2) as r:
                return r.status == 200
        except Exception:
            return False

    def generate(self, prompt: str, out_path: str, workflow_path: str,
                 negative: str = "", width=1344, height=768, seed=None, **kw) -> str:
        with open(workflow_path, encoding="utf-8") as f:
            wf = json.load(f)
        wf = json.loads(json.dumps(wf).replace("{{POSITIVE}}", prompt)
                        .replace("{{NEGATIVE}}", negative)
                        .replace("{{W}}", str(width)).replace("{{H}}", str(height))
                        .replace("{{SEED}}", str(seed if seed is not None else _rand_seed())))
        client_id = "polymath-gen"
        req = urllib.request.Request(self.url + "/prompt",
                                     data=json.dumps({"prompt": wf, "client_id": client_id}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            pid = json.loads(r.read().decode())["prompt_id"]
        t0 = time.time()
        while time.time() - t0 < self.timeout:
            with urllib.request.urlopen(f"{self.url}/history/{pid}", timeout=30) as r:
                hist = json.loads(r.read().decode())
            if pid in hist and hist[pid].get("outputs"):
                outputs = hist[pid]["outputs"]
                for node in outputs.values():
                    for img in node.get("images", []):
                        q = urllib.parse.urlencode({"filename": img["filename"],
                                                    "subfolder": img.get("subfolder", ""),
                                                    "type": img.get("type", "output")})
                        with urllib.request.urlopen(f"{self.url}/view?{q}", timeout=120) as r:
                            data = r.read()
                        with open(out_path, "wb") as f:
                            f.write(data)
                        return out_path
                break
            time.sleep(1.5)
        raise RuntimeError(f"ComfyUI: таймаут/нет результата ({self.url})")


def _rand_seed():
    import random
    return random.randint(0, 2**31 - 1)
