# Project Agent Rules

## Project Context

- This repository is a Python + Playwright frontend automation project.
- The MVP automates a browser workflow: log in, open a target course, enter a video chapter, set the `<video>` playback rate to 2.0, monitor playback, and click the next chapter after completion.
- Real site URLs, credentials, and selectors are intentionally kept in `main.py` configuration placeholders.

## Commands

- Install dependencies: `python -m pip install -r requirements.txt`
- Install browser: `python -m playwright install chromium`
- Run automation: `python main.py`
- Run Chaoxing automation: `.\run_chaoxing.ps1`
- Run assignment robustness tester: `python assignment_tester.py`
- Syntax check: `python -m py_compile main.py assignment_tester.py`

## MUST DO

- Read `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/TASKS.md`, `docs/STATUS.md`, and `docs/DECISIONS.md` before non-trivial changes.
- Keep selectors and credentials configurable; do not hard-code private production values inside logic.
- Add random delays between click and input operations to reduce brittle automation timing.
- Preserve basic exception handling around page operations so missing elements fail gracefully.

## MUST NEVER

- Never commit real passwords, tokens, cookies, private course URLs, or `.env`.
- Never bypass a site's access controls, payment controls, or terms of use.
- Never claim the end-to-end course flow is verified unless it ran against a real configured site.
