#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Критик-контур 4×4 с плато-стопом и append-only журналом · polymath-gen#2 · Волна ×3 (W3-F1).
Контракт критика: строгий JSON/словарь {ось: {score: 0..4, evidence: str}} — ровно 4 оси из
rubrics-4x4.yaml, без свободного флуда. Остановка: максимум gate.max_iterations ИЛИ плато —
суммарный скор не вырос на ≥ gate.plateau_min_gain за итерацию. Ось «безопасность» ниже
gate.safety_min_score — отклонение при любом суммарном. Доработка точечная: промпт-патч
строится только по слабейшей оси последней оценки. Журнал journal/critique-<штамп>.jsonl —
append-only: файл открывается только в 'a', одна строка = одна итерация, строки не
переписываются — история решений читается diff'ом.
Запуск: python3 wave3/critic_loop.py --selftest | --demo
Подключение: from critic_loop import run_loop; run_loop(задание, критик-колбэк, ...)
"""
import argparse, datetime as dt, json, sys, tempfile
from pathlib import Path
RUBRICS_PATH = Path(__file__).resolve().parent / 'rubrics-4x4.yaml'
def load_rubrics(path=RUBRICS_PATH):
    """Плоский YAML без зависимостей: строки «ключ: значение», комментарии с #."""
    rub = {}
    for raw in Path(path).read_text(encoding='utf-8').splitlines():
        line = raw.split('#', 1)[0].strip()
        if not line or ':' not in line:
            continue
        k, _, v = line.partition(':')
        rub[k.strip()] = v.strip().strip('"')
    return rub
def rubric_axes(rub):
    names = [k.split('.', 2)[1] for k in rub if k.startswith('axis.')]
    return list(dict.fromkeys(names))
def parse_verdict(verdict, axes):
    """Строгий контракт: ровно оси рубрикатора, {score, evidence}, score — целое 0..4."""
    if isinstance(verdict, (str, bytes)):
        try:
            verdict = json.loads(verdict)
        except Exception as e:
            raise ValueError('критик вернул не-JSON: %s' % e)
    if not isinstance(verdict, dict) or set(verdict) != set(axes):
        got = sorted(verdict) if isinstance(verdict, dict) else type(verdict).__name__
        raise ValueError('строгий контракт: нужны ровно оси %s, получено %s' % (sorted(axes), got))
    out = {}
    for a in axes:
        v = verdict[a]
        if not (isinstance(v, dict) and set(v) == {'score', 'evidence'}):
            raise ValueError('ось %r: нужен объект {score, evidence}' % a)
        s = v['score']
        if not isinstance(s, int) or isinstance(s, bool) or not 0 <= s <= 4:
            raise ValueError('ось %r: score — целое 0..4, получено %r' % (a, s))
        if not isinstance(v['evidence'], str) or not v['evidence'].strip():
            raise ValueError('ось %r: пустой evidence (флуд без опоры запрещён)' % a)
        out[a] = {'score': s, 'evidence': v['evidence']}
    return out
def new_journal_path(jdir, prefix):
    jdir = Path(jdir); jdir.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now()
    base = prefix + now.strftime('%Y%m%d-%H%M%S') + '-%03d' % (now.microsecond // 1000)
    p, n = jdir / (base + '.jsonl'), 1
    while p.exists():
        p, n = jdir / ('%s-%d.jsonl' % (base, n)), n + 1
    return p
def patch_prompt(task, axis, score, anchor4):
    return ('Патч-итерация. Задание: %s. Доработать ТОЛЬКО ось «%s» (сейчас %d/4, цель — 4: %s); '
            'остальные оси не менять.' % (task, axis, score, anchor4))
def run_loop(task, critic, rubrics=None, journal_dir=None, journal_path=None):
    """Итерации «критик → плато-стоп/бюджет/безопасность → точечный патч» с jsonl-журналом."""
    rub = rubrics or load_rubrics()
    axes = rubric_axes(rub)
    max_iters, gain = int(rub['gate.max_iterations']), int(rub['gate.plateau_min_gain'])
    saxis, smin = rub['gate.safety_axis'], int(rub['gate.safety_min_score'])
    jp = Path(journal_path) if journal_path else new_journal_path(journal_dir or rub.get('gate.journal_dir', 'journal'), rub.get('gate.journal_prefix', 'critique-'))
    jp.parent.mkdir(parents=True, exist_ok=True)
    prompt, prev_total = task, None
    with open(jp, 'a', encoding='utf-8') as jf:  # только 'a' — append-only, никогда 'w'
        for it in range(1, max_iters + 1):
            verdict = parse_verdict(critic(task, prompt, it), axes)
            total = sum(v['score'] for v in verdict.values())
            rec = {'iteration': it, 'task': task, 'prompt': prompt, 'status': 'scored',
                   'scores': {a: verdict[a]['score'] for a in axes},
                   'evidence': {a: verdict[a]['evidence'] for a in axes},
                   'total': total, 'max_total': 4 * len(axes)}
            if verdict[saxis]['score'] < smin:
                rec.update({'status': 'rejected_safety', 'stop': 'safety'})
                jf.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + '\n'); jf.flush()
                return {'verdict': 'rejected', 'reason': 'safety', 'iterations': it, 'journal': str(jp), 'last': rec}
            jf.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + '\n'); jf.flush()
            if prev_total is not None and total - prev_total < gain:
                return {'verdict': 'stopped', 'reason': 'plateau', 'iterations': it, 'journal': str(jp), 'last': rec}
            prev_total = total
            if it == max_iters:
                return {'verdict': 'stopped', 'reason': 'budget', 'iterations': it, 'journal': str(jp), 'last': rec}
            weak = min(axes, key=lambda a: (verdict[a]['score'], axes.index(a)))
            prompt = patch_prompt(task, weak, verdict[weak]['score'], rub.get('axis.%s.4' % weak, ''))
