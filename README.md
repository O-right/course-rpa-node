# Chaoxing Course Automation Tester

Python + Playwright automation for an authorized Chaoxing course account.

## Setup

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## Run

Use the launcher. If `.env` exists, credentials are loaded automatically. Otherwise the launcher asks for credentials for that run:

```powershell
.\run_chaoxing.ps1
```

To choose a course for this run, pass a course keyword:

```powershell
.\run_chaoxing.ps1 --course "课程名称关键词"
```

You can also start from a specific chapter keyword or cap a test run:

```powershell
.\run_chaoxing.ps1 --course "课程名称关键词" --chapter "第一章" --max-chapters 3
```

For an authorized quick validation run, reduce click/input waits:

```powershell
.\run_chaoxing.ps1 --course "中国近现代史纲要" --max-chapters 1 --headless --fast-actions
```

If Playwright browser download is slow or unavailable, use an installed system browser:

```powershell
.\run_chaoxing.ps1 --course "“四史”专题课" --headless --fast-actions --browser-channel chrome
.\run_chaoxing.ps1 --course "“四史”专题课" --headless --fast-actions --browser-channel msedge
```

The script is configured for:

- Login URL: Chaoxing passport login
- Course keyword: `“四史”专题课`
- Login selectors: `#phone`, `#pwd`, `#loginBtn`

## Course Runtime Settings

Useful `.env` / PowerShell environment settings for `main.py`:

```text
CX_HEADLESS=true
CX_BROWSER_CHANNEL=chrome
CX_SLOW_MO_MS=0
CX_MIN_ACTION_DELAY_SECONDS=0.1
CX_MAX_ACTION_DELAY_SECONDS=0.3
CX_MAX_CHAPTERS=100
CX_STOP_WHEN_NO_NEXT=true
CX_PLAYBACK_RATE=2.0
CX_PROGRESS_POLL_SECONDS=10
CX_PROGRESS_MIN_POLL_SECONDS=0.5
CX_PROGRESS_COMPLETION_MARGIN_SECONDS=0.8
CX_PROGRESS_STALL_POLLS=3
CX_COMMITMENT_TIMEOUT_MS=10000
CX_COURSEWARE_HOLD_SECONDS=1.0
CX_COMPLETION_SETTLE_SECONDS=5.0
CX_VIDEO_INITIAL_WAIT_SECONDS=12.0
CX_SCREENSHOT_DIR=logs/screenshots
```

The watcher processes learning task points, not only URL-level chapters. If a task point contains multiple `<video>` elements, it sets speed and waits for each video in sequence. If a task point has no video, it treats it as a courseware/non-video task, tries to open a visible courseware entry, then closes the popup or goes back quickly.

The watcher retries playback if the video pauses, the speed drifts, or progress stops moving for several polls. Near the end of a video, it wakes early based on remaining duration and playback rate instead of always sleeping the full poll interval. If a failure occurs, it saves a screenshot under `logs/screenshots`.

When no next-task control is available, the watcher waits briefly for Chaoxing to refresh completion state and scans the current page/catalog for unfinished-task markers. If the current task still appears incomplete, it fails with a diagnostic screenshot instead of reporting full-course completion.

`--fast-actions` also lowers action delays, disables Playwright slow motion, caps video progress polling at 3 seconds, and caps non-video courseware hold time at 0.2 seconds. You can override those directly:

```powershell
.\run_chaoxing.ps1 --course "课程名称关键词" --headless --fast-actions --progress-poll-seconds 2 --courseware-hold-seconds 0.1
```

If Chaoxing shows the online learning commitment dialog, the script attempts to confirm it automatically when `CX_AUTO_COMMITMENT=true`.

## Validation

```powershell
python -m py_compile main.py
python -m py_compile assignment_tester.py
python -c "import main; print('main import ok')"
```

## Assignment Robustness Tester

`assignment_tester.py` is an independent module for assignment/quiz interaction robustness experiments. It can extract question text and options, call a local OpenAI-compatible decision API, parse JSON answers, and verify answer-control mapping.

Current repository note: during the temporary experiment phase, the real Chaoxing assignment host hard-block may remain relaxed by explicit user direction. Treat this as reversible experiment state, keep runs authorized and bounded, and restore the staging-only defaults when the experiment ends. This note does not override site access rules, account authorization, or the repo rule against committing secrets.

It now runs as a background-style monitor by default:

```powershell
$env:ASSIGNMENT_SERVER_MODE="true"
python assignment_tester.py
```

Useful monitor settings:

```text
ASSIGNMENT_SCAN_INTERVAL_SECONDS=3600
ASSIGNMENT_MAX_SCAN_ROUNDS=0
ASSIGNMENT_INBOX_URL=
ASSIGNMENT_DRY_RUN=false
ASSIGNMENT_ALLOW_SUBMISSION=true
ASSIGNMENT_ALLOW_LIVE_AI_ON_REAL_SITE=true
ASSIGNMENT_BLOCKED_REAL_ASSIGNMENT_HOSTS=
ASSIGNMENT_MIN_ACTION_DELAY_SECONDS=0.05
ASSIGNMENT_MAX_ACTION_DELAY_SECONDS=0.15
ASSIGNMENT_MIN_READING_DELAY_SECONDS=0.1
ASSIGNMENT_MAX_READING_DELAY_SECONDS=0.3
ASSIGNMENT_WAIT_FOR_NETWORKIDLE=false
ASSIGNMENT_SETTLE_WAIT_MS=300
ASSIGNMENT_NEXT_BUTTON_TIMEOUT_MS=800
ASSIGNMENT_SUBMIT_BUTTON_TIMEOUT_MS=3000
ASSIGNMENT_CONFIRMATION_INITIAL_WAIT_MS=250
ASSIGNMENT_CONFIRMATION_TIMEOUT_MS=800
ASSIGNMENT_BLOCK_ON_INCOMPLETE=false
ASSIGNMENT_HOLD_BROWSER_ON_EXIT=false
ASSIGNMENT_REQUIRE_MANUAL_REVIEW_BEFORE_SUBMIT=true
ASSIGNMENT_REVIEW_OUTPUT_DIR=logs/reviews
ASSIGNMENT_REVIEWED_ANSWER_FILE=
```

The monitor is Inbox-only. It forces navigation to `ASSIGNMENT_INBOX_URL`, opens the `收件箱` view when needed, and scans notice items such as `li.dataBody_item > a.notice_title`. It should not fall back to course-list or course-assignment navigation.

Real submit runs require a manual pre-submit review by default. Without `ASSIGNMENT_REVIEWED_ANSWER_FILE`, the tester writes `assignment_pre_submit_review_*.json` under `ASSIGNMENT_REVIEW_OUTPUT_DIR` and halts before submit. After review, point `ASSIGNMENT_REVIEWED_ANSWER_FILE` at a corrected answer file; the runner checks the assignment title before applying the fixed answers.

For the current temporary experiment phase, the default assignment timing is intentionally short. Keep `ASSIGNMENT_BLOCKED_REAL_ASSIGNMENT_HOSTS=` empty and `ASSIGNMENT_BLOCK_ON_INCOMPLETE=false` when you want the run to continue instead of pausing for manual anomaly handling. Restore blocked hosts and set stricter flags when the experiment ends.

AI API settings are read from `.env` when present:

```text
ASSIGNMENT_AI_API_URL=https://api.2070814.xyz/v1/chat/completions
ASSIGNMENT_AI_API_KEY=...
ASSIGNMENT_AI_MODEL=gpt-5.5
```
