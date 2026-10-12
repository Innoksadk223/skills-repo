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
# Markdown 水平线＝记录边界。必须整行匹配——`\s*$` 不能省：`- **加粗** 说明`、
# `--- 同行尾注` 这类同行还有内容的行本身是内容，宽松匹配会把它们当边界而静默丢弃
# （原始行不再出现在任何输出里）。`- 字段: 值` 只有一个 `-`，匹配不上这套「3 个及以上」。
RULE_LINE = re.compile(r'^\s*[-*_](?:\s*[-*_]){2,}\s*$')
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
    """--project 只是默认位置的基准（默认 cwd），不探测 Git 根。

    --project-path 语义是文件路径；若传进来的其实是已存在的目录，
    按「该目录下的 gotchas.md」处理，避免候选被写到目录的上一级。
    """
    gpath = Path(global_path).expanduser() if global_path else Path(GLOBAL_PATH).expanduser()
    if project_path:
        ppath = Path(project_path).expanduser()
        if ppath.is_dir():
            ppath = ppath / 'gotchas.md'
    else:
        ppath = project_root(project) / '.agents' / 'gotchas.md'
    return {'global': gpath, 'project': ppath, 'candidate': ppath.parent / CANDIDATES_NAME}


def path_for(scope, project=None, global_path=None, project_path=None):
    return paths_for(project, global_path, project_path)[scope]


def read_bytes(path):
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return b''
    except OSError as exc:
        # 权限不足、路径是目录等：当成「这一份读不出」逐份降级，
        # 而不是冒泡到 main 让整个 recall/inspect 失败。
        raise StoreError('READ_ERROR: {} 无法读取（{}）；本次按该文件读不出处理。'
                         .format(path, exc))


def decode(raw, label):
    """解码并丢弃开头的 UTF-8 BOM；写盘时按文本原样写出，不再带 BOM。"""
    try:
        return raw.decode('utf-8').lstrip('\ufeff')
    except UnicodeDecodeError as exc:
        raise StoreError('INVALID_UTF8: {} 不是有效 UTF-8（{}）；'
                         '先手工把它转成 UTF-8，再用 replace 整份提交。'.format(label, exc))


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


def header_ok(text):
    """文件级检查：首个非空行必须是 `# Gotchas`；空文件合法。

    这是唯一不做逐条打捞的判断——没有头行的文件无法可靠区分「记录」与「散落文本」。
    """
    for line in text.split('\n'):
        if line.strip():
            return line.strip() == HEADER
    return True


def diagnose(entry):
    """判定单条记录是否可读：返回 (原因或 None, 是否旧五字段)。

    标题行必须严格是 `### 标题`。缩进、缺空格、多一个 `#` 都算坏记录——但要给出原始行，
    让人一眼知道是哪一行、怎么修：报出的是保留行首缩进的原文，行首有缩进或 `###`
    后缺标题文字时再点明具体症状；不能像去掉缩进那样报出一行看着完全合法的文字，
    否则与「不是 `### 标题`」自相矛盾。
    """
    raw_line = entry.split('\n', 1)[0].rstrip('\r')  # 只去掉行尾 CR，行首缩进必须留着
    title, fields = parse_entry(entry)
    if not title:
        reason = '标题行 `{}` 不是 `### 标题`'.format(raw_line[:40])
        # 两个症状独立判断，不互相顶替：前导空白按「有缩进」算（U+3000/U+00A0 等
        # 不常见的空白也在内），标题文字缺失单独再报一条。
        if raw_line != raw_line.lstrip():
            reason += '（行首有缩进，`###` 必须顶格）'
        if raw_line.strip() == '###':
            reason += '（`###` 后缺少空格与标题文字）'
        return reason, False
    body = [line for line in entry.split('\n')[1:] if line.strip()]
    if len(fields) != len(body):
        stray = body[len(fields)].strip()
        return '有无法解析的行 `{}`'.format(stray[:40]), False
    keys = [key for key, _ in fields]
    if keys == list(LEGACY_FIELDS):
        return None, True
    if keys != list(NEW_FIELDS):
        return ('字段为 {}，既不是现行 {} 也不是完整旧五字段'.format(keys or '空', list(NEW_FIELDS))), False
    for key, value in fields:
        if not value:
            return '字段 `{}` 值为空'.format(key), False
    return None, False


