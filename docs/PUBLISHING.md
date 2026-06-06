# Publishing local-llm-router to PyPI

Checklist to ship `pip install local-llm-router` so other local LLM apps can depend on it.

Repo: [github.com/edwardjbaumel/local-llm-router](https://github.com/edwardjbaumel/local-llm-router)

---

## Before you publish

- [ ] **Tests green:** `pip install -e ".[dev]" && pytest`
- [ ] **Version bumped** in `pyproject.toml` (semver: `0.2.0` → `0.2.1` for fixes, `0.3.0` for features)
- [ ] **README** opens with the 5-line `configure` + `route` example
- [ ] **`docs/FOR_APP_AUTHORS.md`** linked from README (app author entry point)
- [ ] **Git tag** matches version: `git tag v0.2.0`
- [ ] **GitHub repo public** and `main` pushed

---

## Easiest upload (Windows PowerShell)

No env-var quoting — script prompts for token:

```powershell
cd C:\Users\zonka\dev\projects\local-llm-router
.\scripts\upload-pypi.ps1 -TestPyPI    # token from test.pypi.org
.\scripts\upload-pypi.ps1              # token from pypi.org
```

## Manual env vars (quotes required)

PowerShell **must** use double quotes around values:

```powershell
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = "pypi-paste-full-token-here"
```

**Wrong** — these fail silently or run `pypi-...` as a command:

```powershell
$env:TWINE_USERNAME = __token__
$env:TWINE_PASSWORD = pypi-Ag...
username = __token__    # this is .pypirc file syntax, NOT PowerShell
```

## One-time PyPI setup

1. Create accounts:
   - [pypi.org](https://pypi.org/account/register/)
   - [test.pypi.org](https://test.pypi.org/account/register/) (dry run)

2. Install build tools:

```bash
pip install build twine
```

3. **API token** (recommended over password):
   - PyPI → Account settings → API tokens → scope to project `local-llm-router`
   - Save token; use `__token__` as username when uploading

4. Optional: `~/.pypirc` or env vars for twine (**never commit** real tokens):

```ini
[pypi]
username = __token__
password = pypi-...   # placeholder — use env vars instead
```

---

## Dry run (TestPyPI)

From repo root:

```bash
python -m build
twine upload --repository testpypi dist/*
```

Install from TestPyPI in a fresh venv:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ local-llm-router
python -c "import local_llm_router; print(local_llm_router.__version__ if hasattr(local_llm_router,'__version__') else 'ok')"
stack route --prompt "what is JWT?" --hint lookup --json --models gemma4:e4b,qwen3:8b,qwen3:14b
```

Fix any packaging errors before real PyPI.

---

## Publish to PyPI (production)

```bash
# clean old artifacts
rm -rf dist/ build/ *.egg-info   # Linux/macOS
# Remove-Item -Recurse dist, build, *.egg-info  # PowerShell

python -m build
twine check dist/*
twine upload dist/*
```

Verify:

```bash
pip install local-llm-router
pip show local-llm-router
```

---

## After publish

- [ ] GitHub **Release** for tag `v0.2.0` with notes (agent runner, compare POC, `configure`/`route` API)
- [ ] README install block says `pip install local-llm-router` first, `pip install -e .` for contributors
- [ ] PyPI project description links to `FOR_APP_AUTHORS.md` on GitHub
- [ ] Optional: add topics on GitHub (`ollama`, `llm`, `local-first`, `agents`, `routing`)

---

## How other apps discover it

Publishing alone is not marketing. Point authors to:

| Channel | Action |
| --- | --- |
| **PyPI** | `pip install local-llm-router` |
| **GitHub README** | Hero example + link to [`FOR_APP_AUTHORS.md`](FOR_APP_AUTHORS.md) |
| **Your POC demos** | Agent runner + compare — “why routing beats one model” |
| **Integrations doc** | LiteLLM, CLI JSON for non-Python |
| **Related projects** | Footer link from Local Recruiting Ops / your local LLM POC when you add mixed-step chat |

Other local LLM apps do **not** auto-import libraries. Authors add a dependency and three lines of code — or call `stack route --json` from any language.

---

## Version bump cheat sheet

| Change | Bump |
| --- | --- |
| Bug fix, docs only | `0.2.0` → `0.2.1` |
| New API, preset, CLI flag | `0.2.x` → `0.3.0` |
| Breaking API rename | `0.x` → `1.0.0` |

After bump: commit, tag `vX.Y.Z`, push, build, upload.

---

## Optional: add `__version__` to package

Readers often expect `local_llm_router.__version__`. Add to `src/local_llm_router/__init__.py`:

```python
__version__ = "0.2.0"
```

Keep in sync with `pyproject.toml` (or read from importlib.metadata at runtime).

---

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `twine upload` 403 | Token scope or wrong username (`__token__`) |
| Package name taken | PyPI name `local-llm-router` — verify availability before first upload |
| `stack` command missing after install | `[project.scripts]` in `pyproject.toml` — reinstall |
| Old version cached | `pip install --upgrade local-llm-router` |
