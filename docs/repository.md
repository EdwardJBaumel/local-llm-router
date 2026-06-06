# Repository layout

**local-llm-router and Local Recruiting Ops are two different projects.** They share an author and may live as sibling folders on disk. They are not the same GitHub repository and should not be marketed as one product.

## Typical layout (example)

```text
~/dev/projects/
├── local-recruiting-ops/   ← job intelligence app (separate repo)
│   └── .git → github.com/edwardjbaumel/local-recruiting-ops
│
└── local-llm-router/            ← this routing library
    ├── src/local_llm_router/
    ├── examples/
    └── .git → github.com/edwardjbaumel/local-llm-router
```

| | **Local Recruiting Ops** | **local-llm-router** |
| --- | --- | --- |
| **What it is** | Job pipeline, matches, dashboard | Python routing library for agent loops |
| **Primary user** | Job seeker running a local dashboard | Developer embedding `route()` in a runner |
| **GitHub** | `edwardjbaumel/local-recruiting-ops` | `edwardjbaumel/local-llm-router` |

Sibling folders on disk does **not** mean one repository.

## Marketing rule

- **local-llm-router README** leads with the routing library. Local Recruiting Ops appears only in the related-projects footer.
- **Local Recruiting Ops README** describes the job app only. local-llm-router appears only in the related-projects footer.
- Do not describe local-llm-router as a Cursor plugin, chat app, or “job tool.”
- Do not describe Local Recruiting Ops as using or requiring local-llm-router unless you actually integrate them in code.

## Clone and push (local-llm-router only)

```bash
git clone https://github.com/edwardjbaumel/local-llm-router.git
cd local-llm-router
pip install -e ".[dev]"
pytest
```

Do **not** push local-llm-router to `local-recruiting-ops` (or any other project repo).

## Verify you are in the right repo

```bash
git rev-parse --show-toplevel   # directory name should be local-llm-router
git remote -v                   # origin → local-llm-router.git only
```

## Cross-links only

Link between README footers when helpful. Never merge codebases or imply a monorepo product story.

See also: [`security.md`](security.md) — what must not be committed.
