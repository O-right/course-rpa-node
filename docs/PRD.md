# PRD: Course Frontend Automation Tester

## Goal

Build a small Python + Playwright automation script that can drive a course website through login, course selection, video chapter playback, and automatic next-chapter progression.

## MVP Features

- Launch a headed Chromium browser.
- Open a configurable login URL.
- Fill a configurable username and password.
- Click the login button.
- Find and click a course by configurable course name keyword.
- Enter a video chapter using configurable selectors.
- Set the first `<video>` element's `playbackRate` to `2.0`.
- Poll playback progress until the video ends.
- Click the configured next-chapter control and repeat.
- Add `random.uniform(2, 5)` delay before click and input operations.
- Catch common Playwright exceptions so missing elements do not crash the process without context.

## Out Of Scope

- CAPTCHA solving.
- MFA or SMS login automation.
- Scraping private data.
- Site-specific selector tuning before the real target page is known.
- CI execution against a real course site.

## Acceptance Criteria

- `requirements.txt` contains the Playwright dependency.
- `main.py` contains an object-oriented implementation with a clear top-level config dictionary.
- The script can be syntax-checked locally.
- Dependency and browser installation commands are documented.

## Assumptions

- The user is authorized to log in and access the target course.
- The real site selectors will be filled in manually after inspecting the target website.
- Chromium is sufficient for the first implementation.