def salvage(text):
    """逐条打捞：返回 (可读记录, [(标题, 原因), ...], 旧五字段条数, 散落内容行)。

    读取侧不因一条记录坏掉就放弃整份文件：能读的照常输出，坏掉的逐条报出，
    既保住「不静默丢弃」，也不必把可用的记录一起陪葬。写入侧仍走 validate_structure
    的整份严格校验，坏文件上不允许继续积累。

    切块按「去掉行首空白后以 `###` 开头」而不是 `entries()` 的「`### ` 开头」：标题行少了
    空格、或整行被缩进时，它不是一条合法记录，但仍是文件里的内容，必须报出来而不是当成
    没写过，也不能让它粘到上一条记录上把人家的合法记录一起判坏。不属于任何记录的散落行同理。

    Markdown 水平线（一行只由 3 个及以上的 `-`/`*`/`_` 和空白组成）是记录边界：它之后、
    下一个标题之前的内容不属于任何记录，按散落内容报出，不能并进上一条记录把好记录一起判坏。
    字段值不会误撞水平线——`- 适用: 甲` 是单个 `-` 加字段名，匹配不上 RULE_LINE。
    """
    lines = text.split('\n')
    index, total = 0, len(lines)
    while index < total and not lines[index].strip():
        index += 1
    if index < total and lines[index].strip() == HEADER:
        index += 1
    chunks, current, stray = [], None, []
    for line in lines[index:]:
        if line.lstrip().startswith('###'):
            if current is not None:
                chunks.append(current)
            current = [line]
        elif RULE_LINE.match(line):
            # 水平线是记录边界：它本身不是内容，不报成散落；它之后到下一个标题之前的内容
            # 才是散落内容，不能并进上一条记录把好记录一起判坏。
            if current is not None:
                chunks.append(current)
                current = None
        elif current is not None:
            current.append(line)
        elif line.strip():
            stray.append(line.strip())
    if current is not None:
        chunks.append(current)
    usable, skipped, legacy = [], [], 0
    for chunk in chunks:
        entry = '\n'.join(chunk).rstrip()
        if not entry:
            continue
        reason, is_legacy = diagnose(entry)
        title, _ = parse_entry(entry)
        if reason:
            skipped.append((title or '(无标题)', reason))
            continue
        legacy += 1 if is_legacy else 0
        usable.append(entry)
    return usable, skipped, legacy, stray


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


def searchable(entry):
    """检索文本：标题 + 三字段的值，不含字段名。

    字段名（适用/做法/验证）每条都有，若纳入匹配，任何以它们为关键词的查询都会
    命中全部记录，排序随之失效。
    """
    title, fields = parse_entry(entry)
    return title + '\n' + '\n'.join(value for _, value in fields)


def format_notes(scope, usable, legacy):
    """可读但值得迁移/修正的提示：旧五字段条数，以及「验证」未以日期起头的条数。"""
    undated = 0
    for entry in usable:
        _, fields = parse_entry(entry)
        mapping = dict(fields)
        if list(mapping.keys()) == list(NEW_FIELDS) and not DATE_PREFIX.match(mapping['验证']):
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

def single_line(value, name):
    """字段值必须是单行：换行会被拼成额外记录或非字段行，等于注入。"""
    text = redact(value)
    if '\n' in text or '\r' in text:
        raise StoreError('FORMAT: {} 不能含换行；一条记录的三字段各占一行，'
                         '多行内容请压成一句、或改写成并列短语。未写入。'.format(name))
    return text


def make(a):
    return ('### {}\n- 适用: {}\n- 做法: {}\n- 验证: {}\n'.format(
        single_line(a.title, '--title'), single_line(a.when, '--when'),
        single_line(a.action, '--action'), single_line(a.verified, '--verified')))


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
                  'source_version': version_of(source.read_bytes()),
                  'target_version': version_of(target.read_bytes()),
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
            raise StoreError('PARTIAL: 目标 {} 已写入该记录（新版本 {}），但候选 {} 移除失败（{}）；'
                             '先 inspect 两份文件确认实际状态，再决定是否手动清理候选。'
                             .format(target, version_of(target.read_bytes()), source, exc))
        report['message'] = 'PROMOTED'
        report['source_version'] = version_of(source.read_bytes())
        report['target_version'] = version_of(target.read_bytes())
        return report


