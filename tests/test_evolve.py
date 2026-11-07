"""Оффлайн-тесты эволюции памяти. Запуск: pytest -q"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from polymath_gen.evolve import collect_memory   # noqa: E402


def test_collect_memory_reads_states(tmp_path):
    run = tmp_path / "run1"
    run.mkdir()
    (run / "state.json").write_text(json.dumps({
        "task": {"goal": "тест задача"},
        "steps": [{"prompt": "p1", "critic": {"score": 5, "problems": ["туман густой"]}},
                  {"prompt": "p2", "critic": {"score": 8, "problems": []}}],
    }), encoding="utf-8")
    mem = collect_memory(str(tmp_path))
    assert len(mem) == 2
    assert mem[0]["critic_score"] == 5
    assert "туман" in mem[0]["critic_problems"][0]


def test_collect_memory_empty_dir(tmp_path):
    assert collect_memory(str(tmp_path)) == []


def test_collect_memory_broken_file(tmp_path):
    run = tmp_path / "run1"
    run.mkdir()
    (run / "state.json").write_text("{битый json", encoding="utf-8")
    assert collect_memory(str(tmp_path)) == []
