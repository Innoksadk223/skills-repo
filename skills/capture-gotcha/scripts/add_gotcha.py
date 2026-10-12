#!/usr/bin/env python3
"""capture-gotcha 记忆存储：纯标准库 + Markdown。

三份文件（全局 / 项目 / 候选）用同一个硬上限 LIMIT 个 Unicode 码点。
写入入口（add / promote / replace）统一在短时文件锁内做读-改-写，
先验证容量、版本与结构，再用同目录临时文件原子替换；失败一律不写、不截断、不清空。

记什么、写哪个范围由 AI 依据技能规则判断；脚本只保障容量、版本与写入安全，
不核实事实、不做完备脱敏。
"""
from __future__ import annotations
import argparse, fcntl, hashlib, json, os, re, sys, tempfile, time
from contextlib import ExitStack, contextmanager
from datetime import date
from pathlib import Path

LIMIT = 4000  # Unicode 码点硬上限，三份文件相同；不提供抬高上限的开关
GLOBAL_PATH = Path.home() / '.agents' / 'gotchas.md'
CANDIDATES_NAME = 'gotchas-candidates.md'
HEADER = '# Gotchas'
NEW_FIELDS = ('适用', '做法', '验证')  # 现行三字段
LEGACY_FIELDS = ('date', 'scene', 'cause', 'evidence', 'fix')  # 旧五字段，只读兼容
FIELD_LINE = re.compile(r'^- ([^:：]+)[:：]\s*(.*)$')  # 半角与全角冒号都接受
DATE_PREFIX = re.compile(r'^\d{4}-\d{2}-\d{2}')  # 「验证」必须以日期起头
SCOPES = ('global', 'project', 'candidate')
LOCK_NAME = '.capture-gotcha.lock'
LOCK_TRIES, LOCK_WAIT = 20, 0.05
SECRET = re.compile(r'(?i)(password|passwd|token|secret|api[_-]?key|authorization)\s*[=:]\s*[^\s,;]+|https?://[^\s/@]+:[^\s/@]+@|\b(?:sk|ghp|xox[baprs])-?[A-Za-z0-9_-]{12,}')


class StoreError(Exception):
    pass


# ---------- 路径与文本 ----------

def redact(value):
    return SECRET.sub('<redacted>', (value or '').strip())


def project_root(value=None):
    return Path(value or os.getcwd()).resolve()


def paths_for(project=None, global_path=None, project_path=None):
    """--project 只是默认位置的基准（默认 cwd），不探测 Git 根。"""
    gpath = Path(global_path).expanduser() if global_path else Path(GLOBAL_PATH).expanduser()
    ppath = (Path(project_path).expanduser() if project_path
             else project_root(project) / '.agents' / 'gotchas.md')
    return {'global': gpath, 'project': ppath, 'candidate': ppath.parent / CANDIDATES_NAME}


def path_for(scope, project=None, global_path=None, project_path=None):
    return paths_for(project, global_path, project_path)[scope]


def read_bytes(path):
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return b''


def decode(raw, label):
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise StoreError('INVALID_UTF8: {} 不是有效 UTF-8（{}）；未写入。'.format(label, exc))


def count(text):
    """按 Unicode 码点计数；直接解字节，不做 CRLF / 空白规范化。"""
    return len(text)


def version_of(raw):
    return hashlib.sha256(raw).hexdigest()


def entries(text):
    return [x.strip() for x in re.split(r'(?=^### )', text, flags=re.M) if x.startswith('### ')]


def capacity(text, label):
    value = count(text)
    if value > LIMIT:
        raise StoreError('OVER_LIMIT: {}: {} > {} 码点；未写入、未截断。先用 replace 修复该文件。'.format(label, value, LIMIT))
    return value


def field_of(line):
    """解析 `- 键: 值`；半角与全角冒号都算合规写法。"""
    match = FIELD_LINE.match(line.strip())
    if not match:
        return None, None
    return match.group(1).strip(), match.group(2).strip()


def validate_structure(text, label):
    """结构校验：`# Gotchas` 头行 + 每条 `### 标题` 与三字段（适用/做法/验证）。

    只接受现行三字段。旧五字段记录不能被本校验通过，写入入口据此明确拒绝，
    避免把旧格式直接混进新文件；旧文件的查看与迁移走 inspect + replace。
    """
    lines = text.split('\n')
    index, total = 0, len(lines)
    while index < total and not lines[index].strip():
        index += 1
    if index >= total or lines[index].strip() != HEADER:
        raise StoreError('FORMAT: {} 首个非空行必须是 `{}`；未写入。'.format(label, HEADER))
    index += 1
    while index < total:
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if not line.startswith('### ') or not line[4:].strip():
            raise StoreError('FORMAT: {} 第 {} 行应以 `### 标题` 开始；未写入。'.format(label, index + 1))
        title = line[4:].strip()
        index += 1
        for field in NEW_FIELDS:
            if index >= total:
                raise StoreError('FORMAT: {} 记录 `{}` 缺少字段 `- {}:`；未写入。'.format(label, title, field))
            key, value = field_of(lines[index])
            if key in LEGACY_FIELDS:
                raise StoreError('LEGACY_FORMAT: {} 记录 `{}` 仍是旧五字段（`- {}:`）；'
                                 '写入入口只接受新格式（适用/做法/验证）。先用 inspect 查看，'
                                 '再用 replace 按新格式整份迁移；未写入。'.format(label, title, key))
            if key != field:
                raise StoreError('FORMAT: {} 记录 `{}` 缺少或错序字段 `- {}:`；未写入。'.format(label, title, field))
            if not value:
                raise StoreError('FORMAT: {} 记录 `{}` 的 `{}` 值为空；未写入。'.format(label, title, field))
            if field == '验证' and not DATE_PREFIX.match(value):
                raise StoreError('FORMAT: {} 记录 `{}` 的 `验证` 必须以 `YYYY-MM-DD` 日期开头；未写入。'
                                 .format(label, title))
            index += 1
    return True
