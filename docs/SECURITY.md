# Security and privacy (contributors)

What **must not** go on GitHub in this repo.

## Never commit

| Item | Why |
| --- | --- |
| **PyPI / GitHub API tokens** | Full account access if leaked |
| **`.pypirc`** with real passwords | Same |
| **`.env`** files | Often hold keys |
| **`split-stack.models.json`** at repo root | Local machine config (use `config/models.example.json` instead) |
| **`OLLAMA_STACK.md`** | Personal paths and install notes — keep local only (gitignored) |
| **`dist/`**, **`build/`** | Build artifacts, not source |

## Safe to commit (public by design)

| Item | Notes |
| --- | --- |
| **`edwardjbaumel` GitHub URLs** | Public repo links |
| **Author name in `pyproject.toml`** | Standard OSS attribution |
| **Example paths like `~/.ollama/models`** | Generic placeholders |
| **`examples/quickstart/split-stack.models.json`** | Generic template, no secrets |

## Before every push

```bash
# Personal Windows username in tracked files?
rg -n "zonka|C:\\\\Users\\\\[^/]+\\\\dev" . --glob "!dist" --glob "!.git"

# Accidental secrets?
rg -n "pypi-Ag[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{10,}" .

# Local config not ignored?
git check-ignore -v split-stack.models.json OLLAMA_STACK.md dist
```

All sensitive local files should show as ignored.

## If something leaked in an old commit

1. Rotate the token (PyPI, GitHub) immediately.
2. Remove from history before the repo is public: [BFG Repo-Cleaner](https://rsc.io/bfg) or `git filter-repo`.
3. Force-push only if you understand collaborators must re-clone.

## Reporting

Open a GitHub Security advisory on [split-stack](https://github.com/edwardjbaumel/split-stack/security) for vulnerabilities in the library itself.
