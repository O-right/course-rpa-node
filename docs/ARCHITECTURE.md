# Architecture

## System Shape

This is a single-process Python automation project using Playwright's synchronous API.

## Components

- `main.py`
  - `CONFIG`: all site-specific values such as URLs, credentials, course keyword, selectors, delay range, and timeout values.
  - `CourseAutoTester`: owns browser lifecycle and workflow steps.
  - Safe interaction helpers: wrap clicks, fills, waits, and JavaScript video control with delays and exception handling.
- `requirements.txt`
  - Declares the Playwright Python dependency.

## Flow

1. Start headed Chromium.
2. Navigate to the login page.
3. Fill username and password, then submit.
4. Locate the course card by keyword and click it.
5. Locate a video chapter and open it.
6. Wait for a `<video>` element.
7. Set `playbackRate`.
8. Poll playback state until the video ends or a timeout is reached.
9. Click the next-chapter selector and repeat up to a configured limit.

## Key Tradeoffs

- Selectors are configurable instead of site-specific because the real target page is not available yet.
- The script uses headed Chromium by default to make manual observation and debugging easier.
- Synchronous Playwright keeps the script approachable for a small automation project.