def audit_structure(text, label):
    """读取侧的宽松结构审计：返回 (问题或 None, 旧五字段条数)。

    读取入口不能因为语法不同就静默忽略内容：现行三字段与完整旧五字段都算可读，
    其余形态报成问题，而不是当作不存在。
    """
    lines = text.split('\n')
    index, total, legacy = 0, len(lines), 0
    while index < total and not lines[index].strip():
        index += 1
    if index >= total:
        return None, 0
    if lines[index].strip() != HEADER:
        return 'FORMAT: {} 首个非空行不是 `{}`；内容无法当作记录读取。'.format(label, HEADER), 0
    index += 1
    while index < total:
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if not line.startswith('### ') or not line[4:].strip():
            return 'FORMAT: {} 第 {} 行不是 `### 标题`；该文件未作为记忆输出。'.format(label, index + 1), legacy
        title = line[4:].strip()
        index += 1
        keys = []
        while index < total and lines[index].lstrip().startswith('- '):
            key, value = field_of(lines[index])
            if key is None:
                return 'FORMAT: {} 记录 `{}` 有无法解析的字段行 `{}`。'.format(label, title, lines[index].strip()), legacy
            if not value:
                return 'FORMAT: {} 记录 `{}` 的 `{}` 值为空。'.format(label, title, key), legacy
            keys.append(key)
            index += 1
        if tuple(keys) == NEW_FIELDS:
            continue
        if tuple(keys) == LEGACY_FIELDS:
            legacy += 1
            continue
        return ('FORMAT: {} 记录 `{}` 的字段为 {}，既不是现行 `{}` 也不是完整旧五字段。'
                .format(label, title, keys or '空', list(NEW_FIELDS))), legacy
    return None, legacy


def parse_entry(entry):
    """把一条记录解析成 (标题, [(键, 值), ...])；无法解析的行终止字段读取。"""
    lines = entry.split('\n')
    title = lines[0][4:].strip() if lines and lines[0].startswith('### ') else ''
    fields = []
    for line in lines[1:]:
        key, value = field_of(line)
        if key is None:
            break
        fields.append((key, value))
    return title, fields


def format_notes(scope, text):
    """可读但值得迁移/修正的提示：旧五字段条数，以及「验证」未以日期起头的条数。"""
    legacy = undated = 0
    for entry in entries(text):
        _, fields = parse_entry(entry)
        keys = [key for key, _ in fields]
        if keys == list(LEGACY_FIELDS):
            legacy += 1
        elif keys == list(NEW_FIELDS) and not DATE_PREFIX.match(dict(fields)['验证']):
            undated += 1
    notes = []
    if legacy:
        notes.append('[{}] LEGACY_FORMAT: 有 {} 条旧五字段记录；已按原样输出，'
                     '建议用 replace 迁到新格式（适用/做法/验证）。'.format(scope, legacy))
    if undated:
        notes.append('[{}] FORMAT: 有 {} 条记录的「验证」未以 YYYY-MM-DD 日期开头；已按原样输出，'
                     '下次维护时一并修正。'.format(scope, undated))
    return notes


# ---------- 锁与写入 ----------

@contextmanager
def locked(directory, exclusive=False, create=False):
    """锁同目录的锁文件；目录不存在且不创建时说明文件也不存在，无需加锁。"""
    if not directory.exists():
        if not create:
            yield
            return
        directory.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(directory / LOCK_NAME), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        for attempt in range(LOCK_TRIES):
            try:
                fcntl.flock(fd, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if attempt == LOCK_TRIES - 1:
                    raise StoreError('BUSY: 记忆目录正被其他写入者维护，稍后重试；不要删锁文件。')
                time.sleep(LOCK_WAIT)
        yield
    finally:
        os.close(fd)


@contextmanager
def locked_dirs(paths, exclusive=False, create=False):
    directories = sorted({path.parent for path in paths}, key=str)
    with ExitStack() as stack:
        for directory in directories:
            stack.enter_context(locked(directory, exclusive=exclusive, create=create))
        yield


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=str(path.parent), prefix='.gotcha-')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, str(path))
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


# ---------- 命令 ----------

def make(a):
    return ('### {}\n- 适用: {}\n- 做法: {}\n- 验证: {}\n'.format(
        redact(a.title), redact(a.when), redact(a.action), redact(a.verified)))


