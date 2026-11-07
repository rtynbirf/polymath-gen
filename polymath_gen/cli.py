"""ПОЛИМАТ-ГЕН CLI: задание человека -> готовый результат.

Примеры:
  python -m polymath_gen.cli examples/task.demo.yaml
  python -m polymath_gen.cli --text "Ночной дата-центр, ряды GPU, оранжевая подсветка" 
  python -m polymath_gen.cli examples/task.demo_video.yaml --rounds 3
"""
import argparse
import json
import sys

from .core.task import parse_task
from .core.orchestrator import Orchestrator


def _make_llm(pref: str):
    if pref == "none":
        return None
    from .llm.zai import ZaiLLM
    from .llm.ollama import OllamaLLM
    order = [pref] if pref in ("zai", "ollama") else ["zai", "ollama"]
    for name in order:
        inst = ZaiLLM() if name == "zai" else OllamaLLM()
        if inst.available:
            return inst
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="polymath-gen",
                                 description="Автономный медиа-агент: задание -> промпт -> результат")
    ap.add_argument("task", nargs="?", help="yaml/json файл задания")
    ap.add_argument("--text", help="задание прямо строкой")
    ap.add_argument("--mode", choices=["image", "video", "storyboard"], help="переопределить режим")
    ap.add_argument("--backend", default="auto", help="zai | comfy | a1111 | auto (картинки)")
    ap.add_argument("--video-backend", default="auto", help="zai-video | ffmpeg | auto")
    ap.add_argument("--llm", default="auto", choices=["auto", "zai", "ollama", "none"])
    ap.add_argument("--rounds", type=int, default=2, help="попыток на кадр (с самокритикой)")
    ap.add_argument("--threshold", type=int, default=7, help="порог критика 1-10")
    ap.add_argument("--no-critic", action="store_true")
    ap.add_argument("--out", default="runs", help="каталог прогонов")
    ap.add_argument("--comfy-workflow", default=None, help="json workflow для ComfyUI")
    args = ap.parse_args(argv)

    if not args.task and not args.text:
        ap.error("нужно задание: файл или --text")

    if args.task:
        import os
        with open(args.task, encoding="utf-8") as f:
            data = f.read()
        if args.task.endswith((".yaml", ".yml")):
            import yaml
            data = yaml.safe_load(data)
        else:
            data = json.loads(data)
        spec = parse_task(data)
    else:
        spec = parse_task(args.text)
    if args.mode:
        spec.mode = args.mode

    llm = _make_llm(args.llm)
    orch = Orchestrator(llm=llm, out_dir=args.out, rounds=args.rounds,
                        threshold=args.threshold, image_backend=args.backend,
                        video_backend=args.video_backend, critic_enabled=not args.no_critic,
                        comfy_workflow=args.comfy_workflow)
    report = orch.run(spec)
    print(json.dumps({"outputs": report["outputs"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
