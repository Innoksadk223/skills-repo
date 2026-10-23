#!/usr/bin/env python3
"""capture-gotcha 记忆存储：纯标准库 + Markdown。

运行要求：Python >= 3.8，零第三方依赖；Linux / macOS / Windows 均可运行。
锁优先 fcntl（POSIX）、其次 msvcrt（Windows 字节区间锁）；两者都不可用时
退化为不加锁，仍用同目录临时文件 + os.replace 原子替换。Windows 锁未在真机验证。

三份文件（全局 / 项目 / 候选）用同一个硬上限 LIMIT 个 Unicode 码点。
写入入口统一在短时文件锁内做读-改-写，先验证容量、版本与结构，
再用同目录临时文件原子替换；失败一律不写、不截断、不清空。

记什么、写哪个范围由 AI 依据技能规则判断；脚本只保障容量、版本与写入安全，
不核实事实、不做完备脱敏。
"""
from __future__ import annotations
import argparse, difflib, errno, hashlib, importlib, json, os, re, sys, tempfile, time
from contextlib import ExitStack, contextmanager
from pathlib import Path

try:  # POSIX 文件锁
    fcntl = importlib.import_module('fcntl')
except ImportError:
    fcntl = None
try:  # Windows 文件锁
    msvcrt = importlib.import_module('msvcrt')
except ImportError:
    msvcrt = None

LOCK_BACKEND = 'fcntl' if fcntl is not None else 'msvcrt' if msvcrt is not None else 'none'

LIMIT = 4000  # Unicode 码点硬上限，三份文件相同；不提供抬高上限的开关
NEAR = 85  # characters_after 达到上限的 85% 即提示接近满容量
DEFAULT_GLOBAL_HOME = Path.home() / '.agents'
GLOBAL_PATH = DEFAULT_GLOBAL_HOME / 'gotchas.md'
CANDIDATES_NAME = 'gotchas-candidates.md'
HEADER = '# Gotchas'
NEW_FIELDS = ('适用', '做法', '关键词')  # 现行三字段：什么错 + 怎么改 + 检索词
LEGACY_FIELDS = ('date', 'scene', 'cause', 'evidence', 'fix')  # 旧五字段，只读兼容
LEGACY_THREE_FIELDS = ('适用', '做法', '验证')  # 旧三字段，只读兼容
FIELD_LIMITS = {'适用': 120, '做法': 240, '关键词': 80}  # 单字段字符硬上限
FIELD_LINE = re.compile(r'^- ([^:：]+)[:：]\s*(.*)$')  # 半角与全角冒号都接受
# Markdown 水平线＝记录边界。必须整行匹配——`\s*$` 不能省：`- **加粗** 说明`、
# `--- 同行尾注` 这类同行还有内容的行本身是内容，宽松匹配会把它们当边界而静默丢弃
# （原始行不再出现在任何输出里）。`- 字段: 值` 只有一个 `-`，匹配不上这套「3 个及以上」。
RULE_LINE = re.compile(r'^\s*[-*_](?:\s*[-*_]){2,}\s*$')
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
    """探测起点：--project 指定目录，默认 cwd；这里只解析路径，不做向上探测。"""
    return Path(value or os.getcwd()).resolve()


def detect_project_root(value=None, global_file=None):
    """从起点向上探测项目根：优先最近含 .agents/gotchas.md 的祖先，其次最近 .git，最后起点。

    只用文件系统判断，不调用 git；.git 是目录还是文件都算。返回 (根目录, source)，
    source 取 nearest / git / cwd，供 inspect 展示。

    global_file 是全局记忆文件路径：候选命中它时跳过并继续向上。
    否则项目在 $HOME 下时，~/.agents/gotchas.md 会被当成「这个项目的记忆」，
    项目记忆和全局记忆变成同一份，项目条目实际写进全局。
    """
    start = project_root(value)
    lineage = [start] + list(start.parents)
    blocked = global_file.resolve() if global_file else None
    for directory in lineage:
        memory = (directory / '.agents' / 'gotchas.md').resolve()
        if memory == blocked:
            continue
        if memory.exists():
            return directory, 'nearest'
    for directory in lineage:
        if (directory / '.git').exists():
            return directory, 'git'
    return start, 'cwd'


def global_home():
    """GOTCHA_HOME 决定全局记忆根目录；空串或相对路径回退默认 ~/.agents。"""
    default = Path.home() / '.agents'
    raw = os.environ.get('GOTCHA_HOME')
    if raw is None:
        return default, 'default', None
    value = raw.strip()
    if not value:
        return default, 'default', 'GOTCHA_HOME 是空字符串，已回退默认 ~/.agents'
    path = Path(value).expanduser()
    if not path.is_absolute():
        return default, 'default', 'GOTCHA_HOME 是相对路径（{}），不是绝对路径，已回退默认 ~/.agents'.format(value)
    return path, 'env', None


def global_home_fields():
    """写命令输出里的全局根目录信息；非法 GOTCHA_HOME 自带回退说明。"""
    home, source, note = global_home()
    fields = {'global_home': str(home), 'global_home_source': source}
    if note:
        fields['global_home_note'] = note
    return fields


def paths_for(project=None, global_path=None, project_path=None):
    """--project 是向上探测的起点（默认 cwd）；--project-path 显式覆盖优先于探测。

    项目根按「最近祖先 .agents/gotchas.md > 最近祖先 .git > 起点」确定；
    全局根默认 ~/.agents，可由 GOTCHA_HOME 重定向。
    --project-path 语义是文件路径；若传进来的其实是已存在的目录，
    按「该目录下的 gotchas.md」处理，避免候选被写到目录的上一级。
    """
    if global_path:
        gpath = Path(global_path).expanduser()
    else:
        gpath = global_home()[0] / 'gotchas.md'
    if project_path:
        ppath = Path(project_path).expanduser()
        if ppath.is_dir():
            ppath = ppath / 'gotchas.md'
    else:
        root, _ = detect_project_root(project, gpath)
        ppath = root / '.agents' / 'gotchas.md'
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


def legacy_hint():
    """旧格式的统一迁移提示：能单条改就 edit，要整份改就 replace。"""
    return ('先用 `edit --from-entry` 单条迁移，或用 `replace` 按新格式（适用/做法/关键词）'
            '整份迁移；未写入。')


def legacy_error(label, title, kind):
    if kind == 'five':
        detail = '仍是旧五字段（date/scene/cause/evidence/fix）'
    else:
        detail = '仍是旧三字段（适用/做法/验证，含已删除的「验证」）'
    return 'LEGACY_FORMAT: {} 记录 `{}` {}；写入入口只接受新格式（适用/做法/关键词）。{}' \
        .format(label, title, detail, legacy_hint())


def validate_structure(text, label, allow_legacy=False):
    """结构校验：`# Gotchas` 头行 + 每条 `### 标题` 与三字段（适用/做法/关键词）。

    默认只接受现行三字段，并检查单字段字符上限；旧五字段与旧三字段（含「验证」）
    会被明确拒绝，用于拒绝旧格式的输入本身。allow_legacy=True 时接受完整的旧格式
    记录（用于「同一文件里 legacy 与新格式共存」的追加/维护），但新格式记录仍按
    字段顺序、非空与字符上限严格校验，散落行/坏记录照旧拒绝。
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
        fields = []
        while index < total:
            key, value = field_of(lines[index])
            if key is None:
                break
            fields.append((key, value))
            index += 1
        keys = [key for key, _ in fields]
        if keys == list(LEGACY_FIELDS) or keys == list(LEGACY_THREE_FIELDS):
            if allow_legacy:
                continue
            kind = 'five' if keys == list(LEGACY_FIELDS) else 'three'
            raise StoreError(legacy_error(label, title, kind))
        if any(key in LEGACY_FIELDS for key in keys) or '验证' in keys:
            kind = 'five' if any(key in LEGACY_FIELDS for key in keys) else 'three'
            raise StoreError(legacy_error(label, title, kind))
        if keys != list(NEW_FIELDS):
            raise StoreError('FORMAT: {} 记录 `{}` 缺少或错序字段（应为 {}，实际为 {}）；未写入。'
                             .format(label, title, list(NEW_FIELDS), keys or '空'))
        for field, value in fields:
            if not value:
                raise StoreError('FORMAT: {} 记录 `{}` 的 `{}` 值为空；未写入。'.format(label, title, field))
            limit = FIELD_LIMITS[field]
            if len(value) > limit:
                raise StoreError('FORMAT: {} 记录 `{}` 的 `{}` 有 {} 字符，超过上限 {}；'
                                 '写不下说明这条该拆或不该收；未写入。'
                                 .format(label, title, field, len(value), limit))
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
    """判定单条记录是否可读：返回 (原因或 None, 旧格式种类或 None)。

    标题行必须严格是 `### 标题`。缩进、缺空格、多一个 `#` 都算坏记录——但要给出原始行，
    让人一眼知道是哪一行、怎么修：报出的是保留行首缩进的原文，行首有缩进或 `###`
    后缺标题文字时再点明具体症状；不能像去掉缩进那样报出一行看着完全合法的文字，
    否则与「不是 `### 标题`」自相矛盾。

    旧五字段与旧三字段（适用/做法/验证）都算可读，分别返回 'five' / 'three'，
    供 recall 原样输出、inspect 标注 legacy；写入入口会另行拒绝它们。
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
        return reason, None
    body = [line for line in entry.split('\n')[1:] if line.strip()]
    if len(fields) != len(body):
        stray = body[len(fields)].strip()
        return '有无法解析的行 `{}`'.format(stray[:40]), None
    keys = [key for key, _ in fields]
    if keys == list(LEGACY_FIELDS):
        return None, 'five'
    if keys == list(LEGACY_THREE_FIELDS):
        return None, 'three'
    if keys != list(NEW_FIELDS):
        return ('字段为 {}，既不是现行 {} 也不是完整旧五字段/旧三字段'
                .format(keys or '空', list(NEW_FIELDS))), None
    for key, value in fields:
        if not value:
            return '字段 `{}` 值为空'.format(key), None
    return None, None


