# Cross-Agent Skill Symlinking Quick Reference

## Path Map

```
~/.agents/skills/<name>/       ← 真实文件（全局共享）
     ↑ symlink                    ↑ symlink            ↑ symlink
.claude/skills/<name>        .codex/skills/<name>   .hermes/skills/<name>
```

All symlinks: `../../.agents/skills/<name>` (relative from each agent's skills dir)

## After `npx skills add <repo> -g -y`

```bash
cd ~

for skill in browser-use cloud open-source remote-browser x402; do
  # Codex: always needs manual
  [ ! -e ".codex/skills/$skill" ] && \
    ln -s "../../.agents/skills/$skill" ".codex/skills/$skill"

  # Hermes: check native conflict first
  if [ ! -e ".hermes/skills/$skill" ] && \
     [ -z "$(ls -d .hermes/skills/*/$skill 2>/dev/null)" ]; then
    ln -s "../../.agents/skills/$skill" ".hermes/skills/$skill"
  fi
done
```

## Bulk: symlink everything from shared to Codex

```bash
cd .codex/skills
for d in ../../.agents/skills/*/; do
  name=$(basename "$d")
  [ ! -e "$name" ] && ln -s "../../.agents/skills/$name" "$name"
done
```

## Hermes native conflict check

```bash
# If this returns anything, Hermes already has native version → skip symlink
ls -d ~/.hermes/skills/*/<skill-name> 2>/dev/null
```

## git clone failed? Use GitHub API fallback

```bash
# Download repo as zip
curl -sL -o /tmp/skill.zip \
  "https://api.github.com/repos/<owner>/<repo>/zipball/main"

# List structure
unzip -l /tmp/skill.zip | head -20

# Extract skill files
python3 -c "
import zipfile, os
with zipfile.ZipFile('/tmp/skill.zip', 'r') as z:
    for name in z.namelist():
        if name.startswith('<repo-prefix>/.claude/skills/<skill>/') or \
           name.startswith('<repo-prefix>/src/'):
            z.extract(name, '/tmp/extracted')
"
```
