"""Руки-5: сборка видео из ключевых кадров через ffmpeg (xfade + zoompan) — сториборд/анимация.

Это честная «бюджетная» видеотраектория: 3-4 кадра -> живой ролик с плавными
переходами и лёгким наездом камеры. Настоящее генеративное видео —
backends/zai_video.py (облако) или ComfyUI + Wan 2.2 (локально, см. workflows/).
"""
import os
import subprocess
import tempfile


class FFmpegVideoBackend:
    name = "ffmpeg"
    kind = "video"

    def generate(self, keyframes, out_path: str, width=1344, height=768,
                 per_shot: float = 1.6, fade: float = 0.6, fps: int = 30, **kw) -> str:
        assert len(keyframes) >= 2, "нужно >=2 ключевых кадров"
        dur = per_shot + fade
        inputs = []
        for k in keyframes:
            inputs += ["-loop", "1", "-t", f"{dur:.2f}", "-i", k]
        filters = []
        for i in range(len(keyframes)):
            # лёгкий наезд камеры (zoompan) + единый размер
            filters.append(
                f"[{i}:v]scale={width*2}:{height*2},"
                f"zoompan=z='min(zoom+0.0008,1.12)':d=1:s={width}x{height}:fps={fps},"
                f"setsar=1,format=yuv420p[v{i}]")
        cur = "v0"
        t = per_shot
        for i in range(1, len(keyframes)):
            outlbl = f"x{i}"
            filters.append(f"[{cur}][v{i}]xfade=transition=fade:duration={fade}:offset={t:.2f}[{outlbl}]")
            cur = outlbl
            t += per_shot
        filters[-1] = filters[-1].replace(f"[{outlbl}]", f"[{outlbl}]", 1)
        cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters),
               "-map", f"[{cur}]", "-c:v", "libx264", "-preset", "veryfast",
               "-crf", "21", "-r", str(fps), "-movflags", "+faststart", out_path]
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if p.returncode != 0 or not os.path.exists(out_path):
            raise RuntimeError("ffmpeg failed: " + p.stderr[-400:])
        return out_path
