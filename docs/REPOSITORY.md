# Repository layout

**split-stack and Local Recruiting Ops are two different projects.** They share an author and may live as sibling folders on disk. They are not the same GitHub repository and should not be marketed as one product.

## Typical layout (example)

```text
~/dev/projects/
├── local-recruiting-ops/   ← job intelligence app (separate repo)
│   └── .git → github.com/edwardjbaumel/local-recruiting-ops
│
└── split-stack/            ← this routing library
    ├── src/split_stack/
    ├── examples/
    └── .git → github.com/edwardjbaumel/split-stack
```

| | **Local Recruiting Ops** | **split-stack** |
| --- | --- | --- |
| **What it is** | Job pipeline, matches, dashboard | Python routing library for agent loops |
| **Primary user** | Job seeker running a local dashboard | Developer embedding `route()` in a runner |
| **GitHub** | `edwardjbaumel/local-recruiting-ops` | `edwardjbaumel/split-stack` |

Sibling folders on disk does **not** mean one repository.

## Marketing rule

- **split-stack README** leads with the routing library. Local Recruiting Ops appears only in the related-projects footer.
- **Local Recruiting Ops README** describes the job app only. split-stack appears only in the related-projects footer.
- Do not describe split-stack as a Cursor plugin, chat app, or “job tool.”
- Do not describe Local Recruiting Ops as using or requiring split-stack unless you actually integrate them in code.

## Clone and push (split-stack only)

```bash
git clone https://github.com/edwardjbaumel/split-stack.git
cd split-stack
pip install -e ".[dev]"
pytest
```

Do **not** push split-stack to `local-recruiting-ops` (or any other project repo).

## Verify you are in the right repo

```bash
git rev-parse --show-toplevel   # directory name should be split-stack
git remote -v                   # origin → split-stack.git only
```

## Cross-links only

Link between README footers when helpful. Never merge codebases or imply a monorepo product story.

See also: [`SECURITY.md`](SECURITY.md) — what must not be committed.
