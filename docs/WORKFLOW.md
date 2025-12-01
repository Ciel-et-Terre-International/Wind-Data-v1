# WORKFLOW – Git Workflow for Wind Data (Ciel & Terre International)

[← Back to README](../README.md)

**File:** <FILENAME>  
**Version:** v1.x  
**Last updated:** <DATE>  
**Maintainer:** Adrien Salicis  
**Related docs:** See docs/INDEX.md for full documentation index.

---

This document summarizes the Git workflow used for Wind Data v1.

------------------------------------------------------------
1. Branch Structure
------------------------------------------------------------

main      → stable code used internally  
dev       → optional integration branch for parallel features  
feature/* → new features  
fix/*     → bug fixes  
refactor/* → code structure improvements  
docs/*    → documentation updates

Never commit directly to main.
Always work on a dedicated branch.

------------------------------------------------------------
2. Typical Workflow
------------------------------------------------------------

1. Update local repo:
   git checkout main
   git pull

2. Create a feature branch:
   git checkout -b feature/my-new-function

3. Implement and commit:
   git add .
   git commit -m "feat: add my new function"

4. Push the branch:
   git push -u origin feature/my-new-function

5. Open a Pull Request on GitHub

6. After review, merge into main

7. Update local main again:
   git checkout main
   git pull

------------------------------------------------------------
3. Commit Messages
------------------------------------------------------------

Use conventional commits:

feat: new feature  
fix: bug fix  
refactor: code restructuring  
docs: documentation updates  
test: adding tests  
chore: maintenance  

Example:
feat: add ERA5 gust normalization

------------------------------------------------------------
4. Pull Request Rules
------------------------------------------------------------

- One PR per feature  
- PR must be self-contained  
- Documentation updated if necessary  
- Tests should pass  
- PR description must be clear  
- Avoid mixing unrelated changes

------------------------------------------------------------
5. Versioning and Releases
------------------------------------------------------------

Releases follow semantic versioning:

MAJOR.MINOR.PATCH

Example:
v1.2.0

Checklist before release:
- CHANGELOG.md updated  
- main is stable  
- tag created:
  git tag v1.2.0
  git push --tags

------------------------------------------------------------
6. Coding Standards
------------------------------------------------------------

- Follow PEP8  
- Prefer explicit and simple code  
- Use logging module in new code  
- Avoid global state  
- Document non-trivial functions  
- Add minimal tests for new features  

------------------------------------------------------------
7. Syncing Forks or Clones
------------------------------------------------------------

To sync local branch with main:

git checkout main  
git pull  
git checkout feature/my-feature  
git rebase main  

------------------------------------------------------------
8. Contacts
------------------------------------------------------------

Workflow maintainer: Adrien Salicis  
Email: adrien.salicis@cieletterre.net