def check_legacy_args(a):
    used = [name for name in LEGACY_FIELDS if getattr(a, name, None)]
    if used:
        raise StoreError('LEGACY_FORMAT: add 只接受新格式（--title/--when/--action/--verified）；'
                         '不再接受旧字段 {}。先用 `inspect` 查看既有记录，'
                         '再用 `replace` 按新格式整份迁移；未写入。'.format('、'.join('--' + x for x in used)))
    missing = [name for name in ('when', 'action') if not getattr(a, name, None)]
    if missing:
        raise StoreError('FORMAT: add 缺少必填参数 {}；未写入。'
                         .format('、'.join('--' + x for x in missing)))


def append_text(text, item):
    base = text.rstrip()
    if not base:
        base = HEADER
    return base + '\n\n' + item


def titles(text):
    return [line[4:].strip() for line in text.split('\n') if line.startswith('### ')]


def duplicate(text, item):
    """去重规则保持简单：新标题与已有标题互为子串即视为同类记录，并回报命中的标题。"""
    title = item.splitlines()[0][4:].strip().lower()
    for existing in titles(text):
        if title in existing.lower() or existing.lower() in title:
            return existing
    return ''


def load(path):
    raw = read_bytes(path)
    return raw, decode(raw, str(path))


def old_over_limit(text, path):
    return count(text) > LIMIT


def add(a):
    check_legacy_args(a)
    if not a.verified:  # 验证必须以日期起头；未给出时用当天日期
        a.verified = date.today().isoformat()
    path = path_for(a.scope, a.project, a.global_path, a.project_path)
    item = make(a)
    with locked(path.parent, exclusive=not a.dry_run, create=not a.dry_run):
        raw, text = load(path)
        if old_over_limit(text, path):
            raise StoreError('OVER_LIMIT: {}: {} > {} 码点；add 不再累积，先用 replace 修复。'.format(path, count(text), LIMIT))
        validate_structure(append_text(HEADER, item), 'add:--{}'.format(a.scope))
        report = {'ok': True, 'command': 'add', 'scope': a.scope, 'path': str(path),
                  'limit': LIMIT, 'dry_run': bool(a.dry_run), 'item': item}
        same = duplicate(text, item)
        if same:
            report.update(skipped=True, matched=same,
                          message='SKIP: 标题与已有记录 `{}` 重叠，未写入；'
                                  '若确是新规则，请改用不同标题。'.format(same))
            return report
        new_text = append_text(text, item)
        validate_structure(new_text, str(path))
        report['characters_before'] = count(text)
        report['characters_after'] = capacity(new_text, str(path))
        if a.dry_run:
            report['message'] = '[dry-run] 校验通过，未写入'
            return report
        atomic(path, new_text.encode('utf-8'))
        report['version'] = version_of(path.read_bytes())
        report['message'] = 'ADDED'
        return report


def promote(a):
    files = [path_for('candidate', a.project, a.global_path, a.project_path),
             path_for(a.scope, a.project, a.global_path, a.project_path)]
    source, target = files
    if source.resolve() == target.resolve():
        raise StoreError('ERROR: 目标与候选指向同一文件 {}；已中止以免破坏数据。'.format(target))
    with locked_dirs(files, exclusive=not a.dry_run, create=not a.dry_run):
        _, source_text = load(source)
        _, target_text = load(target)
        if not source_text.strip():
            raise StoreError('EMPTY: 候选记忆 {} 不存在或为空，没有可转正的记录；未写入。'.format(source))
        if not target_text.strip():
            raise StoreError('EMPTY: 目标记忆 {} 不存在或为空（应为 `# Gotchas` 头行）；未写入。'.format(target))
        for label, path, text in (('candidate', source, source_text), ('target', target, target_text)):
            if old_over_limit(text, path):
                raise StoreError('OVER_LIMIT: {} ({}) : {} > {} 码点；promote 拒绝继续积累，先用 replace 修复。'.format(path, label, count(text), LIMIT))
        validate_structure(source_text, str(source))
        validate_structure(target_text, str(target))
        found = entries(source_text)
        hits = [entry for entry in found if a.keyword.lower() in entry.lower()]
        if len(hits) != 1:
            raise StoreError('ERROR: promote 需要唯一匹配的候选，实际匹配 {} 条；未写入。'.format(len(hits)))
        item = hits[0] + '\n'
        report = {'ok': True, 'command': 'promote', 'keyword': a.keyword, 'scope': a.scope,
                  'source': str(source), 'target': str(target), 'limit': LIMIT,
                  'dry_run': bool(a.dry_run), 'item': item}
        same = duplicate(target_text, item)
        if same:
            report.update(skipped=True, matched=same, message='SKIP: 目标已有同类记录 `{}`；候选保留未删'.format(same))
            return report
        new_target = append_text(target_text, item)
        remaining = [entry for entry in found if entry != hits[0]]
        new_source = (HEADER + '\n\n' + '\n\n'.join(remaining) + '\n') if remaining else HEADER + '\n'
        validate_structure(new_target, str(target))
        validate_structure(new_source, str(source))
        report['target_characters'] = capacity(new_target, str(target))
        report['candidate_characters'] = capacity(new_source, str(source))
        report['candidate_remaining'] = len(remaining)
        if a.dry_run:
            report['message'] = '[dry-run] 校验通过，未写入'
            return report
        atomic(target, new_target.encode('utf-8'))
        try:
            atomic(source, new_source.encode('utf-8'))
        except OSError as exc:
            raise StoreError('PARTIAL: 目标 {} 已写入该记录，但候选 {} 移除失败（{}）；'
                             '两份文件都请先 inspect 确认，再决定是否手动清理候选。'.format(target, source, exc))
        report['message'] = 'PROMOTED'
        return report


