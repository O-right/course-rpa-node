# Decisions

## 2026-04-26: Use Python + Playwright Sync API

Decision: Build the first version as a single `main.py` script using Playwright's synchronous Python API.

Reason: The requested workflow is linear browser automation, and the sync API keeps setup and debugging simple.

## 2026-04-26: Keep Site Details In A Config Dictionary

Decision: Put URL, credentials, course keyword, selectors, delays, and timeouts at the top of `main.py`.

Reason: The target website is not known yet, and selector tuning should not require code changes inside the automation logic.

## 2026-04-26: Headed Chromium By Default

Decision: Launch Chromium with `headless=False`.

Reason: The workflow is visual and likely needs selector debugging during early runs.

## 2026-04-26: AI Brain Uses Cloudflare Tunnel Endpoint

Decision: Configure `assignment_tester.py` to call `https://api.2070814.xyz/v1/chat/completions` with model `gpt-5.5` via local `.env`.

Reason: The endpoint is OpenAI-compatible and can be swapped without changing assignment tester logic.

Operational note: A previous HTTP 530/1033 failure was caused by no active Cloudflare Tunnel connector. The remote `cloudflared-api-tunnel.service` must stay enabled and active, routing `api.2070814.xyz` to `http://127.0.0.1:5005`.

## 2026-04-26: Assignment Tester Is Inbox-Only

Decision: `assignment_tester.py` is a pure Inbox monitor that forces navigation to `ASSIGNMENT_INBOX_URL` after login and scans `li.dataBody_item > a.notice_title` for titles containing `作业：`.

Reason: Assignment monitoring must be isolated from course/video automation and must not fall back to course-list or course-assignment navigation.

## 2026-04-26: Chaoxing Inbox Notices Require Detail Attachment Resolution

Decision: The Inbox monitor opens assignment notices through `.openNotice[data-url]`, then reads the notice attachment iframe's `window.att_web.url` or `window.screenOpenUrl` to reach the real `intoexamorwork` / `dowork` page.

Reason: Live `a.notice_title` elements use `href="#"`; the actionable assignment URL is not on the title link and is only exposed by the notice-detail attachment iframe.

Safety note: Under the original staging-only model, real-site assignment pages stayed dry-run with submissions blocked and live AI disabled unless moved to an explicitly authorized staging host. This is superseded temporarily by the 2026-05-31 experiment note below.

## 2026-04-26: Real Academic Assignment Hosts Are Hard-Blocked

Decision: `assignment_tester.py` was originally intended to explicitly block Chaoxing assignment hosts from live AI decision calls, answer clicks, text fills, and submit actions, regardless of optional config flags.

Reason: The assignment module is for interaction robustness testing, not for answering or submitting real academic work. Multi-question traversal is allowed for dry-run parsing and mapping validation; live AI/click execution must be tested only on authorized staging hosts.

Implementation status note, 2026-04-27: current `assignment_tester.py` does not match this decision. During repo resume, the code was observed defaulting `ASSIGNMENT_DRY_RUN` to false, `ASSIGNMENT_ALLOW_SUBMISSION` to true, `ASSIGNMENT_ALLOW_LIVE_AI_ON_REAL_SITE` to true, allowing Chaoxing hosts in the allowed host lists, and using an empty default blocked-host list.

Superseding experiment note, 2026-05-31: by explicit user direction, this drift is accepted temporarily while the project is in an experiment phase. Future agents should not treat restoring the hard-block as the immediate next blocker unless the user ends the experiment phase. Restore the staging-only defaults and real-site hard-block before returning the assignment tester to normal operation.

## 2026-04-26: Submit Logic Is Staging-Only And Confirmation-Aware

Decision: The assignment submit path supports Chaoxing-style submit selectors (`.Btn_blue_1:has-text('提交')`, `a.btnSubmit`) plus generic submit controls, scrolls the submit button into view, waits around the click, accepts native JS dialogs, and attempts visible custom confirmation buttons.

Reason: Submission flows are timing-sensitive and often require a secondary confirmation. This behavior is useful for authorized staging tests and temporary bounded experiments. The 2026-05-31 experiment note above means the hard-block is not the immediate next blocker, but it must be restored before normal operation.

## 2026-04-26: Course Watcher Favors Recoverable Long Runs

Decision: `main.py` now exposes runtime tuning through `CX_*` environment variables, recovers playback when progress stalls or the video pauses, saves screenshots on failures, and requires observable evidence before treating a Chaoxing next-section click as successful.

Reason: The course-watching flow is long-running and timing-sensitive. Recovering common video stalls and requiring evidence of navigation or page-content transition reduces false success and makes unattended runs easier to diagnose.

## 2026-04-27: Course Watcher Processes Learning Task Points

Decision: Treat the current Chaoxing learning page as a task point. Process every detected `<video>` on the page before moving next; if no video is present, handle the page as courseware/non-video content by quickly opening and returning when a visible courseware entry exists. A next-task click is successful when either the URL changes or the page content signature changes.

Reason: Live `中国近现代史纲要` testing showed that Chaoxing can move from task point 1 to task point 2 inside the same URL. Some chapters can also contain multiple videos or non-video courseware, so URL-only and single-video assumptions are too narrow for full-course automation.