def salvage(text):
    """逐条打捞：返回 (可读记录, [(标题, 原因), ...], [(标题, 旧格式种类), ...], 散落内容行)。

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
    usable, skipped, legacy = [], [], []
    for chunk in chunks:
        entry = '\n'.join(chunk).rstrip()
        if not entry:
            continue
        reason, legacy_kind = diagnose(entry)
        title, _ = parse_entry(entry)
        if reason:
            skipped.append((title or '(无标题)', reason))
            continue
        if legacy_kind:
            legacy.append((title, legacy_kind))
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

    字段名（适用/做法/关键词）每条都有，若纳入匹配，任何以它们为关键词的查询都会
    命中全部记录，排序随之失效。
    """
    title, fields = parse_entry(entry)
    return title + '\n' + '\n'.join(value for _, value in fields)


def legacy_summary(legacy):
    """把 [(标题, 'five'|'three'), ...] 压成给人看的中文摘要。"""
    five = sum(1 for _, kind in legacy if kind == 'five')
    three = sum(1 for _, kind in legacy if kind == 'three')
    parts = []
    if five:
        parts.append('旧五字段 {} 条'.format(five))
    if three:
        parts.append('旧三字段（含「验证」）{} 条'.format(three))
    return '、'.join(parts)


def near_limit(value):
    """容量接近上限：characters_after 达到 LIMIT 的 NEAR%（整数边界）。"""
    return value * 100 >= LIMIT * NEAR


def format_notes(scope, legacy):
    """可读但值得迁移的提示：legacy 与新格式可共存，但旧格式输入本身仍会被拒绝。"""
    if not legacy:
        return []
    return ['[{}] LEGACY_FORMAT: 有 {} 条旧格式记录（{}）；已按原样输出，'
            '文件里仍可追加/维护新格式记录，但旧格式输入会被拒绝；'
            '建议用 `edit --from-entry` 单条迁移或 `replace` 整份迁移到新格式'
            '（适用/做法/关键词）。'.format(scope, len(legacy), legacy_summary(legacy))]


# ---------- 锁与写入 ----------

LOCK_DEGRADED_NOTE = ('LOCK_DEGRADED: 无锁降级：当前环境没有 fcntl/msvcrt，未加锁；'
                      '仍使用同目录临时文件 + os.replace 原子替换。')


def lock_fields():
    """写命令输出里的锁后端信息；无锁时附降级说明。"""
    fields = {'lock': LOCK_BACKEND}
    if LOCK_BACKEND == 'none':
        fields['lock_note'] = LOCK_DEGRADED_NOTE
    return fields


def _msvcrt_busy(exc):
    return exc.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK)