def recall(a):
    """只输出正式记忆：项目在先、全局在后；关键词过滤；超限或读不出结构的文件只报问题，不给正文。"""
    keyword = (a.keyword or '').lower()
    targets = [('project', path_for('project', a.project, a.global_path, a.project_path)),
               ('global', path_for('global', a.project, a.global_path, a.project_path))]
    problems, notes, lines = [], [], []
    for scope, path in targets:
        _, text = load(path)
        if old_over_limit(text, path):
            problems.append('[{}] OVER_LIMIT: {} {} > {} 码点；该文件未作为记忆输出（不截断）。'
                            '用 inspect --scope {} 查看，用 replace 修复。'.format(scope, path, count(text), LIMIT, scope))
            continue
        if not text.strip():
            continue  # 空文件是合法状态，不算读失败
        problem, _ = audit_structure(text, str(path))
        if problem:
            problems.append('[{}] {} 该文件未作为记忆输出（不截断）。用 inspect --scope {} 查看。'
                            .format(scope, problem, scope))
            continue
        notes += format_notes(scope, text)  # 旧格式/缺日期仍可读，只提示迁移
        lines += ['[{}] {}'.format(scope, entry) for entry in entries(text) if not keyword or keyword in entry.lower()]
    body = '\n\n'.join(lines) or 'No matching gotchas.'
    output = '\n\n'.join(problems + notes + [body])
    return output, bool(problems)


def inspect(a):
    """只读：路径、是否存在、字符数与上限、是否超限、版本、结构、条数与正文。"""
    blocks = []
    for scope in ([a.scope] if a.scope else list(SCOPES)):
        path = path_for(scope, a.project, a.global_path, a.project_path)
        raw, text = load(path)
        value = count(text)
        problem, legacy = (None, 0)
        if text.strip():
            problem, legacy = audit_structure(text, str(path))
            if problem is None and legacy == 0:
                try:
                    validate_structure(text, str(path))  # 与写入入口同一把尺子对比现状
                except StoreError as exc:
                    problem = str(exc)
        state = 'ok' if problem is None else 'invalid: ' + problem
        if problem is None and legacy:
            state = 'legacy: {} 条旧五字段（可读，建议用 replace 迁到新格式）'.format(legacy)
        blocks.append('\n'.join([
            'scope: {}'.format(scope),
            'path: {}'.format(path),
            'exists: {}'.format('true' if path.exists() else 'false'),
            'characters: {} (limit {}) over_limit: {}'.format(value, LIMIT, 'true' if value > LIMIT else 'false'),
            'version: {}'.format(version_of(raw)),
            'structure: {}'.format(state),
            'entries: {}'.format(len(entries(text))),
            '--- text ---',
        ]) + '\n' + text + ('' if text.endswith('\n') else '\n'))
    return '\n'.join(blocks)


def replace(a):
    path = path_for(a.scope, a.project, a.global_path, a.project_path)
    draft = Path(a.from_file).expanduser()
    try:
        raw = draft.read_bytes()
    except OSError as exc:
        raise StoreError('READ_ERROR: 无法读取修订稿 {}：{}；未写入。'.format(draft, exc))
    text = decode(raw, str(draft))
    new_count = capacity(text, '{} -> {}'.format(draft, path))
    validate_structure(text, str(draft))
    with locked(path.parent, exclusive=not a.dry_run, create=not a.dry_run):
        current_raw, current_text = load(path)
        current_version = version_of(current_raw)
        if a.expect != current_version:
            raise StoreError('STALE_VERSION: {} 当前版本 {}，与 --expect {} 不符；本次未写入。'
                             .format(path, current_version, a.expect))
        report = {'ok': True, 'command': 'replace', 'scope': a.scope, 'path': str(path),
                  'from_file': str(draft), 'limit': LIMIT, 'dry_run': bool(a.dry_run),
                  'characters_before': count(current_text), 'characters_after': new_count,
                  'version_before': current_version, 'entries_after': len(entries(text))}
        if a.dry_run:
            report['message'] = '[dry-run] 容量、结构、版本校验通过，未写入'
            return report
        atomic(path, text.encode('utf-8'))
        report['version_after'] = version_of(path.read_bytes())
        report['message'] = 'REPLACED'
        return report


# ---------- 自检 ----------

