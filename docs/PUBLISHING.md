# Publishing split-stack to PyPI

Checklist to ship `pip install split-stack` so other local LLM apps can depend on it.

Repo: [github.com/edwardjbaumel/split-stack](https://github.com/edwardjbaumel/split-stack)

---

## Before you publish

- [ ] **Tests green:** `pip install -e ".[dev]" && pytest`
- [ ] **Version bumped** in `pyproject.toml` (semver: `0.2.0` → `0.2.1` for fixes, `0.3.0` for features)
- [ ] **README** opens with the 5-line `configure` + `route` example
- [ ] **`docs/FOR_APP_AUTHORS.md`** linked from README (app author entry point)
- [ ] **Git tag** matches version: `git tag v0.2.0`
- [ ] **GitHub repo public** and `main` pushed

---

## One-time PyPI setup

1. Create accounts:
   - [pypi.org](https://pypi.org/account/register/)
   - [test.pypi.org](https://test.pypi.org/account/register/) (dry run)

2. Install build tools:

```bash
pip install build twine
```

3. **API token** (recommended over password):
   - PyPI → Account settings → API tokens → scope to project `split-stack`
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
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ split-stack
python -c "import split_stack; print(split_stack.__version__ if hasattr(split_stack,'__version__') else 'ok')"
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
pip install split-stack
pip show split-stack
```

---

## After publish

- [ ] GitHub **Release** for tag `v0.2.0` with notes (agent runner, compare POC, `configure`/`route` API)
- [ ] README install block says `pip install split-stack` first, `pip install -e .` for contributors
- [ ] PyPI project description links to `FOR_APP_AUTHORS.md` on GitHub
- [ ] Optional: add topics on GitHub (`ollama`, `llm`, `local-first`, `agents`, `routing`)

---

## How other apps discover it

Publishing alone is not marketing. Point authors to:

| Channel | Action |
| --- | --- |
| **PyPI** | `pip install split-stack` |
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

Readers often expect `split_stack.__version__`. Add to `src/split_stack/__init__.py`:

```python
__version__ = "0.2.0"
```

Keep in sync with `pyproject.toml` (or read from importlib.metadata at runtime).

---

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `twine upload` 403 | Token scope or wrong username (`__token__`) |
| Package name taken | PyPI name `split-stack` — verify availability before first upload |
| `stack` command missing after install | `[project.scripts]` in `pyproject.toml` — reinstall |
| Old version cached | `pip install --upgrade split-stack` |