def recall(a):
    """只输出正式记忆：项目在先、全局在后；逐条打捞；多关键词按命中数排序。"""
    keywords = [word.lower() for word in (a.keywords or []) if word.strip()]
    targets = [('project', path_for('project', a.project, a.global_path, a.project_path)),
               ('global', path_for('global', a.project, a.global_path, a.project_path))]
    problems, notes, index, hits_by_scope = [], [], [], {}
    for scope, path in targets:
        try:
            _, text = load(path)
        except StoreError as exc:  # 单份文件读不出时只报该份，健康的那份照常输出
            problems.append('[{}] {} 该文件未作为记忆输出。用 inspect --scope {} 查看。'
                            .format(scope, exc, scope))
            continue
        if not text.strip():
            continue  # 空文件是合法状态，不算读失败
        if not header_ok(text):
            problems.append('[{}] FORMAT: {} 首个非空行不是 `{}`；该文件未作为记忆输出。'
                            '用 inspect --scope {} 查看。'.format(scope, path, HEADER, scope))
            continue
        if old_over_limit(text, path):  # 容量守卫：超限文件整份先不输出，逼一次 replace
            problems.append('[{}] OVER_LIMIT: {} {} > {} 码点；该文件未作为记忆输出（不截断）。'
                            '用 inspect --scope {} 查看，用 replace 修复。'
                            .format(scope, path, count(text), LIMIT, scope))
            continue
        usable, skipped, legacy, stray = salvage(text)
        for title, reason in skipped:  # 坏的逐条报出，其余照常输出：不静默丢弃，也不整份陪葬
            problems.append('[{}] FORMAT: 记录 `{}` {}；已跳过该条，同文件其余记录照常输出。'
                            '用 inspect --scope {} 查看，用 replace 修复。'.format(scope, title, reason, scope))
        for line in stray:  # 不属于任何记录的散落内容：同样报出，不当成没写过
            problems.append('[{}] FORMAT: 散落内容 `{}` 不属于任何 `### 记录`；未作为记忆输出。'
                            '用 inspect --scope {} 查看，用 replace 修复。'.format(scope, line[:60], scope))
        notes += format_notes(scope, usable, legacy)  # 旧格式/缺日期仍可读，只提示迁移
        index += ['[{}] {}'.format(scope, searchable(entry).split('\n', 1)[0]) for entry in usable]
        hits_by_scope[scope] = []
        for order, entry in enumerate(usable):
            hits = sum(1 for word in keywords if word in searchable(entry).lower())
            if keywords and not hits:
                continue
            hits_by_scope[scope].append((hits, order, entry))
    lines = []
    for scope, _ in targets:  # 顺序保持「项目在先、全局在后」；同范围内按命中数降序，再按原文顺序
        for _, _, entry in sorted(hits_by_scope.get(scope, []), key=lambda row: (-row[0], row[1])):
            lines.append('[{}] {}'.format(scope, entry))
    if lines:
        body = '\n\n'.join(lines)
    elif keywords:
        titled = [line for line in index if line.partition('] ')[2].strip()]
        body = ('No matching gotchas.\n\n没有记录命中 {}。以下是全部可用记录的标题，'
                '换个更贴近的写法再查一次；标题越具体越容易命中：\n\n{}'
                .format('、'.join(keywords), '\n'.join(titled) or '（无可用记录）'))
    else:
        body = 'No matching gotchas.'
    return '\n\n'.join(problems + notes + [body]), bool(problems)


