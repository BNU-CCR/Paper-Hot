# Workspace Structure Review

Date: 2026-06-30

This review records the current workspace organization after moving from a flat engineering layout to a product-function layout.

## PM Assessment

The previous root folder was technically workable but hard to read. It mixed backend workflow code, website files, public JSON, runtime data, configuration, tests, Feishu artifacts, secrets, and Python build outputs at the same level.

The current structure uses one first-level directory per responsibility:

| Area | Path | Responsibility |
| --- | --- | --- |
| Backend workflow | `backend/` | Paper fetching, screening, storage, config, tests, and backend scripts. |
| Frontend website | `frontend/` | Static website UI and public JSON consumed by the website. |
| Project docs | `docs/` | Current roadmap, project map, workspace review, and archived historical plans. |
| Local-only state | `.local/` | Secrets, Feishu QR codes, tool locks, and generated build artifacts. |
| Repo entrance | root files | README, package metadata, agent notes, and Git ignore rules. |

## Current Target Structure

```text
.
├── README.md
├── CLAUDE.md
├── pyproject.toml
├── backend/
│   ├── journal_tracker/       # Python package and CLI workflow
│   ├── config/                # journals, prompts, settings
│   ├── data/                  # local database and generated reports, ignored
│   ├── scripts/               # backend helper scripts
│   └── tests/                 # backend unit tests
├── frontend/
│   ├── web/                   # static website HTML/CSS/JS
│   └── public/data/           # website JSON snapshots
├── docs/
│   ├── project-map.md
│   ├── roadmap.md
│   ├── workspace-structure-review.md
│   └── archive/
└── .local/                    # local-only secrets and tool artifacts, ignored
```

## Changes Made In This Cleanup

- Moved Python workflow package from `src/` to `backend/journal_tracker/`.
- Moved backend tests from `tests/` to `backend/tests/`.
- Moved backend configuration from `config/` to `backend/config/`.
- Moved local database state from `data/` to `backend/data/`.
- Moved helper scripts from `scripts/` to `backend/scripts/`.
- Moved website files from `web/` to `frontend/web/`.
- Moved public website data from `public/data/` to `frontend/public/data/`.
- Moved local API keys from `key.env` to `.local/key.env`.
- Moved Python build output into `.local/build-artifacts/`.
- Updated package metadata, config loading, commands, tests, and docs for the new paths.

## Root Folder Rule

The root folder should stay short and readable. It should only contain:

- Project entrance files: `README.md`, `CLAUDE.md`
- Build/package metadata: `pyproject.toml`
- Git/project controls: `.gitignore`
- First-level responsibility folders: `backend/`, `frontend/`, `docs/`
- Ignored local/tool folders: `.local/`, `.agents/`, `.claude/`, `.codex/`

Do not add new root-level TODO files, screenshots, QR codes, exports, or one-off notes. Put them under `docs/`, `.local/`, `backend/`, or `frontend/` based on responsibility.

## Documentation Rule Going Forward

There should be only one active document for each management purpose:

| Purpose | File |
| --- | --- |
| Project entrance and current state | `README.md` |
| File/folder responsibilities | `docs/project-map.md` |
| Active TODO and phases | `docs/roadmap.md` |
| Workspace cleanup rationale | `docs/workspace-structure-review.md` |
| Historical plans/specs | `docs/archive/` |

New planning notes should update `docs/roadmap.md` instead of creating another root-level TODO file.