## 2026-04-27: tutai Uses Playwright 1.29.1 While On Windows Server 2012 R2

Decision: Run `course-rpa-node` on tutai with Playwright `1.29.1` and its Chromium `109.0.5414.46` browser build while tutai remains Windows Server 2012 R2.

Reason: Playwright `1.48.0` installed successfully on tutai, but its bundled Chromium cannot execute on Windows Server 2012 R2 and fails with `BrowserType.launch: spawn UNKNOWN`. Downgrading to Playwright `1.29.1` installed Chromium `109`, and the headless Chromium smoke test passed. Future reinstalls must keep this pin or upgrade the operating system first.

## 2026-04-27: tutai Is Not Yet A Viable Chaoxing Runner

Decision: Do not rely on tutai for real Chaoxing course watching until its network path is changed or the Chaoxing login access block is otherwise resolved.

Reason: After syncing `.env`, a real `中国近现代史纲要 --max-chapters 1` smoke on tutai failed before login because Chaoxing redirected the server to `passport2-api.chaoxing.com/views/error/passport403.html`, which then self-redirected and surfaced in Playwright as `net::ERR_TOO_MANY_REDIRECTS`. The same flow is verified locally, so this points to tutai's cloud-server environment/IP rather than the course watcher logic.

## 2026-04-28: Course Watcher Failure Paths Must Return Non-Zero

Decision: `main.py` returns exit code 1 for failed course-watcher paths and exit code 0 only for normal completion or configured max-chapter stop.

Reason: A real OpenClaw Feishu-triggered run reached this runner and made genuine progress, but a Playwright locator timeout near the end of a video produced a local failure while the process still exited with code 0. That made the OpenClaw service shell record `external_runner_completed`.

Consequence: `CourseAutoTester.run()` now returns `bool`, `__main__` maps it to `SystemExit`, and video progress reads retry by re-locating the indexed video before failing.

## 2026-04-28: OpenClaw Quality Tests Should Cap The Runner

Decision: When this runner is launched by OpenClaw for webpage-quality testing, OpenClaw should pass a small `--max-chapters` cap instead of treating the command as a full-course run.

Reason: A fresh OpenClaw-triggered quality run after the stale-locator fix reached task point 6 and encountered a `7238.0s` video. The runner correctly continued, but that is not appropriate for a diagnostic quality-test command.

Consequence: The cap is implemented in `D:\ai` command routing; direct local `main.py` runs remain controlled by `--max-chapters` or `CX_MAX_CHAPTERS`.

## 2026-05-14: Course Watcher Can Use Installed System Browsers

Decision: `main.py` supports `--browser-channel chrome`, `--browser-channel msedge`, `CX_BROWSER_CHANNEL`, and `CX_BROWSER_EXECUTABLE_PATH` in addition to Playwright-managed Chromium.

Reason: Playwright browser downloads can be slow or unavailable on the local network. Using an already installed Chrome or Edge keeps authorized course runs unblocked without changing the watcher workflow.

## 2026-05-31: Assignment Experiment Runs Prefer Fast Bounded Interaction

Decision: During the temporary assignment tester experiment phase, optimize for fast completion: keep only short randomized action delays, use fixed short settle waits instead of default `networkidle`, search briefly for optional next/confirm controls, and make incomplete-answer blocking opt-in with `ASSIGNMENT_BLOCK_ON_INCOMPLETE=true`.

Reason: The current user goal is to complete authorized assignment interaction experiments as quickly as possible while preserving basic page-operation stability. Long manual pauses and broad anomaly handling are deferred until the experiment phase ends.

## 2026-05-31: Course Watcher Polls Video Completion By Remaining Time

Decision: `main.py` still uses periodic progress polling, but near the end of a video it estimates remaining wall time from `duration`, `currentTime`, and `playbackRate` and wakes early instead of always sleeping the full poll interval. `--fast-actions` also caps progress polling and non-video courseware hold time.

Reason: Waiting the full progress poll interval after a nearly completed video creates avoidable idle time. The remaining-time estimate reduces tail latency without changing the playback recovery logic.

## 2026-05-31: GitHub Remote Is O-right/course-rpa-node

Decision: Use `https://github.com/O-right/course-rpa-node` as the canonical GitHub remote for this project. Local `main` tracks `origin/main`; `.env`, `logs/`, `dist/`, `__pycache__/`, and temporary probe JSON files are ignored.

Reason: The project now needs durable off-machine source backup and handoff. Runtime credentials, logs, screenshots, caches, and deployment archives are machine-local artifacts and must stay out of GitHub.

## 2026-05-31: Chat2API Health Requires Both Tunnel And Upstream Token

Decision: Treat `api.2070814.xyz` as healthy only when both `/v1/models` and an authenticated `/v1/chat/completions` smoke pass. Service uptime or Cloudflare Tunnel reachability alone is insufficient.

Reason: The current `glm/chat2api` check showed `chat2api.service` and `cloudflared-api-tunnel.service` running and `/v1/models` returning 200, while authenticated chat completions returned 500 because `chat2api` had no valid token and was falling back to a no-auth ChatGPT path that hit `Unusual activity` / proxy errors.
