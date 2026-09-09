#!/usr/bin/env python3
from __future__ import annotations
import argparse, os, re, tempfile
from datetime import date
from pathlib import Path

GLOBAL = Path.home() / '.agents' / 'gotchas.md'
CANDIDATES = 'gotchas-candidates.md'
SECRET = re.compile(r'(?i)(password|passwd|token|secret|api[_-]?key|authorization)\s*[=:]\s*[^\s,;]+|https?://[^\s/@]+:[^\s/@]+@|\b(?:sk|ghp|xox[baprs])-?[A-Za-z0-9_-]{12,}')

def redact(value): return SECRET.sub('<redacted>', (value or '').strip())
def project_root(value=None): return Path(value or os.getcwd()).resolve()
def path_for(scope, project=None, global_path=None, project_path=None):
    if scope == 'global': return Path(global_path or GLOBAL).expanduser()
    if scope == 'project': return Path(project_path or (project_root(project) / '.agents' / 'gotchas.md')).expanduser()
    return project_root(project) / '.agents' / CANDIDATES
def read(path): return path.read_text(encoding='utf-8') if path.exists() else '# Gotchas\n'
def atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.gotcha-', text=True)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f: f.write(text); f.flush(); os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp): os.unlink(temp)
def entries(text): return [x.strip() for x in re.split(r'(?=^### )', text, flags=re.M) if x.startswith('### ')]
def make(a):
    return f'### {redact(a.title)}\n- date: {a.date or date.today()}\n- scene: {redact(a.scene)}\n- cause: {redact(a.cause)}\n- evidence: {redact(a.evidence)}\n- fix: {redact(a.fix)}\n'
def append(path, item, dry=False):
    text = read(path)
    if any(redact(item.splitlines()[0][4:]).lower() in e.lower() for e in entries(text)): return 'SKIP: similar gotcha already exists'
    if dry: return '[dry-run]\n' + item
    atomic(path, text.rstrip() + '\n\n' + item + '\n'); return f'ADDED: {path}'
def add(a):
    path = path_for(a.scope, a.project, a.global_path, a.project_path)
    return append(path, make(a), a.dry_run)
def recall(a):
    project = path_for('project', a.project, project_path=a.project_path)
    keyword = a.keyword.lower()
    paths = [('project', project), ('global', Path(a.global_path or GLOBAL).expanduser())]
    out = []
    for scope, path in paths:
        out += [f'[{scope}] {e}' for e in entries(read(path)) if not keyword or keyword in e.lower()]
    return '\n\n'.join(out) or 'No matching gotchas.'
def promote(a):
    src = path_for('candidate', a.project)
    es = entries(read(src)); hits = [e for e in es if a.keyword.lower() in e.lower()]
    if len(hits) != 1: return 'ERROR: promote requires exactly one matching candidate'
    target = path_for(a.scope, a.project, a.global_path, a.project_path)
    result = append(target, hits[0], a.dry_run)
    if result.startswith('SKIP') or a.dry_run: return result
    atomic(src, '\n\n'.join(e for e in es if e != hits[0]) + ('\n' if len(es) > 1 else ''))
    return f'PROMOTED [{a.scope}]: {target}'
def self_test():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        root = Path(d); gp = root/'global.md'; pp = root/'.agents'/'gotchas.md'; cp = root/'.agents'/'gotchas-candidates.md'
        ns = argparse.Namespace(scope='project', title='isolated', scene='scene', cause='cause', evidence='token=SECRET123456789', fix='fix', date=None, project=str(root), global_path=str(gp), project_path=str(pp), dry_run=False)
        assert add(ns).startswith('ADDED') and '<redacted>' in pp.read_text()
        ns.scope='candidate'; ns.project_path=None; assert add(ns).startswith('ADDED')
        pr = argparse.Namespace(keyword='isolated', project=str(root), project_path=str(pp), global_path=str(gp)); assert '[project]' in recall(pr) and '[candidate]' not in recall(pr)
        pm = argparse.Namespace(keyword='isolated', scope='global', project=str(root), global_path=str(gp), project_path=None, dry_run=False); assert promote(pm).startswith('PROMOTED') and 'isolated' in gp.read_text() and 'isolated' not in cp.read_text()
    return 'SELF_TEST: ok'
def main():
    p=argparse.ArgumentParser(); s=p.add_subparsers(dest='cmd', required=True)
    a=s.add_parser('add'); a.add_argument('--scope', choices=['global','project','candidate'], required=True); a.add_argument('--title',required=True); a.add_argument('--scene',required=True); a.add_argument('--cause',required=True); a.add_argument('--fix',required=True); a.add_argument('--evidence',required=True); a.add_argument('--date'); a.add_argument('--project'); a.add_argument('--project-path'); a.add_argument('--global-path'); a.add_argument('--dry-run',action='store_true')
    r=s.add_parser('recall'); r.add_argument('keyword',nargs='?',default=''); r.add_argument('--project'); r.add_argument('--project-path'); r.add_argument('--global-path')
    q=s.add_parser('promote'); q.add_argument('keyword'); q.add_argument('--scope',choices=['global','project'],required=True); q.add_argument('--project'); q.add_argument('--project-path'); q.add_argument('--global-path'); q.add_argument('--dry-run',action='store_true')
    s.add_parser('self-test'); x=p.parse_args(); print(add(x) if x.cmd=='add' else recall(x) if x.cmd=='recall' else promote(x) if x.cmd=='promote' else self_test())
if __name__=='__main__': main()
