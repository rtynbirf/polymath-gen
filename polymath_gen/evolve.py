#!/usr/bin/env python3
"""ЭВОЛЮЦИЯ ПОЛИМАТ-ГЕН: агент учится на памяти своих прогонов.

1. Собирает все runs/*/state.json (промпты, оценки критика, замечания).
2. Отдаёт LLM сводку лучших/худших опытов.
3. LLM предлагает новые правила-паттерны (JSON).
4. Новые правила дописываются в prompts/patterns.json -> brain становится умнее.

Запуск: python -m polymath_gen.evolve            (обычный прогон)
        python -m polymath_gen.evolve --dry      (только показать, не писать)
"""
import argparse
import datetime
import glob
import json
import os

from .llm.zai import ZaiLLM, extract_json

EVOLVE_SYSTEM = """Ты — эволюционный модуль автономного медиа-агента ПОЛИМАТ-ГЕН.
Тебе дают сводку его прошлых прогонов: задание, промпт, оценку критика-глаз и замечания.
Найди ЗАКОНОМЕРНОСТИ: почему низкие оценки, какие приёмы дали высокие.
Сформулируй 1-3 НОВЫХ правила промптинга, которых ещё нет в кодексе.
Ответь ТОЛЬКО валидным JSON:
{"insights": ["1 предложение на русском — вывод"],
 "new_patterns": [{"id": "kebab-case-id", "when": "когда применять", "rule": "правило для промпт-движка, на русском, 1-2 предложения"}]}"""


def collect_memory(runs_dir="runs"):
    memory = []
    for state_path in sorted(glob.glob(os.path.join(runs_dir, "*", "state.json"))):
        try:
            with open(state_path, encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            continue
        task = (state.get("task") or {}).get("goal", "?")
        for step in state.get("steps", []):
            memory.append({
                "task": task[:160],
                "prompt": (step.get("prompt") or "")[:220],
                "critic_score": (step.get("critic") or {}).get("score"),
                "critic_problems": (step.get("critic") or {}).get("problems", []),
                "video_prompt": bool(step.get("video_prompt")),
            })
    return memory


def evolve(runs_dir="runs", patterns_path=None, dry=False):
    llm = ZaiLLM()
    assert llm.available, "z-ai CLI недоступен"
    root = os.path.dirname(os.path.abspath(__file__))
    patterns_path = patterns_path or os.path.join(root, "..", "prompts", "patterns.json")

    memory = collect_memory(runs_dir)
    if not memory:
        print("🧬 Памяти пока нет (нет runs/*/state.json) — эволюция отложена.")
        return None

    with open(patterns_path, encoding="utf-8") as f:
        patterns = json.load(f)
    existing_ids = {p.get("id") for p in patterns.get("patterns", [])}

    scores = [m["critic_score"] for m in memory if m["critic_score"] is not None]
    summary = {
        "total_steps": len(memory),
        "avg_score": round(sum(scores) / len(scores), 2) if scores else None,
        "worst": sorted(memory, key=lambda m: m["critic_score"] or 10)[:3],
        "best": sorted(memory, key=lambda m: -(m["critic_score"] or 0))[:3],
        "existing_pattern_ids": sorted(existing_ids),
    }
    raw = llm.chat(json.dumps(summary, ensure_ascii=False), system=EVOLVE_SYSTEM, json_mode=True)
    data = extract_json(raw)
    new = [p for p in data.get("new_patterns", []) if p.get("id") not in existing_ids]

    print(f"🧬 Память: {len(memory)} шагов | средний балл критика: {summary['avg_score']}")
    for i in data.get("insights", []):
        print("   💡", i)
    if not new:
        print("🧬 Новых правил нет — кодекс уже покрывает наблюдения.")
        return None

    print("\nПЛАНИРУЕМЫЕ НОВЫЕ ПРАВИЛА:")
    for p in new:
        print(f"   + [{p['id']}] {p.get('when')} → {p.get('rule')}")

    if dry:
        return data

    patterns.setdefault("meta", {})["last_evolution"] = datetime.date.today().isoformat()
    patterns["meta"].setdefault("evolution_log", []).append({
        "date": datetime.date.today().isoformat(),
        "steps_analyzed": len(memory),
        "avg_score": summary["avg_score"],
        "added": [p["id"] for p in new],
        "insights": data.get("insights", []),
    })
    patterns["patterns"].extend(new)
    with open(patterns_path, "w", encoding="utf-8") as f:
        json.dump(patterns, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Кодекс обновлён: +{len(new)} правил → {patterns_path}")
    return data


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    evolve(dry=args.dry)