def self_test(scratch):
    """只在隔离临时目录里用虚构数据自检；不读写真实记忆。"""
    import subprocess
    checks = []
    scratch = Path(scratch).expanduser()
    scratch.mkdir(parents=True, exist_ok=True)
    real_before = read_bytes(GLOBAL_PATH)
    real_stat = GLOBAL_PATH.stat().st_mtime_ns if GLOBAL_PATH.exists() else None
    script = str(Path(__file__).resolve())
    script_dir = Path(__file__).resolve().parent
    cache_before = {str(p) for p in script_dir.rglob('__pycache__')}
    with tempfile.TemporaryDirectory(prefix='capture-gotcha-test-', dir=str(scratch)) as folder:
        base = Path(folder)
        gp = base / 'global' / 'gotchas.md'
        pp = base / 'project' / '.agents' / 'gotchas.md'
        cp = pp.parent / CANDIDATES_NAME

        def where(scope):
            return {'global': gp, 'project': pp, 'candidate': cp}[scope]

        def snapshot():
            return {str(path): read_bytes(path) for path in (gp, pp, cp)}

        def overlay(*extra):
            return ['--project-path', str(pp), '--global-path', str(gp), *extra]

        def run(*args, code=0):
            result = subprocess.run([sys.executable, '-B', script, *args], capture_output=True, text=True, timeout=60)
            assert result.returncode == code, (args, result.returncode, result.stdout, result.stderr)
            return result

        def rejected(args, marker):
            before = snapshot()
            result = run(*args, code=1)
            assert marker in result.stderr and not result.stdout, (args, result.stdout, result.stderr)
            assert snapshot() == before, ('被拒绝的写入改动了数据', args)
            return result

        def put(path, text):
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = text if isinstance(text, bytes) else text.encode('utf-8')
            path.write_bytes(raw)
            return raw

        def record(title, verified='2026-01-01 虚构验证'):
            return '### {}\n- 适用: s\n- 做法: a\n- 验证: {}\n'.format(title, verified)

        def legacy(title):
            return ('### {}\n- date: 2026-01-01\n- scene: s\n- cause: c\n'
                    '- evidence: e\n- fix: f\n'.format(title))

        def revision(size, title='cap🙂', eol='\n'):
            """构造正好 size 个码点的合法新格式文件；eol 给 CRLF 时换行计入两个码点。"""
            head = (HEADER + eol + eol + '### {}'.format(title) + eol + '- 适用: s' + eol
                    + '- 做法: a' + eol + '- 验证: 2026-01-01 ')
            text = head + '中' * (size - len(head) - len(eol)) + eol
            assert len(text) == size, len(text)
            return text

        fields = ['--when', 's', '--action', 'a', '--verified', '2026-01-01 虚构验证']

        # 缺失文件状态
        for scope in SCOPES:
            out = run('inspect', '--scope', scope, *overlay()).stdout
            assert 'scope: {}'.format(scope) in out and 'exists: false' in out, out
            assert 'characters: 0 (limit {}) over_limit: false'.format(LIMIT) in out
            assert 'version: ' + version_of(b'') in out
        checks.append('inspect 三个作用域可用；缺失文件有明确状态和空内容版本')

        # add / recall / 候选隔离
        add_project = ['add', '--scope', 'project', '--title', '项目约束甲', *fields, *overlay()]
        report = json.loads(run(*add_project).stdout)
        assert report['ok'] and report['message'] == 'ADDED'
        body = pp.read_text(encoding='utf-8')
        assert report['characters_after'] == len(body) <= LIMIT
        assert '- 适用: s' in body and '- 做法: a' in body and '- 验证: 2026-01-01' in body
        run('add', '--scope', 'global', '--title', '全局经验乙', *fields, *overlay())
        run('add', '--scope', 'candidate', '--title', '候选经验丙', *fields, *overlay())
        out = run('recall', *overlay()).stdout
        assert '[project]' in out and '[global]' in out and '[candidate]' not in out
        assert out.index('[project]') < out.index('[global]')
        out = run('recall', '项目约束甲', *overlay()).stdout
        assert '[project]' in out and '[global]' not in out
        checks.append('add 写新三字段；recall 项目在先全局在后、关键词过滤、候选不召回')

        # 全角冒号兼容：正常中文写法不因标点差异丢记录
        wide = base / 'wide.md'
        put(wide, HEADER + '\n\n### 全角冒号记录\n- 适用：s\n- 做法：a\n- 验证：2026-01-02 虚构\n')
        report = json.loads(run('replace', '--scope', 'candidate', '--from-file', str(wide),
                                '--expect', version_of(cp.read_bytes()), *overlay()).stdout)
        assert report['ok'] and cp.read_bytes() == wide.read_bytes()
        out = run('inspect', '--scope', 'candidate', *overlay()).stdout
        assert 'structure: ok' in out and '全角冒号记录' in out, out
        put(cp, HEADER + '\n\n' + record('候选经验丙'))
        checks.append('全角冒号与半角冒号都算合规，inspect/replace 不因标点丢记录')

        again = json.loads(run(*add_project).stdout)
        assert again['ok'] and again['skipped'] and pp.read_text(encoding='utf-8').count('项目约束甲') == 1
        short = json.loads(run('add', '--scope', 'project', '--title', '项目约束', *fields, *overlay()).stdout)
        assert short['skipped'] and short['matched'] == '项目约束甲' and pp.read_text(encoding='utf-8').count('项目约束甲') == 1
        checks.append('重复记录按标题子串规则跳过，并回报命中的已有标题（不静默吞掉新记录）')

        # promote 正常转正 / dry-run
        before = snapshot()
        report = json.loads(run('promote', '候选经验丙', '--scope', 'global', '--dry-run', *overlay()).stdout)
        assert report['dry_run'] and snapshot() == before and report['candidate_remaining'] == 0
        report = json.loads(run('promote', '候选经验丙', '--scope', 'global', *overlay()).stdout)
        assert report['ok'] and report['message'] == 'PROMOTED'
        assert '候选经验丙' in gp.read_text(encoding='utf-8') and '候选经验丙' not in cp.read_text(encoding='utf-8')
        checks.append('promote 转正写入目标并移除候选；dry-run 结果一致且不写盘')

        # 4000 可写 / 4001 拒绝，三作用域
        for scope in SCOPES:
            path = where(scope)
            put(path, HEADER + '\n')
            draft = base / 'cap-{}.md'.format(scope)
            raw = put(draft, revision(LIMIT))
            assert len(raw) > LIMIT  # 字节数已超上限，证明按码点而非字节计数
            report = json.loads(run('replace', '--scope', scope, '--from-file', str(draft),
                                    '--expect', version_of(path.read_bytes()), *overlay()).stdout)
            assert report['ok'] and report['characters_after'] == LIMIT and path.read_bytes() == raw
            over = base / 'cap4001-{}.md'.format(scope)
            put(over, revision(LIMIT + 1))
            rejected(['replace', '--scope', scope, '--from-file', str(over),
                      '--expect', version_of(raw), *overlay()], '4001 > 4000')
        checks.append('三作用域按 Unicode 码点计数：4000 可写，4001 拒绝且原文不变')

        # CRLF 换行计入容量
        put(pp, HEADER + '\n')
        crlf = base / 'crlf.md'
        put(crlf, revision(LIMIT, title='crlf上限', eol='\r\n'))
        assert len(crlf.read_bytes().decode('utf-8')) == LIMIT
        report = json.loads(run('replace', '--scope', 'project', '--from-file', str(crlf),
                                '--expect', version_of(pp.read_bytes()), *overlay()).stdout)
        assert report['characters_after'] == LIMIT and pp.read_bytes() == crlf.read_bytes()
        crlf_over = base / 'crlf4001.md'
        put(crlf_over, revision(LIMIT + 1, title='crlf超限', eol='\r\n'))
        rejected(['replace', '--scope', 'project', '--from-file', str(crlf_over),
                  '--expect', version_of(pp.read_bytes()), *overlay()], '4001 > 4000')
        checks.append('CRLF 按两个码点计入容量：4000 可写，4001 拒绝')

        # stale 版本
        put(pp, HEADER + '\n\n' + record('stale基准'))
        stale = base / 'stale.md'
        put(stale, HEADER + '\n\n' + record('stale新'))
        rejected(['replace', '--scope', 'project', '--from-file', str(stale),
                  '--expect', '0' * 64, *overlay()], 'STALE_VERSION')
        checks.append('版本不符（stale）拒绝写入，正式内容不变')

        # 非法格式：缺字段 / 缺头行 / 验证无日期 / 结构错乱 / 空值
        bad_field = base / 'bad-field.md'
        put(bad_field, HEADER + '\n\n### 缺字段\n- 适用: s\n- 做法: a\n')
        bad_head = base / 'bad-head.md'
        put(bad_head, '### 无头行\n- 适用: s\n- 做法: a\n- 验证: 2026-01-01 虚构\n')
        bad_date = base / 'bad-date.md'
        put(bad_date, HEADER + '\n\n### 验证无日期\n- 适用: s\n- 做法: a\n- 验证: 只写结论\n')
        bad_gap = base / 'bad-gap.md'
        put(bad_gap, HEADER + '\n\n### 字段间插言\n- 适用: s\n随手插一行\n- 做法: a\n- 验证: 2026-01-01 虚构\n')
        for path in (bad_field, bad_head, bad_date, bad_gap):
            rejected(['replace', '--scope', 'project', '--from-file', str(path),
                      '--expect', version_of(pp.read_bytes()), *overlay()], 'FORMAT')
        empty_value = base / 'empty-value.md'
        put(empty_value, HEADER + '\n\n### 空值\n- 适用: s\n- 做法: a\n- 验证:   \n')
        rejected(['replace', '--scope', 'project', '--from-file', str(empty_value),
                  '--expect', version_of(pp.read_bytes()), *overlay()], 'FORMAT')
        checks.append('非法格式（缺字段/缺头行/验证无日期/结构错乱/空值）拒绝，避免 recall 静默忽略')

        # 旧五字段：写入拒绝，读取仍可识别
        put(pp, HEADER + '\n\n' + legacy('旧格式记录甲'))
        reject_legacy = base / 'reject-legacy.md'
        put(reject_legacy, HEADER + '\n\n' + legacy('旧格式写入乙'))
        rejected(['replace', '--scope', 'project', '--from-file', str(reject_legacy),
                  '--expect', version_of(pp.read_bytes()), *overlay()], 'LEGACY_FORMAT')
        rejected(['add', '--scope', 'project', '--title', '旧参数丙', '--scene', 's', '--cause', 'c',
                  '--evidence', 'e', '--fix', 'f', *overlay()], 'LEGACY_FORMAT')
        rejected(['add', '--scope', 'project', '--title', '混用丁', '--when', 's', '--action', 'a',
                  '--verified', '2026-01-01 虚构', '--fix', 'f', *overlay()], 'LEGACY_FORMAT')
        rejected(['add', '--scope', 'project', '--title', '缺参数戊', *overlay()], 'FORMAT')
        result = run('recall', *overlay())
        assert result.returncode == 0 and '旧格式记录甲' in result.stdout and 'LEGACY_FORMAT' in result.stdout
        out = run('inspect', '--scope', 'project', *overlay()).stdout
        assert 'legacy' in out and '旧格式记录甲' in out, out
        checks.append('旧五字段：写入明确拒绝并指导迁移；recall 仍可识别（不静默丢），inspect 标注 legacy')

        # 旧超限文件：inspect / recall / add / promote 保护
        raw_over = put(pp, revision(LIMIT + 1, title='超限遗留'))
        out = run('inspect', '--scope', 'project', *overlay()).stdout
        assert 'over_limit: true' in out and 'characters: {} (limit {})'.format(LIMIT + 1, LIMIT) in out
        assert '超限遗留' in out, out
        result = run('recall', *overlay(), code=1)
        assert 'OVER_LIMIT' in result.stdout and '超限遗留' not in result.stdout, result.stdout
        assert '[global]' in result.stdout, result.stdout
        rejected(['add', '--scope', 'project', '--title', '追加禁止庚', *fields, *overlay()], 'OVER_LIMIT')
        put(cp, HEADER + '\n\n' + record('待转正戊'))
        rejected(['promote', '待转正戊', '--scope', 'project', *overlay()], 'OVER_LIMIT')
        assert '待转正戊' in cp.read_text(encoding='utf-8')
        checks.append('旧超限文件：inspect 可查正文，recall 明确报告且不输出、不截断；add/promote 拒绝继续积累')

        # 候选超限时 promote 拒绝且候选不丢
        raw_candidate = put(cp, revision(LIMIT + 1, title='候选超限己'))
        rejected(['promote', '候选超限己', '--scope', 'project', *overlay()], 'OVER_LIMIT')
        assert cp.read_bytes() == raw_candidate
        put(cp, HEADER + '\n\n' + record('待转正戊'))
        checks.append('候选超限时 promote 拒绝，候选文件保持原样')

        # 同一路径保护
        result = run('promote', '待转正戊', '--scope', 'project', '--project-path', str(cp),
                     '--global-path', str(gp), code=1)
        assert '同一文件' in result.stderr and '待转正戊' in cp.read_text(encoding='utf-8')
        checks.append('目标与候选同一路径时中止，不破坏数据')

        # replace 修复超限文件，并完成旧→新迁移
        fixed = base / 'fixed.md'
        raw_fixed = put(fixed, HEADER + '\n\n' + record('修复后记录'))
        report = json.loads(run('replace', '--scope', 'project', '--from-file', str(fixed),
                                '--expect', version_of(raw_over), *overlay()).stdout)
        assert report['ok'] and report['characters_before'] == LIMIT + 1 and pp.read_bytes() == raw_fixed
        assert '修复后记录' in run('recall', *overlay()).stdout
        report = json.loads(run('promote', '待转正戊', '--scope', 'project', *overlay()).stdout)
        assert report['ok'] and '待转正戊' in pp.read_text(encoding='utf-8')
        assert '待转正戊' not in cp.read_text(encoding='utf-8')
        checks.append('replace 凭版本修复超限文件并迁到新格式，之后 recall 与 promote 恢复正常')

        # 清空记录
        clear = base / 'clear.md'
        raw_clear = put(clear, HEADER + '\n')
        report = json.loads(run('replace', '--scope', 'project', '--from-file', str(clear),
                                '--expect', version_of(pp.read_bytes()), *overlay()).stdout)
        assert report['ok'] and report['entries_after'] == 0 and pp.read_bytes() == raw_clear
        run('recall', *overlay())  # 退出码 0：清空不等于读失败
        checks.append('replace 允许清空记录（保留头行），recall 不算读失败')

        # add 结果与 promote 目标超限保护
        put(pp, revision(LIMIT - 10, title='近满'))
        put(cp, HEADER + '\n\n' + record('容量转正癸'))
        rejected(['add', '--scope', 'project', '--title', '超限追加壬', *fields, *overlay()], 'OVER_LIMIT')
        rejected(['promote', '容量转正癸', '--scope', 'project', *overlay()], 'OVER_LIMIT')
        assert '容量转正癸' in cp.read_text(encoding='utf-8')
        checks.append('add 结果与 promote 目标超限时报 OVER_LIMIT，未写入且候选保留')

        put(pp, HEADER + '\n\n' + record('dry基准'))
        # dry-run 不写盘
        before = snapshot()
        report = json.loads(run('add', '--scope', 'project', '--title', 'dry运行丁', *fields,
                                '--dry-run', *overlay()).stdout)
        assert report['dry_run'] and snapshot() == before
        draft = base / 'dry.md'
        put(draft, HEADER + '\n\n' + record('dry替换'))
        report = json.loads(run('replace', '--scope', 'project', '--from-file', str(draft),
                                '--expect', version_of(pp.read_bytes()), '--dry-run', *overlay()).stdout)
        assert report['dry_run'] and report['characters_after'] == len(draft.read_text(encoding='utf-8'))
        assert snapshot() == before
        checks.append('add/replace 的 dry-run 只展示容量与版本结论，不写盘')

        # 并发锁
        namespace = argparse.Namespace(scope='project', title='锁测试辛', when='s', action='a',
                                       verified='2026-01-01 虚构', date=None, scene=None, cause=None,
                                       evidence=None, fix=None, project=str(base),
                                       global_path=str(gp), project_path=str(pp), dry_run=False)
        with locked(pp.parent, exclusive=True):
            held = pp.read_bytes()
            try:
                add(namespace)
                raise AssertionError('锁未生效')
            except StoreError as exc:
                assert 'BUSY' in str(exc), exc
            assert pp.read_bytes() == held
        assert add(namespace)['message'] == 'ADDED'
        checks.append('写入口在短时锁内完成读-改-写；并发写入者收到 BUSY 且内容不变')

        assert not list(base.rglob('.gotcha-*')), '临时文件残留'
        checks.append('写入使用同目录临时文件原子替换，无临时文件残留')

        assert {str(p) for p in script_dir.rglob('__pycache__')} == cache_before, '自检产生了 __pycache__'
        checks.append('子进程以 -B 运行，自检不在脚本目录留下 __pycache__')

    assert read_bytes(GLOBAL_PATH) == real_before, '自检触碰了真实全局记忆'
    assert (GLOBAL_PATH.stat().st_mtime_ns if GLOBAL_PATH.exists() else None) == real_stat
    return {'ok': True, 'checks': checks, 'count': len(checks), 'limit': LIMIT,
            'temporary_data_removed': not base.exists(), 'real_memory_used': False}