@contextmanager
def locked(directory, exclusive=False, create=False):
    """锁同目录锁文件：POSIX fcntl / Windows msvcrt；都不可用时降级为无锁。

    BUSY 重试仍沿用 LOCK_TRIES / LOCK_WAIT。Windows 没有共享锁语义，
    读写都按同一个字节区间加独占锁；无锁后端只保证同目录临时文件 + os.replace。
    """
    if not directory.exists():
        if not create:
            yield
            return
        directory.mkdir(parents=True, exist_ok=True)
    if LOCK_BACKEND == 'none':
        yield
        return
    fd = os.open(str(directory / LOCK_NAME), os.O_RDWR | os.O_CREAT, 0o600)
    acquired = False
    try:
        if LOCK_BACKEND == 'msvcrt' and os.fstat(fd).st_size == 0:
            os.write(fd, b'\0')  # _locking 需要至少一个字节的区间
        for attempt in range(LOCK_TRIES):
            try:
                if LOCK_BACKEND == 'fcntl':
                    fcntl.flock(fd, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
                else:
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                acquired = True
                break
            except BlockingIOError:
                pass
            except OSError as exc:
                if not (LOCK_BACKEND == 'msvcrt' and _msvcrt_busy(exc)):
                    raise
            if attempt == LOCK_TRIES - 1:
                raise StoreError('BUSY: 记忆目录正被其他写入者维护，稍后重试；不要删锁文件。')
            time.sleep(LOCK_WAIT)
        yield
    finally:
        if acquired:
            try:
                if LOCK_BACKEND == 'fcntl':
                    fcntl.flock(fd, fcntl.LOCK_UN)
                else:
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
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

# 除 \n 外，这些字符也会被 splitlines() 当行分隔符，本地文件里它们只是内容，
# 但渲染与 grep 会把一行看成多行；一律拒写，免得一条记录长得像几条。
LINE_BREAKERS = '\u2028\u2029\u0085\x0b\x0c\x1c\x1d\x1e'


def single_line(value, name):
    """字段值必须是单行：换行会被拼成额外记录或非字段行，等于注入。"""
    text = redact(value)
    if '\n' in text or '\r' in text or any(ch in text for ch in LINE_BREAKERS):
        raise StoreError('FORMAT: {} 不能含换行或 Unicode 行分隔符（U+2028/U+2029/U+0085 等）；'
                         '每条记录每字段各占一行，多行内容请压成一句、或改写成并列短语。未写入。'
                         .format(name))
    return text


def field_value(value, name, field):
    """单字段值：非空 + 单行 + 不超过该字段的字符硬上限。"""
    text = single_line(value, name)
    if not text:
        raise StoreError('FORMAT: {} 不能为空；未写入。'.format(name))
    limit = FIELD_LIMITS[field]
    if len(text) > limit:
        raise StoreError('FORMAT: {} 有 {} 字符，超过 `{}` 上限 {}；'
                         '写不下说明这条该拆或不该收；未写入。'
                         .format(name, len(text), field, limit))
    return text


def entry_from_values(title, when, action, keywords):
    """用新三字段拼一条规范化记录（半角冒号、单行、各字段上限）。"""
    title = single_line(title, '标题')
    if not title:
        raise StoreError('FORMAT: 标题不能为空；未写入。')
    return '### {}\n- 适用: {}\n- 做法: {}\n- 关键词: {}\n'.format(
        title, field_value(when, '--when', '适用'),
        field_value(action, '--action', '做法'),
        field_value(keywords, '--keywords', '关键词'))


def make(a):
    keywords = getattr(a, 'keywords', None)
    if keywords is None:
        keywords = a.title  # 省略 --keywords 时用标题作为检索词
    return entry_from_values(a.title, a.when, a.action, keywords)


def check_legacy_args(a):
    used = [name for name in LEGACY_FIELDS + ('verified',) if getattr(a, name, None) is not None]
    if used:
        raise StoreError('LEGACY_FORMAT: add 只接受新格式（--title/--when/--action/--keywords）；'
                         '不再接受旧字段 {}。{}'.format(
                             '、'.join('--' + x for x in used), legacy_hint()))


def parse_fragment(text, label):
    """解析一条 markdown 片段：首个非空行 `### 标题`，其后字段严格按序。

    半角/全角冒号都接受，首尾空行忽略；片段只能有一条记录。旧五字段与旧三字段
    在这里明确拒绝，并指向 edit / replace 的迁移路径。
    """
    lines = text.split('\n')
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        raise StoreError('FORMAT: {} 是空的，首行必须是 `### 标题`；未写入。'.format(label))
    first = lines[0].rstrip('\r')
    if not first.startswith('### ') or not first[4:].strip():
        raise StoreError('FORMAT: {} 首个非空行必须是 `### 标题`；未写入。'.format(label))
    title = first[4:].strip()
    fields = []
    for offset, line in enumerate(lines[1:], start=2):
        if line.lstrip().startswith('###'):
            raise StoreError('FORMAT: {} 只能包含一条记录，第 {} 行又出现了标题行；未写入。'
                             .format(label, offset))
        if not line.strip():
            raise StoreError('FORMAT: {} 第 {} 行是空行，字段必须连续、严格按序；未写入。'
                             .format(label, offset))
        key, value = field_of(line)
        if key is None:
            raise StoreError('FORMAT: {} 第 {} 行不是 `- 字段: 值`；未写入。'.format(label, offset))
        fields.append((key, value))
    keys = [key for key, _ in fields]
    if keys == list(LEGACY_FIELDS):
        raise StoreError(legacy_error(label, title, 'five'))
    if keys == list(LEGACY_THREE_FIELDS) or '验证' in keys:
        raise StoreError(legacy_error(label, title, 'three'))
    if keys != list(NEW_FIELDS):
        raise StoreError('FORMAT: {} 的字段必须严格按序为 {}，实际为 {}；未写入。'
                         .format(label, list(NEW_FIELDS), keys or '空'))
    values = dict(fields)
    return title, entry_from_values(title, values['适用'], values['做法'], values['关键词'])


def read_fragment(source):
    """读 `--from-entry`：`-` 表示 stdin，其余按 UTF-8 文件路径读取。"""
    if source == '-':
        return decode(sys.stdin.buffer.read(), '<stdin>')
    path = Path(source).expanduser()
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise StoreError('READ_ERROR: 无法读取片段 {}：{}；未写入。'.format(path, exc))
    return decode(raw, str(path))


def append_text(text, item):
    base = text.rstrip()
    if not base:
        base = HEADER
    return base + '\n\n' + item


def titles(text):
    return [line[4:].strip() for line in text.split('\n') if line.startswith('### ')]


def duplicate(text, item):
    """去重规则保持简单：标题完全相同（忽略大小写与首尾空白）才算重复，并回报命中的标题。"""
    title = item.split('\n', 1)[0][4:].strip().lower()
    for existing in titles(text):
        if title == existing.strip().lower():
            return existing
    return ''


def load(path):
    raw = read_bytes(path)
    return raw, decode(raw, str(path))


def old_over_limit(text, path):
    return count(text) > LIMIT


def located_entries(text):
    """按字符偏移定位每条记录的标题行到最后一个字段行（不含其后空行）。

    单条编辑/删除只替换这一段，前后字节原样保留；标题行必须顶格且为 `### 标题`，
    坏文件在 ensure_maintainable 里先被拒绝，不会走到这里。

    切行口径必须与 validate_structure / salvage / field_of 一致，一律按 `\\n`：
    用 splitlines() 会把 U+2028 这类字符当行尾，记录跨度被截短，drop/edit 就只删半条。
    """
    lines = re.findall(r'[^\n]*\n|[^\n]+$', text)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    found = []
    for index, line in enumerate(lines):
        if not (line.startswith('### ') and line[4:].strip()):
            continue
        title = line[4:].strip()
        cursor, fields = index + 1, []
        while cursor < len(lines):
            key, value = field_of(lines[cursor])
            if key is None:
                break
            fields.append((key, value))
            cursor += 1
        found.append({'title': title, 'fields': fields,
                      'start': offsets[index], 'end': offsets[cursor]})
    return found


def similar_titles(text, query, limit=3):
    """最相近的已有标题：先给子串命中，再用 difflib 补足，最多 limit 条。"""
    names = titles(text)
    lowered = [name.strip().lower() for name in names]
    needle = query.strip().lower()
    picked = []
    if needle:
        for name in names:
            low = name.strip().lower()
            if needle in low or low in needle:
                if name not in picked:
                    picked.append(name)
    for candidate in difflib.get_close_matches(needle, lowered, n=limit, cutoff=0.0):
        for name in names:
            if name.strip().lower() == candidate and name not in picked:
                picked.append(name)
                break
    return picked[:limit]


def not_found_error(path, query, text):
    similar = similar_titles(text, query)
    return StoreError('NOT_FOUND: {} 里没有标题为 `{}` 的记录（比较时忽略大小写与首尾空白）。'
                      '最相近的已有标题：{}；未写入。'
                      .format(path, query, '、'.join(similar) or '（无）'))


def find_entry(text, query, path):
    """按标题精确匹配（忽略大小写与首尾空白）；找不到时列出最相近的标题。"""
    needle = query.strip().lower()
    matches = [entry for entry in located_entries(text)
               if entry['title'].strip().lower() == needle]
    if not matches:
        raise not_found_error(path, query, text)
    if len(matches) > 1:
        raise StoreError('FORMAT: {} 有 {} 条标题同为 `{}` 的记录，无法唯一确定；'
                         '先用 replace 合并重名记录；未写入。'.format(path, len(matches), query))
    return matches[0]


def ensure_maintainable(text, path):
    """单条维护的前置检查：头行与逐条可读，坏文件不在上面继续改。"""
    if not text.strip():
        return
    if not header_ok(text):
        raise StoreError('FORMAT: {} 首个非空行必须是 `{}`；先用 replace 修复；未写入。'
                         .format(path, HEADER))
    _, skipped, _, stray = salvage(text)
    if skipped or stray:
        raise StoreError('FORMAT: {} 有 {} 条记录读不出、{} 处散落内容；'
                         '先用 replace 修复整份文件，再做单条维护；未写入。'
                         .format(path, len(skipped), len(stray)))


def add(a):
    check_legacy_args(a)
    from_entry = getattr(a, 'from_entry', None)
    long_args = [name for name in ('title', 'when', 'action', 'keywords')
                 if getattr(a, name, None) is not None]
    if from_entry:
        if long_args:
            raise StoreError('FORMAT: add 的 --from-entry 不能与 {} 同时使用；未写入。'
                             .format('、'.join('--' + name for name in long_args)))
        _, item = parse_fragment(read_fragment(from_entry), str(from_entry))
    else:
        missing = [name for name in ('title', 'when', 'action') if not getattr(a, name, None)]
        if missing:
            raise StoreError('FORMAT: add 缺少必填参数 {}；未写入。'
                             .format('、'.join('--' + x for x in missing)))
        item = make(a)
    path = path_for(a.scope, a.project, a.global_path, a.project_path)
    with locked(path.parent, exclusive=not a.dry_run, create=not a.dry_run):
        raw, text = load(path)
        if old_over_limit(text, path):
            raise StoreError('OVER_LIMIT: {}: {} > {} 码点；add 不再累积，先用 replace 修复。'.format(path, count(text), LIMIT))
        validate_structure(append_text(HEADER, item), 'add:--{}'.format(a.scope))
        report = {'ok': True, 'command': 'add', 'scope': a.scope, 'path': str(path),
                  'limit': LIMIT, 'dry_run': bool(a.dry_run), 'item': item,
                  'characters_before': count(text), 'characters_after': count(text),
                  'near_limit': near_limit(count(text)),
                  **lock_fields(), **global_home_fields()}
        same = duplicate(text, item)
        if same:
            report.update(skipped=True, matched=same,
                          message='SKIP: 标题与已有记录 `{}` 相同，未写入；'
                                  '若确是新规则，请改用不同标题。'.format(same))
            return report
        new_text = append_text(text, item)
        validate_structure(new_text, str(path), allow_legacy=True)
        after = capacity(new_text, str(path))
        report['characters_after'] = after
        report['near_limit'] = near_limit(after)
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
        validate_structure(source_text, str(source), allow_legacy=True)
        validate_structure(target_text, str(target), allow_legacy=True)
        found = entries(source_text)
        hits = [entry for entry in found if a.keyword.lower() in entry.lower()]
        if len(hits) != 1:
            raise StoreError('ERROR: promote 需要唯一匹配的候选，实际匹配 {} 条；未写入。'.format(len(hits)))
        item = hits[0] + '\n'
        validate_structure(HEADER + '\n\n' + item, 'promote:item', allow_legacy=False)
        report = {'ok': True, 'command': 'promote', 'keyword': a.keyword, 'scope': a.scope,
                  'source': str(source), 'target': str(target), 'limit': LIMIT,
                  'source_version': version_of(source.read_bytes()),
                  'target_version': version_of(target.read_bytes()),
                  'target_characters': count(target_text),
                  'characters_after': count(target_text),
                  'near_limit': near_limit(count(target_text)),
                  'dry_run': bool(a.dry_run), 'item': item,
                  **lock_fields(), **global_home_fields()}
        same = duplicate(target_text, item)
        if same:
            report.update(skipped=True, matched=same, message='SKIP: 目标已有同类记录 `{}`；候选保留未删'.format(same))
            return report
        new_target = append_text(target_text, item)
        remaining = [entry for entry in found if entry != hits[0]]
        new_source = (HEADER + '\n\n' + '\n\n'.join(remaining) + '\n') if remaining else HEADER + '\n'
        validate_structure(new_target, str(target), allow_legacy=True)
        validate_structure(new_source, str(source), allow_legacy=True)
        report['target_characters'] = capacity(new_target, str(target))
        report['characters_after'] = report['target_characters']
        report['candidate_characters'] = capacity(new_source, str(source))
        report['candidate_remaining'] = len(remaining)
        report['near_limit'] = near_limit(report['target_characters'])
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


def edit(a):
    """按标题单条修改：只替换命中的那一条，其余字节保持不变。"""
    from_entry = getattr(a, 'from_entry', None)
    field_args = [name for name in ('when', 'action', 'keywords')
                  if getattr(a, name, None) is not None]
    replacement = None
    if from_entry:
        if field_args:
            raise StoreError('FORMAT: edit 的 --from-entry 不能与 {} 同时使用；未写入。'
                             .format('、'.join('--' + name for name in field_args)))
        _, replacement = parse_fragment(read_fragment(from_entry), str(from_entry))
    elif not field_args:
        raise StoreError('FORMAT: edit 需要 --from-entry 或至少一个字段参数'
                         '（--when/--action/--keywords）；未写入。')
    path = path_for(a.scope, a.project, a.global_path, a.project_path)
    with locked(path.parent, exclusive=not a.dry_run, create=not a.dry_run):
        raw, text = load(path)
        version = version_of(raw)
        if a.expect != version:
            raise StoreError('STALE_VERSION: {} 当前版本 {}，与 --expect {} 不符；本次未写入。'
                             .format(path, version, a.expect))
        ensure_maintainable(text, path)
        located = find_entry(text, a.title, path)
        if replacement is None:
            original = text[located['start']:located['end']]
            _, fields = parse_entry(original)
            keys = [key for key, _ in fields]
            if keys == list(LEGACY_FIELDS):
                raise StoreError(legacy_error(str(path), located['title'], 'five'))
            if keys == list(LEGACY_THREE_FIELDS) or '验证' in keys:
                raise StoreError(legacy_error(str(path), located['title'], 'three'))
            if keys != list(NEW_FIELDS):
                raise StoreError('FORMAT: {} 记录 `{}` 的字段为 {}，不是现行 {}；未写入。'
                                 .format(path, located['title'], keys or '空', list(NEW_FIELDS)))
            values = dict(fields)
            for field, name in zip(NEW_FIELDS, ('when', 'action', 'keywords')):
                value = getattr(a, name, None)
                if value is not None:
                    values[field] = field_value(value, '--' + name, field)
            replacement = entry_from_values(located['title'], values['适用'], values['做法'], values['关键词'])
        new_title = replacement.split('\n', 1)[0][4:].strip()
        if new_title.strip().lower() != located['title'].strip().lower():
            others = [name for name in titles(text)
                      if name.strip().lower() == new_title.strip().lower()]
            if others:
                raise StoreError('DUPLICATE: 已有同名记录 `{}`；改名不能撞上既有标题；未写入。'
                                 .format('、'.join(dict.fromkeys(others))))
        new_text = text[:located['start']] + replacement + text[located['end']:]
        after = capacity(new_text, str(path))
        report = {'ok': True, 'command': 'edit', 'scope': a.scope, 'path': str(path),
                  'title': new_title, 'previous_title': located['title'],
                  'limit': LIMIT, 'dry_run': bool(a.dry_run),
                  'characters_before': count(text), 'characters_after': after,
                  'entries_after': len(entries(new_text)), 'version_before': version,
                  'near_limit': near_limit(after), 'item': replacement,
                  **lock_fields(), **global_home_fields()}
        if a.dry_run:
            report['message'] = '[dry-run] 校验通过，未写入'
            return report
        atomic(path, new_text.encode('utf-8'))
        report['version_after'] = version_of(path.read_bytes())
        report['message'] = 'EDITED'
        return report


def drop(a):
    """按标题删除单条记录；只去掉那一条，其余字节保持不变。"""
    path = path_for(a.scope, a.project, a.global_path, a.project_path)
    with locked(path.parent, exclusive=not a.dry_run, create=not a.dry_run):
        raw, text = load(path)
        version = version_of(raw)
        if a.expect != version:
            raise StoreError('STALE_VERSION: {} 当前版本 {}，与 --expect {} 不符；本次未写入。'
                             .format(path, version, a.expect))
        ensure_maintainable(text, path)
        located = find_entry(text, a.title, path)
        new_text = text[:located['start']] + text[located['end']:]
        after = capacity(new_text, str(path))
        report = {'ok': True, 'command': 'drop', 'scope': a.scope, 'path': str(path),
                  'title': located['title'], 'deleted': 1, 'limit': LIMIT,
                  'dry_run': bool(a.dry_run), 'characters_before': count(text),
                  'characters_after': after, 'entries_after': len(entries(new_text)),
                  'version_before': version, 'near_limit': near_limit(after),
                  **lock_fields(), **global_home_fields()}
        if a.dry_run:
            report['message'] = '[dry-run] 校验通过，未写入'
            return report
        atomic(path, new_text.encode('utf-8'))
        report['version_after'] = version_of(path.read_bytes())
        report['message'] = 'DROPPED'
        return report


def recall(a):
    """只输出正式记忆：项目在先、全局在后；逐条打捞；多关键词按命中数排序。"""
    keywords = [word.lower() for word in (a.keywords or []) if word.strip()]
    targets = [('project', path_for('project', a.project, a.global_path, a.project_path)),
               ('global', path_for('global', a.project, a.global_path, a.project_path))]
    _, _, home_note = global_home()
    problems, index, hits_by_scope = [], [], {}
    notes = ['[global] GOTCHA_HOME: {}'.format(home_note)] if home_note else []
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
        notes += format_notes(scope, legacy)  # 旧格式仍可读，只提示迁移
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
    detected_root, project_source = detect_project_root(a.project, path_for('global', a.project,
                                                                         a.global_path, a.project_path))
    home, home_source, home_note = global_home()
    blocks = []
    for scope in ([a.scope] if a.scope else list(SCOPES)):
        path = path_for(scope, a.project, a.global_path, a.project_path)
        text, read_problem, legacy, write_problem = '', None, [], None
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
            extra = '；另有 {} 条旧格式（需用 edit 或 replace 迁移）'.format(len(legacy)) if legacy else ''
            state = ('partial: {} 条可读、{} 条读不出、{} 处散落内容'
                     '（recall 会输出可读的，并逐条报出其余）{}'
                     .format(len(usable), len(skipped), len(stray), extra))
        elif legacy:
            state = ('legacy: {} 条旧格式（{}；可读，可追加/维护新格式记录，'
                     '旧格式输入仍会被拒绝；建议用 edit 或 replace 迁移）'
                     .format(len(legacy), legacy_summary(legacy)))
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
        header_lines = ['scope: {}'.format(scope)]
        if scope in ('project', 'candidate'):
            header_lines += ['project_root: {}'.format(detected_root),
                             'source: {}'.format(project_source)]
        if scope == 'global':
            header_lines += ['global_home: {}'.format(home),
                             'global_home_source: {}'.format(home_source)]
        if home_note:
            header_lines.append('global_home_note: {}'.format(home_note))
        blocks.append('\n'.join(header_lines + [
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
                  'version_before': current_version, 'entries_after': len(entries(text)),
                  'near_limit': near_limit(new_count),
                  **lock_fields(), **global_home_fields()}
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

        def run(*args, code=0, input_text=None, cwd=None, env=None):
            """code=0/1 时照旧严格校验退出码；code=None 只取输出，退出码由调用方自己断言。

            需要 code=None 的场合：用例的首要证伪目标是「某段原文必须出现在输出里」，
            若先卡退出码，失败信息会只报「退出码不对」，把真正的静默丢弃盖在后面。
            """
            result = subprocess.run([sys.executable, '-B', script, *args], input=input_text,
                                    capture_output=True, text=True, timeout=60, cwd=cwd, env=env)
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

        def assert_lock(report):
            assert report.get('lock') in ('fcntl', 'msvcrt', 'none'), report
            if report['lock'] == 'none':
                assert report.get('lock_note') and '未加锁' in report['lock_note'], report

        def entry_text(title, when='s', action='a', keywords='k', eol='\n'):
            return ('### {}{}- 适用: {}{}- 做法: {}{}- 关键词: {}{}'
                    .format(title, eol, when, eol, action, eol, keywords, eol))

        def record(title, **kwargs):
            return entry_text(title, **kwargs)

        def legacy(title):
            return ('### {}\n- date: 2026-01-01\n- scene: s\n- cause: c\n'
                    '- evidence: e\n- fix: f\n'.format(title))

        def legacy_three(title):
            return '### {}\n- 适用: s\n- 做法: a\n- 验证: v\n'.format(title)

        def revision(size, title='cap', eol='\n'):
            """构造正好 size 个码点的合法新格式文件；eol 给 CRLF 时换行计入两个码点。

            单条记录受字段上限约束，所以用多条记录拼到目标容量；最后一条的「做法」
            补足余数（余数小于下一条记录长度）。
            """
            head = HEADER + eol + eol
            records, used, index = [], len(head), 0
            while True:
                name = title if index == 0 else 'r{:03d}'.format(index)
                chunk = entry_text(name, eol=eol)
                if used + len(chunk) > size:
                    break
                records.append([name, 'a'])
                used += len(chunk)
                index += 1
            assert records, '容量测试的 size 太小'
            remaining = size - used
            assert 0 <= remaining <= FIELD_LIMITS['做法'] - 1, (size, remaining)
            records[-1][1] = 'a' + '中' * remaining
            text = head + ''.join(entry_text(name, action=action, eol=eol)
                                  for name, action in records)
            assert len(text) == size, (len(text), size)
            return text

        fields = ['--when', 's', '--action', 'a', '--keywords', 'k']

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
        assert_lock(report)
        assert report['ok'] and report['message'] == 'ADDED' and report['near_limit'] is False
        body = pp.read_text(encoding='utf-8')
        assert report['characters_after'] == len(body) <= LIMIT
        assert '- 适用: s' in body and '- 做法: a' in body and '- 关键词: k' in body
        assert '- 验证:' not in body
        run('add', '--scope', 'global', '--title', '全局经验乙', *fields, *overlay())
        run('add', '--scope', 'candidate', '--title', '候选经验丙', *fields, *overlay())
        out = run('recall', *overlay()).stdout
        assert '[project]' in out and '[global]' in out and '[candidate]' not in out
        assert out.index('[project]') < out.index('[global]')
        out = run('recall', '项目约束甲', *overlay()).stdout
        assert '[project]' in out and '[global]' not in out
        checks.append('add 写新三字段（适用/做法/关键词）；recall 项目在先全局在后、关键词过滤、候选不召回')

        # 全角冒号兼容：正常中文写法不因标点差异丢记录
        wide = base / 'wide.md'
        put(wide, HEADER + '\n\n### 全角冒号记录\n- 适用：s\n- 做法：a\n- 关键词：k\n')
        report = json.loads(run('replace', '--scope', 'candidate', '--from-file', str(wide),
                                '--expect', version_of(cp.read_bytes()), *overlay()).stdout)
        assert report['ok'] and cp.read_bytes() == wide.read_bytes() and report['near_limit'] is False
        out = run('inspect', '--scope', 'candidate', *overlay()).stdout
        assert 'structure: ok' in out and '全角冒号记录' in out, out
        put(cp, HEADER + '\n\n' + record('候选经验丙'))
        checks.append('全角冒号与半角冒号都算合规，inspect/replace 不因标点丢记录')

        again = json.loads(run(*add_project).stdout)
        assert again['ok'] and again['skipped'] and again['matched'] == '项目约束甲'
        assert 'near_limit' in again
        short = json.loads(run('add', '--scope', 'project', '--title', '项目约束', *fields, *overlay()).stdout)
        assert short['ok'] and short['message'] == 'ADDED' and '### 项目约束' in pp.read_text(encoding='utf-8')
        longer = json.loads(run('add', '--scope', 'project', '--title', '项目约束甲乙丙', *fields, *overlay()).stdout)
        assert longer['ok'] and longer['message'] == 'ADDED'
        checks.append('重复记录按标题完全相同跳过并回报命中标题；子串不算重复，短标题与长标题都写得进去')

        # promote 正常转正 / dry-run
        before = snapshot()
        report = json.loads(run('promote', '候选经验丙', '--scope', 'global', '--dry-run', *overlay()).stdout)
        assert report['dry_run'] and snapshot() == before and report['candidate_remaining'] == 0
        assert report['near_limit'] == near_limit(report['target_characters'])
        assert report['characters_after'] == report['target_characters']
        report = json.loads(run('promote', '候选经验丙', '--scope', 'global', *overlay()).stdout)
        assert_lock(report)
        assert report['ok'] and report['message'] == 'PROMOTED'
        assert report['near_limit'] == near_limit(report['target_characters'])
        assert report['characters_after'] == report['target_characters']
        assert '候选经验丙' in gp.read_text(encoding='utf-8') and '候选经验丙' not in cp.read_text(encoding='utf-8')
        checks.append('promote 转正写入目标并移除候选；dry-run 结果一致且不写盘；near_limit 按目标容量计算')

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
            assert report['near_limit'] is True
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

        # 非法格式：缺字段 / 缺头行 / 字段错序 / 结构错乱 / 空值
        bad_field = base / 'bad-field.md'
        put(bad_field, HEADER + '\n\n### 缺字段\n- 适用: s\n- 做法: a\n')
        bad_head = base / 'bad-head.md'
        put(bad_head, '### 无头行\n- 适用: s\n- 做法: a\n- 关键词: k\n')
        bad_gap = base / 'bad-gap.md'
        put(bad_gap, HEADER + '\n\n### 字段间插言\n- 适用: s\n随手插一行\n- 做法: a\n- 关键词: k\n')
        bad_order = base / 'bad-order.md'
        put(bad_order, HEADER + '\n\n### 字段错序\n- 做法: a\n- 适用: s\n- 关键词: k\n')
        empty_value = base / 'empty-value.md'
        put(empty_value, HEADER + '\n\n### 空值\n- 适用: s\n- 做法: a\n- 关键词:   \n')
        for path in (bad_field, bad_head, bad_gap, bad_order, empty_value):
            rejected(['replace', '--scope', 'project', '--from-file', str(path),
                      '--expect', version_of(pp.read_bytes()), *overlay()], 'FORMAT')
        checks.append('非法格式（缺字段/缺头行/字段错序/结构错乱/空值）拒绝，避免 recall 静默忽略')

        # 字段硬上限：120 / 240 / 80，边界值可写，超一字符即拒绝
        put(pp, HEADER + '\n')
        report = json.loads(run('add', '--scope', 'project', '--title', '字段上限内',
                                '--when', '适' * 120, '--action', '做' * 240,
                                '--keywords', '词' * 80, *overlay()).stdout)
        assert report['message'] == 'ADDED'
        for name, value in (('when', '中' * 121), ('action', '中' * 241), ('keywords', '中' * 81)):
            put(pp, HEADER + '\n')
            args = ['add', '--scope', 'project', '--title', '字段超限' + name,
                    '--when', 's', '--action', 'a', '--keywords', 'k']
            args[args.index('--' + name) + 1] = value
            rejected([*args, *overlay()], '写不下说明这条该拆或不该收')
        limit_draft = base / 'limit-over.md'
        put(limit_draft, HEADER + '\n\n### 超长字段\n- 适用: s\n- 做法: ' + '中' * 241 + '\n- 关键词: k\n')
        rejected(['replace', '--scope', 'project', '--from-file', str(limit_draft),
                  '--expect', version_of(pp.read_bytes()), *overlay()], 'FORMAT')
        put(pp, HEADER + '\n\n' + record('编辑上限'))
        rejected(['edit', '编辑上限', '--scope', 'project', '--action', '中' * 241,
                  '--expect', version_of(pp.read_bytes()), *overlay()], 'FORMAT')
        limit_entry = base / 'limit-entry.md'
        put(limit_entry, '### 超长片段\n- 适用: s\n- 做法: ' + '中' * 241 + '\n- 关键词: k\n')
        rejected(['add', '--scope', 'project', '--from-entry', str(limit_entry), *overlay()], 'FORMAT')
        checks.append('适用/做法/关键词的 120/240/80 字符硬上限生效：边界可写、超限报 FORMAT 并提示该拆或不该收')

        # 可读但写入前需修：超限字段仍被 recall 原样输出，inspect 标 readable
        put(pp, HEADER + '\n\n### 超长做法\n- 适用: s\n- 做法: ' + '中' * 241 + '\n- 关键词: k\n')
        out = run('inspect', '--scope', 'project', *overlay()).stdout
        assert 'structure: readable:' in out and 'entries: 1' in out, out
        result = run('recall', *overlay())
        assert result.returncode == 0 and '超长做法' in result.stdout, result.stdout
        checks.append('非空但字段超限的记录：inspect 标 readable（可读但写入前需修），recall 仍可输出')

        # 旧五/旧三只读兼容；文件含 legacy 时仍可追加/维护新格式记录，旧格式输入本身仍拒绝
        put(pp, HEADER + '\n\n' + legacy('旧格式记录甲'))
        reject_legacy = base / 'reject-legacy.md'
        put(reject_legacy, HEADER + '\n\n' + legacy('旧格式写入乙'))
        rejected(['replace', '--scope', 'project', '--from-file', str(reject_legacy),
                  '--expect', version_of(pp.read_bytes()), *overlay()], 'LEGACY_FORMAT')
        rejected(['add', '--scope', 'project', '--title', '旧参数丙', '--scene', 's', '--cause', 'c',
                  '--evidence', 'e', '--fix', 'f', *overlay()], 'LEGACY_FORMAT')
        rejected(['add', '--scope', 'project', '--title', '旧验证丁', '--when', 's', '--action', 'a',
                  '--keywords', 'k', '--verified', '2026-01-01 虚构', *overlay()], 'LEGACY_FORMAT')
        report = json.loads(run('add', '--scope', 'project', '--title', '累积戊', *fields, *overlay()).stdout)
        assert report['message'] == 'ADDED' and report['characters_before'] > 0, report
        assert_lock(report)
        text = pp.read_text(encoding='utf-8')
        assert '旧格式记录甲' in text and '累积戊' in text and '- 关键词: k' in text, text
        result = run('recall', *overlay())
        assert result.returncode == 0 and '旧格式记录甲' in result.stdout and '累积戊' in result.stdout, result.stdout
        assert 'LEGACY_FORMAT' in result.stdout and '旧五字段' in result.stdout, result.stdout
        out = run('inspect', '--scope', 'project', *overlay()).stdout
        assert 'structure: legacy' in out and 'entries: 2' in out, out

        # legacy 文件里维护新格式记录：edit 与 drop 都不要求先整份迁移
        version = version_of(pp.read_bytes())
        report = json.loads(run('edit', '累积戊', '--scope', 'project', '--keywords', '新词',
                                '--expect', version, *overlay()).stdout)
        assert report['message'] == 'EDITED' and report['title'] == '累积戊', report
        assert_lock(report)
        text = pp.read_text(encoding='utf-8')
        assert '旧格式记录甲' in text and '- 关键词: 新词' in text, text
        report = json.loads(run('drop', '累积戊', '--scope', 'project',
                                '--expect', version_of(pp.read_bytes()), *overlay()).stdout)
        assert report['message'] == 'DROPPED' and report['deleted'] == 1, report
        assert_lock(report)
        text = pp.read_text(encoding='utf-8')
        assert '旧格式记录甲' in text and '累积戊' not in text, text

        # legacy 目标文件允许 promote 新格式候选；旧候选本身仍被拒绝
        put(pp, HEADER + '\n\n' + legacy('旧目标庚'))
        put(cp, HEADER + '\n\n' + record('新候选辛'))
        report = json.loads(run('promote', '新候选辛', '--scope', 'project', *overlay()).stdout)
        assert report['message'] == 'PROMOTED', report
        assert_lock(report)
        text = pp.read_text(encoding='utf-8')
        assert '旧目标庚' in text and '新候选辛' in text, text
        assert '新候选辛' not in cp.read_text(encoding='utf-8')
        out = run('inspect', '--scope', 'project', *overlay()).stdout
        assert 'structure: legacy' in out and 'entries: 2' in out, out

        put(pp, HEADER + '\n\n' + legacy_three('旧三字段记录乙') + '\n\n' + record('新格式陪跑'))
        result = run('recall', *overlay())
        assert result.returncode == 0 and '旧三字段记录乙' in result.stdout, result.stdout
        assert '旧三字段（含「验证」）' in result.stdout and 'LEGACY_FORMAT' in result.stdout, result.stdout
        out = run('inspect', '--scope', 'project', *overlay()).stdout
        assert 'structure: legacy' in out and '旧三字段' in out and 'entries: 2' in out, out
        put(cp, HEADER + '\n\n' + legacy_three('旧候选丙'))
        put(pp, HEADER + '\n\n' + record('目标正常'))
        rejected(['promote', '旧候选丙', '--scope', 'project', *overlay()], 'LEGACY_FORMAT')

        put(pp, HEADER + '\n\n' + legacy_three('待迁移丁') + '\n\n' + record('旁证'))
        version = version_of(pp.read_bytes())
        rejected(['edit', '待迁移丁', '--scope', 'project', '--keywords', 'x',
                  '--expect', version, *overlay()], 'LEGACY_FORMAT')
        migrate = base / 'migrate.md'
        put(migrate, '\n\n### 待迁移丁\n- 适用：新适\n- 做法：新做\n- 关键词：新词\n\n')
        report = json.loads(run('edit', '待迁移丁', '--scope', 'project', '--from-entry', str(migrate),
                                '--expect', version, *overlay()).stdout)
        assert report['message'] == 'EDITED' and report['near_limit'] is False
        assert_lock(report)
        text = pp.read_text(encoding='utf-8')
        assert '- 验证:' not in text and '- 关键词: 新词' in text and '旁证' in text, text

        put(pp, HEADER + '\n\n' + legacy('待删除戊') + '\n\n' + record('保留己'))
        report = json.loads(run('drop', '待删除戊', '--scope', 'project',
                                '--expect', version_of(pp.read_bytes()), *overlay()).stdout)
        assert report['message'] == 'DROPPED' and report['deleted'] == 1
        assert_lock(report)
        assert '待删除戊' not in pp.read_text(encoding='utf-8') and '保留己' in pp.read_text(encoding='utf-8')
        checks.append('legacy 与新格式共存：add/promote 可写入含 legacy 的文件，edit/drop 可维护新记录；'
                      '旧格式输入、per-field edit legacy 目标仍拒绝；edit --from-entry 可单条迁移')

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
        put(pp, HEADER + '\n\n' + record('容量目标'))
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

        # replace 修复超限文件
        put(pp, raw_over)
        fixed = base / 'fixed.md'
        raw_fixed = put(fixed, HEADER + '\n\n' + record('修复后记录'))
        report = json.loads(run('replace', '--scope', 'project', '--from-file', str(fixed),
                                '--expect', version_of(raw_over), *overlay()).stdout)
        assert_lock(report)
        assert report['ok'] and report['characters_before'] == LIMIT + 1 and pp.read_bytes() == raw_fixed
        assert report['near_limit'] is False
        assert '修复后记录' in run('recall', *overlay()).stdout
        report = json.loads(run('promote', '待转正戊', '--scope', 'project', *overlay()).stdout)
        assert report['ok'] and '待转正戊' in pp.read_text(encoding='utf-8')
        assert '待转正戊' not in cp.read_text(encoding='utf-8')
        checks.append('replace 凭版本修复超限文件，之后 recall 与 promote 恢复正常')

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

        # dry-run 不写盘（add / replace / edit / drop）
        put(pp, HEADER + '\n\n' + record('dry基准'))
        before = snapshot()
        report = json.loads(run('add', '--scope', 'project', '--title', 'dry运行丁', *fields,
                                '--dry-run', *overlay()).stdout)
        assert report['dry_run'] and snapshot() == before and 'near_limit' in report
        draft = base / 'dry.md'
        put(draft, HEADER + '\n\n' + record('dry替换'))
        report = json.loads(run('replace', '--scope', 'project', '--from-file', str(draft),
                                '--expect', version_of(pp.read_bytes()), '--dry-run', *overlay()).stdout)
        assert report['dry_run'] and report['characters_after'] == len(draft.read_text(encoding='utf-8'))
        assert snapshot() == before and 'near_limit' in report
        version = version_of(pp.read_bytes())
        report = json.loads(run('edit', 'dry基准', '--scope', 'project', '--keywords', 'dry词',
                                '--expect', version, '--dry-run', *overlay()).stdout)
        assert report['dry_run'] and snapshot() == before
        assert report['near_limit'] == near_limit(report['characters_after'])
        report = json.loads(run('drop', 'dry基准', '--scope', 'project', '--expect', version,
                                '--dry-run', *overlay()).stdout)
        assert report['dry_run'] and report['deleted'] == 1 and snapshot() == before
        assert report['near_limit'] == near_limit(report['characters_after'])
        checks.append('add/replace/edit/drop 的 dry-run 只展示容量与版本结论，不写盘')

        # 并发锁
        namespace = argparse.Namespace(scope='project', title='锁测试辛', when='s', action='a',
                                       keywords='k', from_entry=None, project=str(base),
                                       global_path=str(gp), project_path=str(pp), dry_run=False)
        if LOCK_BACKEND == 'fcntl':
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
        else:
            assert add(namespace)['message'] == 'ADDED'
            checks.append('锁后端 {}：不做同进程 BUSY 断言，写入仍走同目录临时文件 + os.replace'
                          .format(LOCK_BACKEND))

        # 输入值不得含换行：换行可注入额外记录并绕过查重
        put(pp, HEADER + '\n\n' + record('换行基准'))
        rejected(['add', '--scope', 'project', '--title', '注入甲\n### 伪造记录',
                  *fields, *overlay()], '不能含换行')
        assert pp.read_text(encoding='utf-8').count('### ') == 1, '换行注入改动了文件'
        rejected(['add', '--scope', 'project', '--title', '注入乙', '--when', 's',
                  '--action', 'a\n- 适用: p', '--keywords', 'k', *overlay()], '不能含换行')
        rejected(['add', '--scope', 'project', '--title', '注入丙', '--when', 's',
                  '--action', 'a', '--keywords', 'k\n### 伪造', *overlay()], '不能含换行')
        checks.append('标题与三个字段都拒绝换行，一次 add 无法注入第二条记录')

        # Unicode 行分隔符：写入口一律拒；既有文件里已经含有这类字符时，
        # drop/edit 的跨度必须仍覆盖整条记录，不能只删半条留下孤儿行。
        put(pp, HEADER + '\n\n' + record('分隔符基准'))
        rejected(['add', '--scope', 'project', '--title', '分隔符甲', '--when', 's',
                  '--action', 'a\u2028### 伪造', '--keywords', 'k', *overlay()], '行分隔符')
        rejected(['add', '--scope', 'project', '--title', '分隔符乙', '--when', 's',
                  '--action', 'a', '--keywords', 'k\u2029x', *overlay()], '行分隔符')
        rejected(['add', '--scope', 'project', '--title', '分隔符丙', '--when', 's',
                  '--action', 'a\x85b', '--keywords', 'k', *overlay()], '行分隔符')
        checks.append('四个字段都拒绝 U+2028/U+2029/U+0085 等行分隔符')

        put(pp, HEADER + '\n\n' + record('老文件甲')
            + '\n' + record('老文件乙', action='a\u2028### 伪造') + '\n' + record('老文件丙'))
        report = json.loads(run('drop', '老文件乙', '--scope', 'project',
                                '--expect', version_of(pp.read_bytes()), *overlay()).stdout)
        assert report['deleted'] == 1 and report['entries_after'] == 2, report
        after_drop = pp.read_text(encoding='utf-8')
        assert '伪造' not in after_drop and '老文件甲' in after_drop and '老文件丙' in after_drop, after_drop
        out = run('inspect', '--scope', 'project', *overlay()).stdout
        assert 'structure: ok' in out and 'entries: 2' in out, out
        checks.append('既有文件含 U+2028 时 drop 仍删掉整条记录，不留孤儿行')

        put(pp, HEADER + '\n\n' + record('老文件丁') + '\n'
            + record('老文件戊', keywords='k\u2029### 伪造') + '\n' + record('老文件己'))
        report = json.loads(run('edit', '老文件戊', '--scope', 'project', '--action', '改后',
                                '--keywords', '新词',
                                '--expect', version_of(pp.read_bytes()), *overlay()).stdout)
        assert report['message'] == 'EDITED' and report['entries_after'] == 3, report
        after_edit = pp.read_text(encoding='utf-8')
        assert '伪造' not in after_edit and '改后' in after_edit and '老文件己' in after_edit, after_edit
        out = run('inspect', '--scope', 'project', *overlay()).stdout
        assert 'structure: ok' in out, out
        checks.append('既有文件含 U+2029 时 edit 整条重写（连带脏字段），不留下半行残留')

        # 改名不能撞上既有标题：撞了就拒，不制造 edit/drop 无法定位的重名
        put(pp, HEADER + '\n\n' + record('改名甲') + '\n' + record('改名乙'))
        put(base / 'rename.md', record('改名乙'))
        rejected(['edit', '改名甲', '--scope', 'project', '--expect',
                  version_of(pp.read_bytes()), *overlay(),
                  '--from-entry', str(base / 'rename.md')], 'DUPLICATE')
        checks.append('edit 改名撞上既有标题时报 DUPLICATE，未写入')

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

        # 逐条打捞：一条坏记录不再让同文件其余记录失联
        put(pp, HEADER + '\n\n' + record('好记录甲') + '\n' + '### 坏记录乙\n- 适用: s\n随手插一行\n- 做法: a\n- 关键词: k\n'
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
        put(pp, HEADER + '\n\n### 全坏甲\n- 适用: s\n散落行\n- 做法: a\n- 关键词: k\n')
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
        put(pp, HEADER + '\n\n' + record('存活甲') + '\n### 坏一\n- 适用: s\nx\n- 做法: a\n- 关键词: k\n'
            + '\n### 坏二\n- 适用: s\n- 做法: a\n- 关键词: \n' + '\n' + record('存活乙'))
        result = run('recall', *overlay(), code=1)
        assert result.stdout.count('已跳过该条') == 2, result.stdout
        assert '坏一' in result.stdout and '坏二' in result.stdout, result.stdout
        assert '存活甲' in result.stdout and '存活乙' in result.stdout, result.stdout
        checks.append('多条坏记录逐条报出各自标题与原因，不静默合并')

        # 标题不合法（`###` 后缺空格、行首缩进）与散落内容：都不能被静默丢弃
        put(pp, HEADER + '\n\n### \n- 适用: s\n- 做法: a\n- 关键词: k\n\n' + record('正常甲'))
        result = run('recall', *overlay(), code=1)
        assert '正常甲' in result.stdout, result.stdout
        assert '不是 `### 标题`' in result.stdout, result.stdout
        put(pp, HEADER + '\n\n  ### 缩进标题\n- 适用: s\n- 做法: a\n- 关键词: k\n\n' + record('正常乙'))
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
        put(pp, HEADER + '\n\n  ### 缩进标题诊断\n- 适用: s\n- 做法: a\n- 关键词: k\n'
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
        put(pp, crlf(HEADER + '\n\n  ###\n- 适用: s\n- 做法: a\n- 关键词: k\n'))
        result = run('recall', *overlay(), code=1)
        bad = [line for line in result.stdout.split('\n') if '不是 `### 标题`' in line]
        assert bad and '\r' not in bad[0], result.stdout      # 诊断里不能带 CR（终端会被覆盖）
        assert '`  ###`' in bad[0], result.stdout             # 行首缩进必须保留
        assert '行首有缩进' in bad[0] and '`###` 后缺少空格与标题文字' in bad[0], bad[0]
        checks.append('CRLF 文件的水平线同样是边界；CRLF 坏标题诊断不带 CR，缩进与缺标题两个症状独立给出')

        # ⑥ U+3000 缩进标题：前导空白不止 ' '/'\t'，诊断必须照样点明「行首有缩进」
        put(pp, HEADER + '\n\n\u3000### 全角空格缩进标题\n- 适用: s\n- 做法: a\n- 关键词: k\n'
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
        assert report['near_limit'] == near_limit(report['target_characters'])
        checks.append('promote 结果带两份文件的 version，PARTIAL 时调用方无需再跑一次 inspect')

        # --project-path 传目录时，候选落在该目录内而不是它的上一级
        put(pp, HEADER + '\n')
        report = json.loads(run('add', '--scope', 'candidate', '--title', '目录语义辛',
                                *fields, '--project-path', str(pp.parent), *overlay()[2:]).stdout)
        assert Path(report['path']) == cp, report
        assert '目录语义辛' in cp.read_text(encoding='utf-8')
        checks.append('--project-path 传已存在目录时按该目录下的 gotchas.md 处理，候选不再写错位置')

        # add --from-entry：文件 / stdin / 长参数互斥 / 字段错序或缺字段 / 旧格式
        put(pp, HEADER + '\n')
        frag = base / 'entry-add.md'
        put(frag, '\n\n### 片段甲\n- 适用：全角适\n- 做法：全角做\n- 关键词：全角词\n\n')
        report = json.loads(run('add', '--scope', 'project', '--from-entry', str(frag), *overlay()).stdout)
        assert report['message'] == 'ADDED' and 'near_limit' in report
        assert report['item'] == entry_text('片段甲', when='全角适', action='全角做', keywords='全角词')
        report = json.loads(run('add', '--scope', 'project', '--from-entry', '-', *overlay(),
                                input_text='### 片段乙\n- 适用: s2\n- 做法: a2\n- 关键词: k2\n').stdout)
        assert report['message'] == 'ADDED' and '- 适用: s2' in pp.read_text(encoding='utf-8')
        rejected(['add', '--scope', 'project', '--from-entry', str(frag), '--title', '片段甲', *overlay()], 'FORMAT')
        for name, content in (
                ('缺字段', '### 缺字段\n- 适用: s\n- 做法: a\n'),
                ('错序', '### 错序\n- 做法: a\n- 适用: s\n- 关键词: k\n'),
                ('空行', '### 空行\n- 适用: s\n\n- 做法: a\n- 关键词: k\n'),
                ('两条', '### 两条甲\n- 适用: s\n- 做法: a\n- 关键词: k\n'
                         '### 两条乙\n- 适用: s\n- 做法: a\n- 关键词: k\n')):
            path = base / 'frag-{}.md'.format(name)
            put(path, content)
            rejected(['add', '--scope', 'project', '--from-entry', str(path), *overlay()], 'FORMAT')
        legacy_frag = base / 'frag-legacy.md'
        put(legacy_frag, '### 旧片段\n- 适用: s\n- 做法: a\n- 验证: v\n')
        rejected(['add', '--scope', 'project', '--from-entry', str(legacy_frag), *overlay()], 'LEGACY_FORMAT')
        checks.append('add --from-entry 支持文件与 stdin、首尾空行忽略、半/全角冒号兼容；长参数互斥，错序/缺字段/多条/旧格式都拒绝')

        # edit / drop：标题匹配、按版本写入、只替换命中记录、失败不写盘
        put(pp, HEADER + '\n\n' + record('编辑甲', action='旧动作') + '\n\n' + record('编辑乙') + '\n')
        before = pp.read_text(encoding='utf-8')
        version = version_of(pp.read_bytes())
        old = entry_text('编辑甲', action='旧动作')
        new = entry_text('编辑甲', action='旧动作', keywords='新检索词')
        report = json.loads(run('edit', '编辑甲', '--scope', 'project', '--keywords', '新检索词',
                                '--expect', version, *overlay()).stdout)
        assert_lock(report)
        assert report['message'] == 'EDITED' and report['entries_after'] == 2
        assert report['characters_after'] == len(pp.read_text(encoding='utf-8'))
        assert report['near_limit'] == near_limit(report['characters_after'])
        assert pp.read_text(encoding='utf-8') == before.replace(old, new), 'edit 改动了命中记录以外的字节'

        run('add', '--scope', 'project', '--title', 'CaseTitle', *fields, *overlay())
        version = version_of(pp.read_bytes())
        report = json.loads(run('edit', '  casetitle  ', '--scope', 'project', '--keywords', 'caseword',
                                '--expect', version, *overlay()).stdout)
        assert report['title'] == 'CaseTitle' and '- 关键词: caseword' in pp.read_text(encoding='utf-8')

        result = rejected(['edit', '编辑', '--scope', 'project', '--keywords', 'x',
                           '--expect', version_of(pp.read_bytes()), *overlay()], 'NOT_FOUND')
        assert '编辑甲' in result.stderr and '编辑乙' in result.stderr, result.stderr
        rejected(['edit', '编辑甲', '--scope', 'project', '--keywords', 'x',
                  '--expect', '0' * 64, *overlay()], 'STALE_VERSION')
        rejected(['drop', '编辑甲', '--scope', 'project', '--expect', '0' * 64, *overlay()], 'STALE_VERSION')

        before = pp.read_text(encoding='utf-8')
        target = entry_text('编辑乙')
        report = json.loads(run('drop', '编辑乙', '--scope', 'project',
                                '--expect', version_of(pp.read_bytes()), *overlay()).stdout)
        assert_lock(report)
        assert report['message'] == 'DROPPED' and report['deleted'] == 1
        assert report['characters_after'] == len(pp.read_text(encoding='utf-8'))
        assert report['near_limit'] == near_limit(report['characters_after'])
        assert pp.read_text(encoding='utf-8') == before.replace(target, ''), 'drop 改动了目标记录以外的字节'
        assert report['entries_after'] == 2
        rejected(['drop', '编辑', '--scope', 'project',
                  '--expect', version_of(pp.read_bytes()), *overlay()], 'NOT_FOUND')

        # edit --from-entry：文件与 stdin，片段可整条替换（标题也可随片段改）
        before = pp.read_text(encoding='utf-8')
        version = version_of(pp.read_bytes())
        old = entry_text('编辑甲', action='旧动作', keywords='新检索词')
        edit_frag = base / 'edit-frag.md'
        put(edit_frag, '\n\n### 编辑甲\n- 适用：片段适\n- 做法：片段做\n- 关键词：片段词\n\n')
        new = entry_text('编辑甲', when='片段适', action='片段做', keywords='片段词')
        report = json.loads(run('edit', '编辑甲', '--scope', 'project', '--from-entry', str(edit_frag),
                                '--expect', version, *overlay()).stdout)
        assert report['message'] == 'EDITED' and report['title'] == '编辑甲'
        assert pp.read_text(encoding='utf-8') == before.replace(old, new)

        before = pp.read_text(encoding='utf-8')
        version = version_of(pp.read_bytes())
        old = entry_text('编辑甲', when='片段适', action='片段做', keywords='片段词')
        new = entry_text('编辑甲', when='stdin适', action='stdin做', keywords='stdin词')
        report = json.loads(run('edit', '编辑甲', '--scope', 'project', '--from-entry', '-',
                                '--expect', version, *overlay(),
                                input_text='### 编辑甲\n- 适用: stdin适\n- 做法: stdin做\n- 关键词: stdin词\n').stdout)
        assert report['message'] == 'EDITED'
        assert pp.read_text(encoding='utf-8') == before.replace(old, new)

        mismatch = base / 'edit-mismatch.md'
        put(mismatch, '### 改名后\n- 适用: s\n- 做法: a\n- 关键词: k\n')
        before = pp.read_text(encoding='utf-8')
        old = entry_text('编辑甲', when='stdin适', action='stdin做', keywords='stdin词')
        new = entry_text('改名后')
        report = json.loads(run('edit', '编辑甲', '--scope', 'project', '--from-entry', str(mismatch),
                                '--expect', version_of(pp.read_bytes()), *overlay()).stdout)
        assert report['message'] == 'EDITED' and report['title'] == '改名后'
        assert report['previous_title'] == '编辑甲', report
        assert pp.read_text(encoding='utf-8') == before.replace(old, new)
        rejected(['edit', '编辑甲', '--scope', 'project', '--from-entry', str(mismatch),
                  '--when', 'x', '--expect', version_of(pp.read_bytes()), *overlay()], 'FORMAT')
        checks.append('edit 按标题忽略大小写与首尾空白精确匹配；支持逐字段与 --from-entry（文件/stdin）；'
                      'STALE_VERSION/NOT_FOUND 不写盘；只替换命中记录，其余字节不变；drop 同理')

        # near_limit：85% 整数边界（3400 真 / 3399 假），所有写入口都输出
        assert near_limit(3400) is True and near_limit(3399) is False
        item = entry_text('近界甲')
        put(pp, revision(3400 - len(item) - 1, title='填充甲'))
        report = json.loads(run('add', '--scope', 'project', '--title', '近界甲', *fields, *overlay()).stdout)
        assert report['characters_after'] == 3400 and report['near_limit'] is True, report
        item = entry_text('近界乙')
        put(pp, revision(3399 - len(item) - 1, title='填充乙'))
        report = json.loads(run('add', '--scope', 'project', '--title', '近界乙', *fields, *overlay()).stdout)
        assert report['characters_after'] == 3399 and report['near_limit'] is False, report
        near3400 = base / 'near3400.md'
        put(near3400, revision(3400, title='替换近界甲'))
        report = json.loads(run('replace', '--scope', 'project', '--from-file', str(near3400),
                                '--expect', version_of(pp.read_bytes()), *overlay()).stdout)
        assert report['characters_after'] == 3400 and report['near_limit'] is True
        near3399 = base / 'near3399.md'
        put(near3399, revision(3399, title='替换近界乙'))
        report = json.loads(run('replace', '--scope', 'project', '--from-file', str(near3399),
                                '--expect', version_of(pp.read_bytes()), *overlay()).stdout)
        assert report['characters_after'] == 3399 and report['near_limit'] is False
        checks.append('near_limit 用 characters_after 判定：3400（85%）为真、3399 为假；add/promote/edit/drop/replace 都输出该布尔值')

        # 锁后端字段：无 fcntl/msvcrt 时降级为 none，仍能原子写入
        assert LOCK_BACKEND in ('fcntl', 'msvcrt', 'none')
        stub_wrapper = base / 'run_without_lock_modules.py'
        put(stub_wrapper, (
            'import runpy, sys\n'
            'target = sys.argv[1]\n'
            "sys.modules['fcntl'] = None\n"
            "sys.modules['msvcrt'] = None\n"
            'sys.argv = [target] + sys.argv[2:]\n'
            "runpy.run_path(target, run_name='__main__')\n"))
        stub_project = base / 'nolock' / '.agents' / 'gotchas.md'
        stub_global = base / 'nolock-global.md'
        result = subprocess.run([sys.executable, '-B', str(stub_wrapper), script,
                                 'add', '--scope', 'project', '--title', '无锁桩',
                                 '--when', 's', '--action', 'a', '--keywords', 'k',
                                 '--project-path', str(stub_project),
                                 '--global-path', str(stub_global)],
                                capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, (result.stdout, result.stderr)
        report = json.loads(result.stdout)
        assert report['lock'] == 'none' and 'lock_note' in report, report
        assert '未加锁' in report['lock_note'] and '原子替换' in report['lock_note'], report
        assert stub_project.exists() and '无锁桩' in stub_project.read_text(encoding='utf-8')
        checks.append('无 fcntl/msvcrt 桩导入不崩：写命令 lock 为 none 并给出降级说明，仍原子写入')

        # GOTCHA_HOME：绝对路径重定向；空串/相对路径回退默认并说明
        custom_home = base / 'ghome-custom'
        custom_home.mkdir()
        fake_home = base / 'fake-home'
        fake_home.mkdir()
        env = os.environ.copy()
        env.update({'GOTCHA_HOME': str(custom_home), 'HOME': str(fake_home),
                    'USERPROFILE': str(fake_home)})
        report = json.loads(run('add', '--scope', 'global', '--title', 'GOTCHA家',
                                '--when', 's', '--action', 'a', '--keywords', 'k',
                                '--project-path', str(pp), env=env).stdout)
        assert Path(report['path']) == custom_home / 'gotchas.md', report
        assert report['global_home'] == str(custom_home) and report['global_home_source'] == 'env', report
        assert (custom_home / 'gotchas.md').exists()
        assert_lock(report)
        env['GOTCHA_HOME'] = 'relative/path'
        out = run('inspect', '--scope', 'global', '--project-path', str(pp), env=env).stdout
        assert 'path: {}'.format(fake_home / '.agents' / 'gotchas.md') in out, out
        assert 'global_home_source: default' in out and 'global_home_note:' in out, out
        assert '不是绝对路径' in out and '回退默认' in out, out
        env['GOTCHA_HOME'] = ''
        out = run('inspect', '--scope', 'global', '--project-path', str(pp), env=env).stdout
        assert '空字符串' in out and '回退默认' in out, out
        checks.append('GOTCHA_HOME 绝对路径重定向生效；空串/相对路径回退默认 ~/.agents 并说明')

        # 项目根向上探测：最近 .agents/gotchas.md > 最近 .git（文件/目录）> cwd
        import shutil
        detect_base = Path(tempfile.mkdtemp(prefix='capture-gotcha-detect-')).resolve()
        try:
            agents_root = detect_base / 'agents-root'
            (agents_root / '.agents').mkdir(parents=True)
            put(agents_root / '.agents' / 'gotchas.md', HEADER + '\n\n' + record('祖先记忆'))
            deep_agents = agents_root / 'sub' / 'deep'
            deep_agents.mkdir(parents=True)
            out = run('inspect', '--scope', 'project', '--global-path', str(gp),
                      cwd=str(deep_agents)).stdout
            assert 'project_root: {}'.format(agents_root) in out, out
            assert 'source: nearest' in out, out
            assert 'path: {}'.format(agents_root / '.agents' / 'gotchas.md') in out, out
            assert '祖先记忆' in out, out

            git_root = detect_base / 'git-root'
            git_root.mkdir()
            (git_root / '.git').write_text('gitdir: fake\n', encoding='utf-8')
            deep_git = git_root / 'sub' / 'deep'
            deep_git.mkdir(parents=True)
            out = run('inspect', '--scope', 'project', '--global-path', str(gp),
                      cwd=str(deep_git)).stdout
            assert 'project_root: {}'.format(git_root) in out, out
            assert 'source: git' in out, out
            assert 'path: {}'.format(git_root / '.agents' / 'gotchas.md') in out, out

            cwd_root = detect_base / 'cwd-root' / 'sub' / 'deep'
            cwd_root.mkdir(parents=True)
            out = run('inspect', '--scope', 'project', '--global-path', str(gp),
                      cwd=str(cwd_root)).stdout
            assert 'project_root: {}'.format(cwd_root) in out, out
            assert 'source: cwd' in out, out
            assert 'path: {}'.format(cwd_root / '.agents' / 'gotchas.md') in out, out

            override = detect_base / 'override' / '.agents' / 'gotchas.md'
            (detect_base / 'override' / '.agents').mkdir(parents=True)
            put(override, HEADER + '\n')
            out = run('inspect', '--scope', 'project', '--project-path', str(override),
                      '--global-path', str(gp), cwd=str(deep_agents)).stdout
            assert 'path: {}'.format(override) in out, out

            # 全局记忆不能被当成项目记忆：项目在 $HOME 下时，
            # ~/.agents/gotchas.md 可被「最近祖先 .agents」命中，两份就变成同一份。
            home_like = detect_base / 'home-like'
            (home_like / '.agents').mkdir(parents=True)
            put(home_like / '.agents' / 'gotchas.md', HEADER + '\n\n' + record('全局那份'))
            project_in_home = home_like / 'work' / 'proj'
            (project_in_home / '.git').mkdir(parents=True)
            out = run('inspect', '--scope', 'project',
                      '--global-path', str(home_like / '.agents' / 'gotchas.md'),
                      cwd=str(project_in_home)).stdout
            assert 'project_root: {}'.format(project_in_home) in out, out
            assert 'source: git' in out, out
            assert 'path: {}'.format(project_in_home / '.agents' / 'gotchas.md') in out, out
            checks.append('向上探测跳过全局记忆文件自身：项目在 $HOME 下时不会与全局变成同一份')
        finally:
            shutil.rmtree(str(detect_base), ignore_errors=True)
        checks.append('项目根按最近 .agents/gotchas.md > 最近 .git（文件）> cwd 探测；'
                      'inspect 给出 source，--project-path 覆盖优先')

        assert not list(base.rglob('.gotcha-*')), '临时文件残留'
        if LOCK_BACKEND != 'none':
            assert list(base.rglob(LOCK_NAME)), '锁文件应当持续存在'
        checks.append('写入用同目录临时文件原子替换，无 .gotcha-* 残留；'
                      '锁文件按 {} 后端语义保留'.format(LOCK_BACKEND))

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
        sub.add_argument('--project', help='向上探测项目根的起点，默认 cwd（找 .agents/gotchas.md 或 .git）')
        sub.add_argument('--project-path', help='显式覆盖项目记忆文件路径，优先于向上探测')
        sub.add_argument('--global-path', help='显式覆盖全局记忆文件路径，优先于 GOTCHA_HOME')
        return sub

    writer = with_paths(commands.add_parser('add', help='追加一条记录（新格式：适用/做法/关键词）'))
    writer.add_argument('--scope', choices=list(SCOPES), required=True)
    writer.add_argument('--title', help='可迁移的行动规则名，不是某次事故名')
    writer.add_argument('--when', metavar='适用', help='触发条件与适用边界（与 --action 一起必填）')
    writer.add_argument('--action', metavar='做法', help='可执行动作；根因只在影响动作时补一句（与 --when 一起必填）')
    writer.add_argument('--keywords', metavar='关键词', help='检索词；省略时用标题')
    writer.add_argument('--from-entry', dest='from_entry', metavar='路径|-',
                        help='从 markdown 片段读取一条记录，- 表示 stdin；不能与长参数混用')
    for name in LEGACY_FIELDS + ('verified',):  # 旧字段参数：显式拒绝并指导迁移
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

    editor = with_paths(commands.add_parser('edit', help='按标题单条修改（只替换命中的那一条）'))
    editor.add_argument('title')
    editor.add_argument('--scope', choices=list(SCOPES), required=True)
    editor.add_argument('--from-entry', dest='from_entry', metavar='路径|-',
                        help='用一条完整的新记录替换，- 表示 stdin')
    editor.add_argument('--when', metavar='适用', help='新适用值；至少给一个字段参数')
    editor.add_argument('--action', metavar='做法', help='新做法值；至少给一个字段参数')
    editor.add_argument('--keywords', metavar='关键词', help='新检索词；至少给一个字段参数')
    editor.add_argument('--expect', required=True, help='inspect 返回的 version')
    editor.add_argument('--dry-run', action='store_true')

    remover = with_paths(commands.add_parser('drop', help='按标题删除单条记录'))
    remover.add_argument('title')
    remover.add_argument('--scope', choices=list(SCOPES), required=True)
    remover.add_argument('--expect', required=True, help='inspect 返回的 version')
    remover.add_argument('--dry-run', action='store_true')

    replacer = with_paths(commands.add_parser('replace', help='按版本整份提交修订稿（修改/合并/清空）'))
    replacer.add_argument('--scope', choices=list(SCOPES), required=True)
    replacer.add_argument('--from-file', dest='from_file', required=True, help='UTF-8 修订稿')
    replacer.add_argument('--expect', required=True, help='inspect 返回的 version')
    replacer.add_argument('--dry-run', action='store_true')

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
        report = {'add': add, 'promote': promote, 'edit': edit,
                  'drop': drop, 'replace': replace}[args.cmd](args)
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except (StoreError, OSError, UnicodeError) as exc:
        print('ERROR: {}'.format(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