def selftest():
    rub = load_rubrics()
    axes = rubric_axes(rub)
    assert len(axes) == 4, 'ожидались 4 оси, есть %s' % axes
    saxis = rub['gate.safety_axis']
    with tempfile.TemporaryDirectory() as td:
        jdir = Path(td) / 'journal'
        def plateau_critic(task, prompt, it):
            return {a: {'score': 4 if a == saxis else 3, 'evidence': 'мок: скор не растёт'} for a in axes}
        r = run_loop('мок-плато', plateau_critic, rub, journal_dir=jdir)
        assert r['iterations'] == 2 and r['reason'] == 'plateau', r
        def rise_critic(task, prompt, it):
            return {a: {'score': 4 if a == saxis else min(4, 1 + it), 'evidence': 'мок: рост на 1'} for a in axes}
        r2 = run_loop('мок-рост', rise_critic, rub, journal_dir=jdir)
        assert r2['iterations'] == 3 and r2['reason'] == 'budget', r2
        def unsafe_critic(task, prompt, it):
            v = {a: {'score': 4, 'evidence': 'мок: всё хорошо'} for a in axes}
            v[saxis] = {'score': 3, 'evidence': 'мок: нарушение оси безопасности'}
            return v
        r3 = run_loop('мок-нарушение', unsafe_critic, rub, journal_dir=jdir)
        assert r3['verdict'] == 'rejected' and r3['reason'] == 'safety', r3
        assert sum(r3['last']['scores'].values()) == 15, r3['last']['scores']
        shared = jdir / 'append-check.jsonl'
        ra = run_loop('мок-допис', plateau_critic, rub, journal_path=shared)
        before = shared.read_text(encoding='utf-8')
        rb = run_loop('мок-допис', rise_critic, rub, journal_path=shared)
        after = shared.read_text(encoding='utf-8')
        assert after.startswith(before) and len(after) > len(before), 'append-only нарушен'
        assert ra['iterations'] == 2 and rb['iterations'] == 3, (ra['iterations'], rb['iterations'])
    try:
        parse_verdict('свободный текст вместо JSON', axes)
        raise AssertionError('строгий контракт пропустил флуд')
    except ValueError:
        pass
    try:
        parse_verdict({axes[0]: {'score': 5, 'evidence': 'x'}}, axes)
        raise AssertionError('строгий контракт пропустил score 5')
    except ValueError:
        pass
    print('selftest: OK — плато=2 итерации, рост=3, безопасность отклоняет при 15/16, append-only, флуд отсечён')
    return 0
def demo():
    rub = load_rubrics()
    axes = rubric_axes(rub)
    saxis = rub['gate.safety_axis']
    def critic(task, prompt, it):
        return {a: {'score': 4 if a == saxis else min(4, 2 + it // 2), 'evidence': 'демо-критик, итерация %d' % it} for a in axes}
    with tempfile.TemporaryDirectory() as td:
        r = run_loop('демо-задание: ночной город в неоне', critic, rub, journal_dir=Path(td) / 'journal')
        print('демо: %s за %d итераций (журнал временный)' % (r['verdict'], r['iterations']))
    return 0
def main(argv=None):
    ap = argparse.ArgumentParser(description='Критик-контур 4×4 (polymath-gen#2)')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--selftest', action='store_true', help='самотест на мок-критиках')
    g.add_argument('--demo', action='store_true', help='демо-прогон контура')
    a = ap.parse_args(argv)
    return selftest() if a.selftest else demo()
if __name__ == '__main__':
    sys.exit(main())