# ---------- CLI ----------

def build_parser():
    parser = argparse.ArgumentParser(description='capture-gotcha 记忆读写（纯标准库，Markdown）')
    commands = parser.add_subparsers(dest='cmd', required=True)

    def with_paths(sub):
        sub.add_argument('--project', help='默认位置的基准目录，默认 cwd（不探测 Git 根）')
        sub.add_argument('--project-path', help='项目记忆文件覆盖路径')
        sub.add_argument('--global-path', help='全局记忆文件覆盖路径')
        return sub

    writer = with_paths(commands.add_parser('add', help='追加一条记录（新格式：适用/做法/验证）'))
    writer.add_argument('--scope', choices=list(SCOPES), required=True)
    writer.add_argument('--title', required=True, help='可迁移的行动规则名，不是某次事故名')
    writer.add_argument('--when', metavar='适用', help='触发条件与适用边界（必填）')
    writer.add_argument('--action', metavar='做法', help='可执行动作；根因只在影响动作时补一句（必填）')
    writer.add_argument('--verified', metavar='验证', help='YYYY-MM-DD + 最短验证依据；省略则用今天日期')
    for name in LEGACY_FIELDS:  # 旧五字段参数：显式拒绝并指导迁移，不做多套兼容接口
        writer.add_argument('--{}'.format(name), help=argparse.SUPPRESS)
    writer.add_argument('--dry-run', action='store_true')

    reader = with_paths(commands.add_parser('recall', help='输出项目与全局正式记忆，候选不参与'))
    reader.add_argument('keyword', nargs='?', default='')

    promoter = with_paths(commands.add_parser('promote', help='把唯一匹配的候选转正'))
    promoter.add_argument('keyword')
    promoter.add_argument('--scope', choices=['global', 'project'], required=True)
    promoter.add_argument('--dry-run', action='store_true')

    viewer = with_paths(commands.add_parser('inspect', help='只读查看路径、容量、版本与正文'))
    viewer.add_argument('--scope', choices=list(SCOPES), help='默认三份都显示')

    editor = with_paths(commands.add_parser('replace', help='按版本整份提交修订稿（修改/合并/清空）'))
    editor.add_argument('--scope', choices=list(SCOPES), required=True)
    editor.add_argument('--from-file', dest='from_file', required=True, help='UTF-8 修订稿')
    editor.add_argument('--expect', required=True, help='inspect 返回的 version')
    editor.add_argument('--dry-run', action='store_true')

    tester = commands.add_parser('self-test', help='仅在会话临时目录用虚构数据自检')
    tester.add_argument('--scratch', default=tempfile.gettempdir(), help='临时隔离目录，默认系统临时目录')
    return parser


def main():
    args = build_parser().parse_args()
    try:
        if args.cmd == 'inspect':
            print(inspect(args))
            return 0
        if args.cmd == 'recall':
            text, degraded = recall(args)
            print(text)
            return 1 if degraded else 0
        if args.cmd == 'self-test':
            result = self_test(args.scratch)
            print(json.dumps(result, ensure_ascii=False))
            return 0
        report = {'add': add, 'promote': promote, 'replace': replace}[args.cmd](args)
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except (StoreError, OSError, UnicodeError) as exc:
        print('ERROR: {}'.format(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
