"""Оркестратор — цикл автономии ПОЛИМАТ-ГЕН:

  задание -> план (раскадровка) -> [промпт -> генерация -> критика -> доработка] x N
          -> сборка (контактный лист / видео) -> отчёт прогона state.json
"""
import datetime
import json
import os
import shutil
import time
from .task import TaskSpec
from .planner import Planner
from .prompt_engine import PromptEngine, size_for
from .critic import Critic
from ..backends import registry


def _now() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


class Orchestrator:
    def __init__(self, llm=None, out_dir="runs", rounds=2, threshold=7,
                 image_backend="auto", video_backend="auto", critic_enabled=True,
                 comfy_workflow=None, verbose=True):
        self.llm = llm
        self.out_dir = out_dir
        self.rounds = max(1, rounds)
        self.threshold = threshold
        self.image_backend = image_backend
        self.video_backend = video_backend
        self.comfy_workflow = comfy_workflow
        self.verbose = verbose
        self.engine = PromptEngine(llm)
        self.planner = Planner(llm)
        self.critic = Critic(llm, enabled=critic_enabled, threshold=threshold)

    def log(self, *a):
        if self.verbose:
            print(*a, flush=True)

    def run(self, spec: TaskSpec) -> dict:
        run_dir = os.path.join(self.out_dir, _now())
        os.makedirs(run_dir, exist_ok=True)
        report = {"started": _now(), "task": spec.to_dict(), "steps": [], "outputs": []}

        kind = "image" if spec.mode in ("image", "storyboard") else "video"
        self.log(f"🧠 Режим: {spec.mode} | Мозг: {self.llm.name if self.llm and self.llm.available else '— (fallback)'}")

        if spec.mode == "video":
            return self._run_video(spec, run_dir, report)

        backend = registry.pick("image", self.image_backend)
        self.log(f"🖐 Бэкенд картинок: {backend.name}")
        shots = self.planner.plan(spec)
        keyframes = []
        for shot in shots:
            desc = shot.get("desc", spec.goal)
            keyframe = self._one_shot(spec, backend, shot, run_dir, report)
            if keyframe:
                keyframes.append(keyframe)

        if spec.mode == "storyboard" and len(keyframes) >= 2:
            self.log("🎬 Собираю видео из ключевых кадров (ffmpeg xfade)...")
            try:
                fb = registry.VIDEO_BACKENDS["ffmpeg"]()
                mp4 = os.path.join(run_dir, "storyboard.mp4")
                fb.generate(keyframes, mp4)
                report["outputs"].append(mp4)
                self.log(f"   ✅ {mp4}")
            except Exception as e:
                self.log(f"   ⚠️ ffmpeg: {e}")

        if len(keyframes) > 1:
            sheet = os.path.join(run_dir, "contact_sheet.png")
            try:
                _contact_sheet(keyframes, sheet)
                report["outputs"].append(sheet)
            except Exception as e:
                self.log(f"   ⚠️ контактный лист: {e}")

        report["finished"] = _now()
        report["outputs"] += keyframes
        with open(os.path.join(run_dir, "state.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        self.log(f"📦 Готово: {run_dir}")
        return report

    def _one_shot(self, spec: TaskSpec, backend, shot: dict, run_dir: str, report: dict) -> str:
        desc = shot.get("desc", "")
        prompt = self.engine.compose(spec, desc)
        prev = None
        best = None
        for attempt in range(1, self.rounds + 1):
            img_path = os.path.join(run_dir, f"shot{shot.get('idx', 1)}_r{attempt}.png")
            size, _, _ = size_for(spec.aspect)
            self.log(f"🎨 Кадр {shot.get('idx', 1)} / попытка {attempt}: {prompt['positive'][:110]}...")
            t0 = time.time()
            kwargs = dict(size=size)
            if backend.name == "comfy":
                kwargs["workflow_path"] = self.comfy_workflow
                kwargs["negative"] = prompt["negative"]
            elif backend.name == "a1111":
                kwargs["negative"] = prompt["negative"]
            backend.generate(prompt["positive"], img_path, **kwargs)
            dt = time.time() - t0
            verdict = self.critic.judge(img_path, spec.goal or spec.raw, prompt["positive"])
            self.log(f"   👁 Критик: {verdict['score']}/10 ({verdict.get('reviewer')}) "
                     f"{'; '.join(verdict.get('problems', [])[:2])} [{dt:.1f}s]")
            report["steps"].append({"shot": shot.get("idx", 1), "attempt": attempt,
                                    "prompt": prompt["positive"], "negative": prompt.get("negative", ""),
                                    "layout": prompt.get("layout", []), "image": img_path,
                                    "critic": verdict, "seconds": round(dt, 1)})
            if verdict["score"] >= self.threshold:
                return img_path
            best = img_path
            prompt = self.engine.refine(prompt, verdict, spec)
        return best  # лучшая из доступных попыток

    def _run_video(self, spec: TaskSpec, run_dir: str, report: dict) -> dict:
        backend = registry.pick("video", self.video_backend)
        self.log(f"🖐 Бэкенд видео: {backend.name}")
        prompt = self.engine.compose(spec)
        mp4 = os.path.join(run_dir, "video.mp4")
        self.log(f"🎬 Промпт видео: {prompt['positive'][:140]}...")
        t0 = time.time()
        backend.generate(prompt["positive"], mp4, duration=spec.duration,
                         fps=spec.fps, audio=spec.audio, size="1920x1080")
        report["steps"].append({"video_prompt": prompt, "video": mp4, "seconds": round(time.time() - t0, 1)})
        report["outputs"].append(mp4)
        with open(os.path.join(run_dir, "state.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        self.log(f"📦 Готово: {mp4}")
        return report


def _contact_sheet(paths, out, cols=2, cell_w=672):
    from PIL import Image, ImageDraw
    thumbs = []
    for p in paths:
        im = Image.open(p).convert("RGB")
        im.thumbnail((cell_w - 12, cell_w - 12))
        thumbs.append((p, im))
    rows = (len(thumbs) + cols - 1) // cols
    row_h = []
    for r in range(rows):
        row_items = thumbs[r * cols:(r + 1) * cols]
        row_h.append(max(im.height for _, im in row_items) + 26)
    sheet = Image.new("RGB", (cols * cell_w, sum(row_h)), "#0d0f14")
    d = ImageDraw.Draw(sheet)
    y = 0
    for r in range(rows):
        for c in range(cols):
            i = r * cols + c
            if i >= len(thumbs):
                break
            p, im = thumbs[i]
            x = c * cell_w + (cell_w - im.width) // 2
            sheet.paste(im, (x, y + 4))
            d.text((c * cell_w + 10, y + im.height + 8),
                   os.path.basename(p), fill="#8fa3c8")
        y += row_h[r]
    sheet.save(out)
    return out
