"""Оффлайн-тесты ядра (без сети). Запуск: pytest -q"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from polymath_gen.core.task import parse_task, TaskSpec          # noqa: E402
from polymath_gen.core.prompt_engine import PromptEngine, size_for, _translate  # noqa: E402
from polymath_gen.llm.zai import extract_json                    # noqa: E402


def test_parse_task_string_detects_mode():
    assert parse_task("видео: кот играет").mode == "video"
    assert parse_task("сториборд сцены").mode == "storyboard"
    assert parse_task("ночной дата-центр").mode == "image"


def test_parse_task_yaml_fields():
    spec = parse_task({"goal": "тест", "style": "noir", "aspect": "9:16", "mode": "image"})
    assert spec.style == "noir" and spec.aspect == "9:16"


def test_translate_russian_to_english():
    assert "data center" in _translate("ночной дата-центр")
    assert "neon" in _translate("неоновый город")
    assert "cinematic" in _translate("кинематографично")


def test_deterministic_compose_structure():
    eng = PromptEngine(llm=None)
    spec = parse_task("Ночной дата-центр, ряды стоек GPU, оранжевая подсветка")
    out = eng.compose_deterministic(spec)
    assert set(out) >= {"positive", "negative", "layout"}
    assert "data center" in out["positive"]
    assert "watermark" in out["negative"]
    assert len(out["layout"]) == 8


def test_layout_reve_blocks_have_bbox():
    eng = PromptEngine(llm=None)
    out = eng.compose_deterministic(parse_task("дракон над замком"))
    for blk in out["layout"]:
        assert set(blk) == {"block", "bbox", "content"}
        assert len(blk["bbox"]) == 4
        assert all(0.0 <= v <= 1.0 for v in blk["bbox"])


def test_size_map():
    assert size_for("16:9")[0] == "1344x768"
    assert size_for("9:16")[0] == "768x1344"
    assert size_for("unknown")[0] == "1344x768"


def test_extract_json_robust():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('мусор до {"a": {"b": 2}} мусор после') == {"a": {"b": 2}}


def test_refine_without_llm_appends_hint():
    eng = PromptEngine(llm=None)
    prev = {"positive": "a cat", "negative": "x", "notes": ""}
    verdict = {"problems": ["пересвечено"], "fix_hints": ["убрать пересвет"]}
    out = eng.refine(prev, verdict, parse_task("кот"))
    assert out["positive"].startswith("a cat")
    assert "improved composition" in out["positive"]


def test_task_spec_defaults():
    spec = TaskSpec()
    assert spec.mode == "image" and spec.aspect == "16:9"
    assert spec.to_dict()["duration"] == 5
