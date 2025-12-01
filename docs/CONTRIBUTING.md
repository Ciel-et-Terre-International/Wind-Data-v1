# CONTRIBUTING – Ciel & Terre International – Wind Data v1

[← Back to README](../README.md)

**File:** <FILENAME>  
**Version:** v1.x  
**Last updated:** <DATE>  
**Maintainer:** Adrien Salicis  
**Related docs:** See docs/INDEX.md for full documentation index.

---


Thank you for contributing to the Wind Data project.
This document describes how to contribute safely and efficiently within the
Ciel & Terre International development workflow.

------------------------------------------------------------
1. Requirements
------------------------------------------------------------

Before contributing, ensure you have:

- Python 3.10+  
- Conda (Miniconda or Anaconda)  
- A working environment created via `environment.yml`  
- Git installed and configured with your username and email  
- Access to the organization repository:
  https://github.com/Ciel-et-Terre-International/Wind-Data-v1

Check your git setup:

git config --global user.name
git config --global user.email

------------------------------------------------------------
2. Branching Model (Git Workflow)
------------------------------------------------------------

The project follows a simplified and robust Git workflow:

MAIN BRANCHES:
- `main` → stable production-ready code  
- `dev` → integration of ongoing developments (optional if needed)

FEATURE WORK:
- Every new task **must** be implemented in a dedicated branch:
  feature/<short-description>
  fix/<description>
  refactor/<description>
  docs/<description>

EXAMPLES:
feature/add-wind-rose
fix/noaa-parser
refactor/stats-engine
docs/update-readme

RULES:
- Never work directly on `main`
- Keep feature branches small and scoped
- Commit frequently with clear messages
- Open a Pull Request (PR) when ready

------------------------------------------------------------
3. Commit Message Convention
------------------------------------------------------------

Write clean and structured commits:

FORMAT:
<type>: <short description>

TYPES:
- feat: new functionality  
- fix: bug correction  
- refactor: internal code change  
- docs: documentation  
- test: adding or fixing tests  
- chore: maintenance tasks  
- perf: performance improvements

EXAMPLES:
feat: add Gumbel 50-year return period calculation
fix: correct wind direction interpolation error
docs: update DATAS.md with Open-Meteo info
refactor: simplify NOAA ISD parser

------------------------------------------------------------
4. Pull Requests (PRs)
------------------------------------------------------------

When a feature or fix is ready:

- Push your branch:
  git push -u origin <branchName>
- Create a Pull Request on GitHub
- Describe clearly:
  * What was added or fixed  
  * How it was tested  
  * Any side-effect or API change  
- Request review from another team member if possible

PR RULES:
- One feature = one PR  
- Large PRs must be split  
- Tests must pass  
- No auto-merge into main without review

------------------------------------------------------------
5. Code Style and Best Practices
------------------------------------------------------------

- Follow PEP8
- Use descriptive variable names
- Small, pure functions when possible
- Prefer explicit code over clever code
- Add docstrings for all public functions
- Use logging instead of print() in new modules
- Avoid hardcoding configuration → use constants or config files

------------------------------------------------------------
6. Tests
------------------------------------------------------------

The `tests/` folder contains PyTest-based tests.

To run tests:

pytest

New features must be covered by at least a minimal test.
Critical bugs must have a regression test.

------------------------------------------------------------
7. Documentation
------------------------------------------------------------

Every new module or non-trivial function should be documented.

Documentation lives in:
docs/

Before finalizing a PR:
- Update README.md if needed
- Update relevant documentation pages
- Add technical notes when you change APIs or data structures

------------------------------------------------------------
8. Release Process
------------------------------------------------------------

Releases follow semantic versioning (MAJOR.MINOR.PATCH):

MAJOR: breaking changes  
MINOR: new features  
PATCH: fixes

Steps for a release:
1. Ensure main is stable  
2. Update CHANGELOG.md  
3. Tag release:
   git tag vX.Y.Z
   git push --tags  
4. Attach release notes on GitHub

------------------------------------------------------------
9. Code Ownership and Responsibilities
------------------------------------------------------------

- modules/*: data acquisition & normalization  
- analysis_runner: pipeline coordination  
- report_generator: reporting  
- scripts/: utilities & maintenance  
- docs/: documentation & methodology  

------------------------------------------------------------
10. Contact
------------------------------------------------------------

For major changes, discuss with:
adrien.salicis@cieletterre.net