def inspect(a):
    """只读：路径、是否存在、字符数与上限、是否超限、版本、结构、条数与正文。"""
    blocks = []
    for scope in ([a.scope] if a.scope else list(SCOPES)):
        path = path_for(scope, a.project, a.global_path, a.project_path)
        text, read_problem, legacy, write_problem = '', None, 0, None
        usable, skipped, stray = [], [], []
        decoded = True
        read_error = None  # 只有 READ_ERROR 才是「读不出」；解码失败走 decoded=False，两者文案不同
        try:
            raw = read_bytes(path)
            text = decode(raw, str(path))
        except StoreError as exc:  # 单份读不出也要给出该份状态，另两份照常显示
            raw, read_problem, decoded = b'', str(exc), False
            if str(exc).startswith('READ_ERROR'):
                read_error = str(exc)
        if decoded and read_problem is None and text.strip():
            if not header_ok(text):
                read_problem = 'FORMAT: 首个非空行不是 `{}`（无头行时无法逐条打捞）。'.format(HEADER)
            else:
                usable, skipped, legacy, stray = salvage(text)
                if not usable and (skipped or stray):
                    read_problem = ('FORMAT: 没有一条可读记录（{} 条读不出、{} 处散落内容）；'
                                    '该文件未作为记忆输出（原文仍按字节原样列在下方，便于 replace 修复）。'
                                    .format(len(skipped), len(stray)))
                else:
                    try:
                        validate_structure(text, str(path))  # 与写入入口同一把尺子对比现状
                    except StoreError as exc:
                        write_problem = str(exc)
        if read_problem:
            state = 'invalid: ' + read_problem
        elif skipped or stray:
            extra = '；另有 {} 条旧五字段（需用 replace 迁移）'.format(legacy) if legacy else ''
            state = ('partial: {} 条可读、{} 条读不出、{} 处散落内容'
                     '（recall 会输出可读的，并逐条报出其余）{}'
                     .format(len(usable), len(skipped), len(stray), extra))
        elif legacy:
            state = 'legacy: {} 条旧五字段（可读，建议用 replace 迁到新格式）'.format(legacy)
        elif write_problem:
            # 只读命令不执行写入，去掉校验信息里面向写入入口的「未写入」后缀
            state = ('readable: {}（recall 仍会原样输出；写入前需先用 replace 修正）'
                     .format(write_problem.replace('；未写入。', '。')))
        else:
            state = 'ok'
        if decoded:
            # 能解码就给真实容量、条数与正文——即使结构有问题（无头行/全坏）也不例外：
            # inspect 是唯一能看正文的维护入口，藏掉正文等于断了 replace 的修复路径。
            size = 'characters: {} (limit {}) over_limit: {}'.format(
                count(text), LIMIT, 'true' if count(text) > LIMIT else 'false')
            # entries 与 structure 是两条口径：structure 说 recall 会输出几条，entries 说
            # 文件里数得出几条可读记录。同一屏里两个数字不能互相打架，也不能让宽松口径
            # 盖过 strict 口径（recall 一条都没输出，却写着 entries: 1）。所以 entries 一律
            # 报「可读条数」；文件不可用时再把读不出与散落的数字、以及原文里的 `###` 标题行
            # 数一并标明——免得 `entries: 0` 让人误以为文件是空的，用 replace 覆盖掉真实内容。
            # 缺头行时 skipped/stray 都是空，光看 `entries: 0` 最容易被误当成空文件，所以
            # read_problem 已置的文件同样要带上标题行数提示。
            headings = sum(1 for line in text.split('\n') if line.lstrip().startswith('###'))
            if usable:
                entries_line = 'entries: {}'.format(len(usable))
            elif skipped or stray:
                entries_line = ('entries: 0 条可读、{} 条读不出、{} 处散落内容'
                                '（都不作为记忆输出，原文见下方；文件里共 {} 个 `###` 标题行）'
                                .format(len(skipped), len(stray), headings))
            elif read_problem:
                # 缺头行等：skipped/stray 都是空，只报 `entries: 0` 最像空文件，把标题行数说清楚
                entries_line = ('entries: 0 条可读（本文件未逐条打捞，原文见下方；'
                                '文件里共 {} 个 `###` 标题行，别当成空文件整份覆盖）'.format(headings))
            else:
                entries_line = 'entries: 0'
            body = text + ('' if text.endswith('\n') else '\n')
            if skipped:
                body += ''.join('\n（记录 `{}` 读不出：{}）\n'.format(title, reason)
                                for title, reason in skipped)
            if stray:
                body += ''.join('\n（散落内容，不属于任何记录：{}）\n'.format(line[:60]) for line in stray)
        elif read_error:
            # 读不出和编码错误是两回事：不能把「目录/权限」说成「0 字节、解码失败」。
            size = 'characters: 未知（文件读不出：路径类型、权限等原因，字节数与正文都拿不到）'
            entries_line = 'entries: 未知（文件读不出，条数无法统计）'
            body = '（读不出正文：{}）\n'.format(read_error)
        else:
            size = 'characters: 未知（{} 字节，无法按 UTF-8 解码）'.format(len(raw))
            entries_line = 'entries: 0（无法按 UTF-8 解码，条数未知）'
            body = '（读不出正文；若是编码问题先手工转成 UTF-8，再用 replace 整份提交）\n'
        blocks.append('\n'.join([
            'scope: {}'.format(scope),
            'path: {}'.format(path),
            'exists: {}'.format('true' if path.exists() else 'false'),
            size,
            'version: {}'.format(version_of(raw)),
            'structure: {}'.format(state),
            entries_line,
            '--- text ---',
        ]) + '\n' + body)
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
            """code=0/1 时照旧严格校验退出码；code=None 只取输出，退出码由调用方自己断言。

            需要 code=None 的场合：用例的首要证伪目标是「某段原文必须出现在输出里」，
            若先卡退出码，失败信息会只报「退出码不对」，把真正的静默丢弃盖在后面。
            """
            result = subprocess.run([sys.executable, '-B', script, *args], capture_output=True, text=True, timeout=60)
            if code is not None:
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
        assert list(base.rglob(LOCK_NAME)), '锁文件应当持续存在（flock 语义）'
        checks.append('写入用同目录临时文件原子替换，无 .gotcha-* 残留；锁文件按 flock 语义保留')

        # 输入值不得含换行：换行可注入额外记录并绕过查重
        put(pp, HEADER + '\n\n' + record('换行基准'))
        rejected(['add', '--scope', 'project', '--title', '注入甲\n### 伪造记录',
                  *fields, *overlay()], '不能含换行')
        assert pp.read_text(encoding='utf-8').count('### ') == 1, '换行注入改动了文件'
        rejected(['add', '--scope', 'project', '--title', '注入乙', '--when', 's',
                  '--action', 'a\n- 适用: p', '--verified', '2026-01-01 x', *overlay()], '不能含换行')
        checks.append('四个字段都拒绝换行，一次 add 无法注入第二条记录')

        # 读错误逐份降级：某一份权限不足时，不拖垮其余作用域
        blocked = base / 'blocked'
        blocked.mkdir(exist_ok=True)
        bpath = blocked / 'gotchas.md'
        put(bpath, HEADER + '\n\n' + record('读不到丙'))
        bpath.chmod(0o000)
        try:
            out = run('inspect', '--project-path', str(bpath), '--global-path', str(gp)).stdout
            assert 'READ_ERROR' in out and out.count('scope: ') == 3, out
            result = run('recall', '--project-path', str(bpath), '--global-path', str(gp), code=1)
            assert 'READ_ERROR' in result.stdout, result.stdout
        finally:
            bpath.chmod(0o600)
        checks.append('某份文件读错误（权限等）时逐份降级：inspect 三份照列、recall 其余文件照常输出')
        # BOM 容忍：头行前有 U+FEFF 时仍能识别，不整份失联
        raw_bom = put(pp, '\ufeff' + HEADER + '\n\n' + record('带BOM记录'))
        out = run('inspect', '--scope', 'project', *overlay()).stdout
        assert 'structure: ok' in out and '带BOM记录' in out, out
        result = run('recall', *overlay())
        assert result.returncode == 0 and '带BOM记录' in result.stdout, result.stdout
        # 写回时不再带 BOM（decode 已剥离），且版本以原始字节计
        report = json.loads(run('add', '--scope', 'project', '--title', 'BOM后追加',
                                *fields, *overlay()).stdout)
        assert report['message'] == 'ADDED' and not pp.read_bytes().startswith(b'\xef\xbb\xbf')
        assert report['characters_before'] == len(raw_bom.decode('utf-8').lstrip('\ufeff'))
        checks.append('BOM 文件仍可 inspect/recall/add；写回时剥掉 BOM 且不重复计入容量')

        # 非 UTF-8：单份读不出不拖垮其余作用域
        put(pp, record('不可读基准').encode('utf-16'))
        put(Path(str(gp)), HEADER + '\n\n' + record('健康的全局'))
        result = run('recall', *overlay(), code=1)
        assert 'INVALID_UTF8' in result.stdout and '健康的全局' in result.stdout, result.stdout
        out = run('inspect', *overlay()).stdout
        assert out.count('scope: ') == 3 and '健康的全局' in out and 'INVALID_UTF8' in out, out
        checks.append('单份文件非 UTF-8 时 recall 仍输出健康的一份、inspect 仍列出三个作用域')

        # 可读但写入前需修：与 recall 结论一致，不再误报 invalid
        put(pp, HEADER + '\n\n### 缺日期乙\n- 适用: s\n- 做法: a\n- 验证: 只写结论\n')
        out = run('inspect', '--scope', 'project', *overlay()).stdout
        assert 'structure: readable:' in out and 'entries: 1' in out, out
        result = run('recall', *overlay())
        assert result.returncode == 0 and '缺日期乙' in result.stdout, result.stdout
        checks.append('缺日期记录：inspect 标 readable（不再 invalid），recall 仍可输出，两者一致')

        # 逐条打捞：一条坏记录不再让同文件其余记录失联
        put(pp, HEADER + '\n\n' + record('好记录甲') + '\n' + '### 坏记录乙\n- 适用: s\n随手插一行\n- 做法: a\n- 验证: 2026-01-01 x\n'
            + '\n' + record('好记录丙'))
        result = run('recall', *overlay(), code=1)
        assert '好记录甲' in result.stdout and '好记录丙' in result.stdout, result.stdout
        assert '坏记录乙' in result.stdout and '已跳过该条' in result.stdout, result.stdout
        assert '好记录甲' not in result.stderr, result.stderr
        out = run('inspect', '--scope', 'project', *overlay()).stdout
        assert 'structure: partial:' in out and 'entries: 2' in out, out
        assert '记录 `坏记录乙` 读不出' in out, out
        # 写入侧仍以整份严格校验拒绝，不在坏文件上继续积累
        rejected(['add', '--scope', 'project', '--title', '坏文件追加', *fields, *overlay()], 'FORMAT')
        # 全都读不出时退化为 invalid，但正文与容量仍要给出（inspect 是唯一维护入口）
        put(pp, HEADER + '\n\n### 全坏甲\n- 适用: s\n散落行\n- 做法: a\n- 验证: 2026-01-01 x\n')
        out = run('inspect', '--scope', 'project', *overlay()).stdout
        assert 'structure: invalid:' in out, out
        assert 'characters: 0 (limit' not in out and '无法按 UTF-8 解码' not in out, out
        # entries 与 structure 不能互相打架：strict 口径说 0 条可读，entries 行也必须先报
        # 「0 条可读」，读不出的条数单独标明；旧行为（entries: 1 宽松口径）正是此处要防的。
        assert '全坏甲' in out and 'entries: 0 条可读' in out, out
        assert '1 条读不出' in out and '标题行' in out, out
        result = run('recall', *overlay(), code=1)
        assert 'FORMAT' in result.stdout, result.stdout
        checks.append('逐条打捞：单条坏记录只跳过它自己并明确报出，同文件其余记录照常召回；写入侧仍整份拒绝')

        # 多条坏记录时逐条报出，不合并成一句
        put(pp, HEADER + '\n\n' + record('存活甲') + '\n### 坏一\n- 适用: s\nx\n- 做法: a\n- 验证: 2026-01-01 x\n'
            + '\n### 坏二\n- 适用: s\n- 做法: a\n- 验证: \n' + '\n' + record('存活乙'))
        result = run('recall', *overlay(), code=1)
        assert result.stdout.count('已跳过该条') == 2, result.stdout
        assert '坏一' in result.stdout and '坏二' in result.stdout, result.stdout
        assert '存活甲' in result.stdout and '存活乙' in result.stdout, result.stdout
        checks.append('多条坏记录逐条报出各自标题与原因，不静默合并')

        # 标题不合法（`###` 后缺空格、行首缩进）与散落内容：都不能被静默丢弃
        put(pp, HEADER + '\n\n### \n- 适用: s\n- 做法: a\n- 验证: 2026-01-01 x\n\n' + record('正常甲'))
        result = run('recall', *overlay(), code=1)
        assert '正常甲' in result.stdout, result.stdout
        assert '不是 `### 标题`' in result.stdout, result.stdout
        put(pp, HEADER + '\n\n  ### 缩进标题\n- 适用: s\n- 做法: a\n- 验证: 2026-01-01 x\n\n' + record('正常乙'))
        result = run('recall', *overlay(), code=1)
        assert '正常乙' in result.stdout and '缩进标题' in result.stdout, result.stdout
        assert '不是 `### 标题`' in result.stdout, result.stdout
        put(pp, HEADER + '\n\n孤零零的一行\n\n' + record('正常丙'))
        result = run('recall', *overlay(), code=1)
        assert '正常丙' in result.stdout and '散落' in result.stdout, result.stdout
        checks.append('标题不合法（缺空格/缩进）与散落内容都报出，不静默丢弃')

        # ① Markdown 水平线是记录边界：末尾散落内容不并进上一条好记录
        put(pp, HEADER + '\n\n' + record('水平线前的好记录') + '\n---\n以上为历史\n')
        result = run('recall', *overlay(), code=1)  # 散落内容本身仍算问题（exit=1），但好记录不能陪葬
        assert '水平线前的好记录' in result.stdout, result.stdout
        assert '以上为历史' in result.stdout and '散落' in result.stdout, result.stdout
        assert '已跳过该条' not in result.stdout, result.stdout   # 旧行为：好记录被水平线连坐判掉
        out = run('inspect', '--scope', 'project', *overlay()).stdout
        assert 'structure: partial: 1 条可读' in out and 'entries: 1' in out, out
        # 字段行以单个 `- ` 开头，绝不能撞上水平线判断
        put(pp, HEADER + '\n\n' + record('字段行不误判') + '\n')
        result = run('recall', *overlay())
        assert result.returncode == 0 and '字段行不误判' in result.stdout, result.stdout
        assert '水平线' not in result.stdout and '已跳过该条' not in result.stdout, result.stdout
        # 三种水平线字符（- * _）与 2 个 `-`（不是水平线，属散落内容）都要分清
        for rule in ('***', '___', '-----'):
            put(pp, HEADER + '\n\n' + record('边界甲') + '\n' + rule + '\n尾注\n')
            result = run('recall', *overlay(), code=1)
            assert '边界甲' in result.stdout and '已跳过该条' not in result.stdout, (rule, result.stdout)
            assert '尾注' in result.stdout, (rule, result.stdout)
        put(pp, HEADER + '\n\n' + record('两横非边界') + '\n--\n尾注\n')
        result = run('recall', *overlay(), code=1)
        assert '两横非边界' in result.stdout and '已跳过该条' in result.stdout, result.stdout
        # 水平线必须整行匹配：同行还有内容的行（`--- 同行尾注`）和以 `- *` 开头的正文行
        # （`- **加粗** 说明`）都不是边界；宽松匹配会把它们当边界而静默丢弃——原始文本必须
        # 仍出现在输出里。exit 码单列断言，免得「退出码不对」盖住真正的静默丢弃。
        put(pp, HEADER + '\n\n' + record('同行非边界') + '\n--- 同行尾注\n')
        result = run('recall', *overlay(), code=None)
        assert '同行尾注' in result.stdout, result.stdout          # 变异 B 下该词彻底消失（整行被吞）
        assert result.returncode == 1, (result.returncode, result.stdout)  # 记录被判坏，非 0
        assert '已跳过该条' in result.stdout, result.stdout        # 同行文本算「该记录有无法解析的行」
        assert '散落' not in result.stdout, result.stdout          # 不是 stray：它在记录块内部
        put(pp, HEADER + '\n\n' + record('星号行非边界') + '\n- **加粗** 说明\n')
        result = run('recall', *overlay(), code=None)
        # 断言锚在整行文本上（标题里不含「加粗」，不会被标题蒙混过关）
        assert '**加粗** 说明' in result.stdout, result.stdout    # `- *` 开头最易被宽松正则误当水平线
        assert result.returncode == 1, (result.returncode, result.stdout)
        assert '已跳过该条' in result.stdout, result.stdout
        checks.append('水平线必须整行匹配：`--- 同行尾注` 与 `- **加粗** 说明` 都不是边界，原文必须出现在输出里')

        checks.append('Markdown 水平线是记录边界：其后散落内容不并进上一条记录；-/*/_ 三种都算，单字段行不误判')

        # ② 缩进标题的诊断必须报出保留缩进的原始行，不能抹掉缩进后自相矛盾
        put(pp, HEADER + '\n\n  ### 缩进标题诊断\n- 适用: s\n- 做法: a\n- 验证: 2026-01-01 x\n'
            + '\n' + record('诊断旁证'))
        result = run('recall', *overlay(), code=1)
        assert '诊断旁证' in result.stdout, result.stdout
        assert '`  ### 缩进标题诊断`' in result.stdout, result.stdout   # 原始行保留行首缩进
        assert '行首有缩进' in result.stdout, result.stdout             # 并点明症状
        assert '`### 缩进标题诊断` 不是' not in result.stdout, result.stdout  # 不能抹掉缩进后自相矛盾
        checks.append('缩进标题的诊断报出保留缩进的原始行并点明症状，不再抹掉缩进后自相矛盾')

        # ③ entries 两种口径不能并排打架：不可用文件的 entries 与 strict 口径同号
        put(pp, HEADER + '\n\n### 全坏乙\n不是字段\n')
        out = run('inspect', '--scope', 'project', *overlay()).stdout
        assert 'structure: invalid:' in out and '没有一条可读记录' in out, out
        assert 'entries: 0' in out and '1 条读不出' in out, out
        assert 'entries: 1' not in out, out  # 旧行为：宽松口径盖过 strict 口径
        result = run('recall', *overlay(), code=1)
        assert '全坏乙' in result.stdout and 'FORMAT' in result.stdout, result.stdout
        # 正常文件里 entries 仍是可读记录条数（两种口径一致）
        put(pp, HEADER + '\n\n' + record('条数甲') + '\n\n' + record('条数乙'))
        out = run('inspect', '--scope', 'project', *overlay()).stdout
        assert 'structure: ok' in out and 'entries: 2' in out, out
        checks.append('inspect 的 entries 与 strict 口径一致：不可用文件报 0 条可读并单列读不出条数，正常文件仍等于可读条数')

        # ④ 水平线后紧跟一个「看起来像字段」的行：该行归散落，不能并进上一条记录
        put(pp, HEADER + '\n\n' + record('边界前的记录甲') + '\n---\n- 适用: 又是散落\n')
        result = run('recall', *overlay(), code=1)
        assert '边界前的记录甲' in result.stdout, result.stdout
        assert '已跳过该条' not in result.stdout, result.stdout   # 也不能连坐判掉上一条
        assert '散落内容 `- 适用: 又是散落`' in result.stdout, result.stdout
        out = run('inspect', '--scope', 'project', *overlay()).stdout
        assert 'structure: partial: 1 条可读、0 条读不出、1 处散落内容' in out, out
        checks.append('水平线后紧跟「像字段」的行仍归散落，不并进上一条记录也不连坐判掉它')

        # ⑤ CRLF 文件的水平线同样是记录边界；CRLF 坏标题的诊断不带 CR，两个症状独立给出
        crlf = lambda text: text.replace('\n', '\r\n')
        put(pp, crlf(HEADER + '\n\n' + record('CRLF边界乙') + '\n---\nCRLF尾注\n'))
        result = run('recall', *overlay(), code=1)
        assert 'CRLF边界乙' in result.stdout and '已跳过该条' not in result.stdout, result.stdout
        assert '散落内容 `CRLF尾注`' in result.stdout, result.stdout
        put(pp, crlf(HEADER + '\n\n  ###\n- 适用: s\n- 做法: a\n- 验证: 2026-01-01 x\n'))
        result = run('recall', *overlay(), code=1)
        bad = [line for line in result.stdout.split('\n') if '不是 `### 标题`' in line]
        assert bad and '\r' not in bad[0], result.stdout      # 诊断里不能带 CR（终端会被覆盖）
        assert '`  ###`' in bad[0], result.stdout             # 行首缩进必须保留
        assert '行首有缩进' in bad[0] and '`###` 后缺少空格与标题文字' in bad[0], bad[0]
        checks.append('CRLF 文件的水平线同样是边界；CRLF 坏标题诊断不带 CR，缩进与缺标题两个症状独立给出')

        # ⑥ U+3000 缩进标题：前导空白不止 ' '/'\t'，诊断必须照样点明「行首有缩进」
        put(pp, HEADER + '\n\n\u3000### 全角空格缩进标题\n- 适用: s\n- 做法: a\n- 验证: 2026-01-01 x\n'
            + '\n' + record('全角旁证'))
        result = run('recall', *overlay(), code=1)
        assert '全角旁证' in result.stdout, result.stdout
        assert '`\u3000### 全角空格缩进标题`' in result.stdout, result.stdout
        assert '行首有缩进' in result.stdout, result.stdout
        checks.append('U+3000/U+00A0 等前导空白同样判为「行首有缩进」，诊断不再报出一行看着合法的串')

        # ⑦ 缺头行文件：能解码、有正文，entries 必须给出 `###` 标题行数提示，别像空文件
        put(pp, record('无头甲') + '\n' + record('无头乙') + '\n' + record('无头丙'))
        out = run('inspect', '--scope', 'project', *overlay()).stdout
        assert 'structure: invalid:' in out and '首个非空行不是' in out, out
        assert '文件里共 3 个 `###` 标题行' in out, out    # 旧行为：光秃秃的 `entries: 0`
        assert '别当成空文件整份覆盖' in out, out
        checks.append('缺头行文件的 entries 带上 `###` 标题行数提示，不会被误当成空文件整份覆盖')

        # ⑧ READ_ERROR（路径是目录/权限不足）≠ 编码错误：不得谎报「0 字节、无法按 UTF-8 解码」
        broken = base / 'readerr'
        (broken / '.agents' / 'gotchas.md').mkdir(parents=True, exist_ok=True)
        out = run('inspect', '--scope', 'project', '--project', str(broken),
                  '--global-path', str(gp)).stdout
        assert 'READ_ERROR' in out, out
        assert '0 字节' not in out and '无法按 UTF-8 解码' not in out, out
        assert '文件读不出' in out and 'entries: 未知' in out, out
        checks.append('READ_ERROR（目录/权限）与解码失败分文案：不再谎报 0 字节与无法按 UTF-8 解码')

        # 多关键词：按命中词数降序重排（1 命中的故意写在文件最前，能证伪「不排序」），同命中数保持原文顺序
        put(pp, HEADER + '\n\n' + record('同命中甲丁') + '\n\n' + record('命中一个词甲')
            + '\n\n' + record('命中两个词甲丙'))
        put(Path(str(gp)), HEADER + '\n\n' + record('全局也命中甲丙'))
        result = run('recall', '甲', '丙', *overlay())
        out = result.stdout
        assert out.index('命中两个词甲丙') < out.index('同命中甲丁'), out
        assert out.index('同命中甲丁') < out.index('命中一个词甲'), out
        assert out.index('[project]') < out.index('[global]'), out
        checks.append('多关键词按命中数降序重排（不依赖原文顺序），同命中数保持原文顺序，项目仍先于全局')

        # 全不命中时列出可用标题，而不是只回一句无结果
        result = run('recall', '绝不存在的词xyz', *overlay())
        assert result.returncode == 0 and 'No matching gotchas' in result.stdout, result.stdout
        assert '命中两个词甲丙' in result.stdout and '同命中甲丁' in result.stdout, result.stdout
        checks.append('关键词全不命中时列出全部可用标题，便于换词重查')

        # promote 报告两份文件的版本
        put(pp, HEADER + '\n')
        put(cp, HEADER + '\n\n' + record('版本候选庚'))
        report = json.loads(run('promote', '版本候选庚', '--scope', 'project', *overlay()).stdout)
        assert report['message'] == 'PROMOTED' and len(report['source_version']) == 64 \
            and len(report['target_version']) == 64, report
        assert report['target_version'] == version_of(pp.read_bytes())
        checks.append('promote 结果带两份文件的 version，PARTIAL 时调用方无需再跑一次 inspect')

        # --project-path 传目录时，候选落在该目录内而不是它的上一级
        put(pp, HEADER + '\n')
        report = json.loads(run('add', '--scope', 'candidate', '--title', '目录语义辛',
                                *fields, '--project-path', str(pp.parent), *overlay()[2:]).stdout)
        assert Path(report['path']) == cp, report
        assert '目录语义辛' in cp.read_text(encoding='utf-8')
        checks.append('--project-path 传已存在目录时按该目录下的 gotchas.md 处理，候选不再写错位置')

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
    reader.add_argument('keywords', nargs='*', metavar='关键词',
                        help='可选；给多个词时按命中词数排序，全不命中则列出可用标题')

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
