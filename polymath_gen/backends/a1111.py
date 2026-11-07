"""Руки-4: локальный AUTOMATIC1111 / Forge WebUI API (SDXL и др., офлайн).

Запуск: ./webui.sh --api   (или webui-user.bat с --api на Windows)
"""
import base64
import json
import urllib.request

DEFAULT_URL = "http://127.0.0.1:7860"


class A1111Backend:
    name = "a1111"
    kind = "image"

    def __init__(self, url=None, timeout=900):
        self.url = (url or DEFAULT_URL).rstrip("/")
        self.timeout = timeout

    @property
    def available(self) -> bool:
        try:
            with urllib.request.urlopen(self.url + "/sdapi/v1/options", timeout=2) as r:
                return r.status == 200
        except Exception:
            return False

    def generate(self, prompt: str, out_path: str, negative: str = "",
                 width=1344, height=768, steps=30, cfg_scale=7, seed=-1, **kw) -> str:
        payload = {
            "prompt": prompt, "negative_prompt": negative,
            "width": width, "height": height, "steps": steps,
            "cfg_scale": cfg_scale, "sampler_name": "DPM++ 2M Karras", "seed": seed,
        }
        req = urllib.request.Request(self.url + "/sdapi/v1/txt2img",
                                     data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            data = json.loads(r.read().decode())
        images = data.get("images") or []
        if not images:
            raise RuntimeError("A1111: пустой ответ")
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(images[0]))
        return out_path
