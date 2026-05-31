# Status

## Current Phase

Course watcher hardened for recoverable long runs.

## Current Focus

Course watcher is live-verified across the first 5 `中国近现代史纲要` learning task points. Assignment tester is in a temporary experiment phase where the real Chaoxing assignment host hard-block may remain relaxed by explicit user direction and should be restored later. The project is now hosted on GitHub at `https://github.com/O-right/course-rpa-node`; local `main` tracks `origin/main`.

## Completed

- Project rules and kickoff docs created.
- Dependency file created.
- Core automation script drafted.
- Python dependencies installed from `requirements.txt`.
- Playwright Chromium installed.
- `python -m py_compile main.py` passed.
- Playwright import smoke test passed.
- `import main` smoke test passed.
- Chaoxing login URL, course keyword, and login selectors configured.
- `run_chaoxing.ps1` added; it now uses local `.env` automatically when present.
- Authenticated probing confirmed the target course appears in the Chaoxing course iframe.
- Course-page probing found the `章节` tab and an online learning commitment dialog.
- `main.py` now switches to the course popup page, searches page frames, and attempts automatic commitment confirmation when present.
- `README.md` added with setup and run instructions.
- Fixed Playwright Python `Locator.first` usage that caused `TypeError: 'Locator' object is not callable`.
- Locator helper smoke test passed for `#phone`, `#pwd`, and `#loginBtn`.
- Fixed course-card lookup timing by polling current page frames until `lookup_timeout_ms` instead of checking the frame list only once.
- Delayed iframe lookup smoke test passed for the `“四史”专题课` course selector.
- Saved local ignored `.env` credentials for automatic login on this machine.
- Added `python-dotenv` so `main.py` reads `.env` directly.
- Tightened chapter selection to `.chapter_item[onclick*='toOld']` so the script clicks a real task-point chapter rather than a non-navigating title.
- Authenticated smoke test passed through login, course open, chapter open, video detection, and setting `playbackRate` to `2`.
- Added `assignment_tester.py` as an independent assignment/quiz interaction robustness tester with an intended dry-run safety model.
- Added `requests` dependency for local OpenAI-compatible API calls.
- Verified `ask_ai_brain()` response parsing with a fake API response.
- Verified local DOM extraction for question text, options, type, and controls.
- Configured assignment tester AI endpoint from `.env`: `https://api.2070814.xyz/v1/chat/completions`, model `gpt-5.5`.
- Real AI endpoint smoke test now passes from this machine: `ask_ai_brain()` returned `["A"]` for a neutral connectivity test question.
- Confirmed Chaoxing login DOM in headless Playwright: username `#phone`, password `#pwd`, login button `#loginBtn`.
- Updated `assignment_tester.py` default login URL and selectors to Chaoxing.
- Saved `ASSIGNMENT_LOGIN_URL`, `ASSIGNMENT_USERNAME`, and `ASSIGNMENT_PASSWORD` in local ignored `.env`.
- Verified both `main.py` and `assignment_tester.py` load the Chaoxing login URL and locate the login selectors on the live page.
- Enhanced `assignment_tester.py` to navigate from Chaoxing home to the configured course, click the course sidebar `作业` tab, and search assignment content across page frames and `frame_locator`.
- Probed the live course assignment page: `#nav_7059` opens `mooc2/work/list...`; the current course reports `暂无作业`.
- Added Chaoxing-style question extraction support for `.Py_tk` question stems and `.Py_answer` option lists inside iframes.
- Verified local iframe extraction for `.Py_tk` and `.Py_answer li` with radio controls.
- Verified live login -> course -> assignment tab flow; it returns gracefully because no unsubmitted homework exists in the current course.
- Refactored `assignment_tester.py` into background monitor entrypoint with `run_monitor()` and `scan_inbox()`.
- Added `server_mode`, `headless`, `scan_interval_seconds`, `max_scan_rounds`, `inbox_keywords`, and `inbox_unhandled_keywords` config.
- Added Inbox candidate scanning, keyword/status matching, candidate navigation, and timestamped scan logs.
- Added direct `ASSIGNMENT_INBOX_URL` support plus fallback to configured course `作业` tab when no Inbox entry is visible.
- Verified local Inbox scan smoke test with one matching candidate.
- Verified one live monitor round: login succeeded, Inbox entry was not visible, fallback reached course `作业`, and no pending homework was found.
- Updated Inbox scanning to match confirmed Chaoxing DOM: iterate `li.dataBody_item`, read/click `a.notice_title`, and filter titles containing `作业：`.
- Verified local Chaoxing Inbox DOM smoke test: only `li.dataBody_item > a.notice_title` with `作业：` is selected.
- Fixed `main.py` next-chapter handling by adding the real visible Chaoxing control `#prevNextFocusNext`; verified click navigates from `chapterId=1151598212` to `chapterId=1151598213`.
- Hardened `main.py` next-chapter handling with direct `#prevNextFocusNext` click and onclick fallback.
- Verified `CourseAutoTester.click_next_chapter()` integration: login, open first lesson URL, click next, land on `chapterId=1151598213`, and detect video.
- Rebuilt `assignment_tester.py` as a pure Inbox monitor: removed course-name/course-list/course-assignment fallback logic and all course navigation.
- `assignment_tester.py` now reads assignment-scoped AI variables (`ASSIGNMENT_AI_API_URL`, `ASSIGNMENT_AI_API_KEY`, `ASSIGNMENT_AI_MODEL`) from `.env`.
- Verified live pure Inbox one-round monitor: login -> forced Inbox URL -> 0 `作业：` candidates -> logs `扫描完毕，暂无作业，准备休眠`; no course page was visited.
- Fixed an Inbox navigation race after login by waiting for `i.chaoxing.com` and retrying forced Inbox navigation if the first `page.goto()` is aborted.
- Re-ran visible one-round monitor: login succeeded, forced Inbox URL opened, scan found 0 `作业：` candidates, and exited cleanly.
- Fixed live Inbox loading by clicking the `收件箱` navigation entry after the forced `i.chaoxing.com/base` shell URL loads.
- Updated Inbox matching to handle both `作业：` and real DOM `作业:` titles, and to extract `.openNotice[data-url]` detail links.
- Added notice-detail attachment handling: `assignment_tester.py` reads `window.att_web.url` / `window.screenOpenUrl` from the attachment iframe and opens the real `intoexamorwork` URL.
- Added Chaoxing `dowork` question selectors: `.questionLi`, `.mark_name`, and `.answerBg[role=radio|checkbox]`.
- Verified visible one-round Inbox flow against the read `作业:《思想道德与法治》2023版第三章` notice: scan found 8 assignment candidates, limited processing to the first, opened the notice detail, followed the assignment attachment, reached `mooc2/work/dowork`, extracted a single-choice question with options `A-D`, and completed dry-run mapping without submission.
- Added multi-question processing for assignment test pages: `process_all_questions()` enumerates `.questionLi` containers up to `max_questions`, extracts each stem/options/type, maps answers, and defers next/submit until the page-level question loop completes.
- Added real-site safety hardening originally intended to block Chaoxing assignment hosts from live AI calls and answer clicks even if a config flag is changed; current experiment stance supersedes that as an immediate blocker.
- Optimized `.answerBg` option text extraction to avoid slow label-selector timeouts.
- Verified headless dry-run against the live `dowork` page: 10 question containers were detected; 1-5 parsed as single choice, 6-10 parsed as multiple choice; no AI request or answer click was made on the real host.
- Verified a focused two-question dry-run after the extraction optimization: both questions parsed and mapped quickly, with `Live AI disabled on real assignment host` logged.
- Added text-answer detection for non-choice questions: when a question container has no choice options, `assignment_tester.py` now looks for `input[type=text]` or `textarea` and marks the question as `text`.
- Updated AI payload shape for authorized staging text questions to include `question_type`, and accepts either `{"answer": "文本"}` or `{"answer": ["文本"]}` responses.
- Added dry-run text fill path: logs `[探测到简答题] 准备填入内容：...`; real `.fill()` still requires actions to be allowed.
- Verified local DOM smoke test with one `textarea`简答题 and one `input[type=text]`填空题; both parsed as `text` and logged the dry-run fill message without writing.
- Verified mocked API parsing for a text answer response without making a network request.
- Detected assignment tester safety configuration drift during repo resume: current code does not match the intended safe defaults documented in the design notes.
- Hardened staging-only submit flow: submit selector now includes Chaoxing-style `.Btn_blue_1:has-text('提交')` and `a.btnSubmit`, scrolls the button into view, waits before/after clicking, and raises a `RuntimeError` if no submit button is found when submission is allowed.
- Added JS dialog handling with `page.on("dialog", ...)` and custom confirmation handling for visible confirm buttons such as `确定` / `确认`.
- Added explicit submit debug logs: `[Action] 正在定位提交按钮...`, `[Action] 点击提交...`, `[Action] 处理确认弹窗...`, and completion logging.
- Verified local staging fixtures for submit hardening: one custom confirmation dialog and one native `alert('确认提交吗')` both completed successfully.
- Re-applied submit double-confirmation handling in `assignment_tester.py`: submission now ensures the native dialog listener is active immediately before clicking, waits 2 seconds for a custom confirmation, and includes `.bluebtn`, `确认提交`, `确定`, and `确认` selectors.
- Sped up assignment interaction timing: normal click/fill delays are now `0.8-1.8s`, and next/submit reading delays are now `3-8s`.
- Documented the assignment tester drift instead of changing code: under the original staging-only design it needed a safety pass before real assignment use; as of 2026-05-31 this is temporarily accepted for experimentation.
- Fixed a second submit-confirmation failure mode: custom confirmation handling now supports up to 3 confirmation layers and can click popup buttons labeled `提交` as well as `确认提交` / `确定` / `确认`.
- Removed the invalid Playwright `.filter(state="visible")` usage from the submit confirmation path and replaced it with explicit visible/enabled locator scanning across the page and frames.
- Optimized `main.py` for unattended course watching: core runtime settings now read from `CX_*` environment variables, including headless mode, slow motion, playback rate, max chapters, timeouts, and screenshot directory.
- Added command-line course selection to `main.py` and `run_chaoxing.ps1`: use `.\run_chaoxing.ps1 --course "课程名称关键词"` for a one-off target course.
- Updated course watcher completion handling: after a video finishes, missing or disabled next-section controls are treated as normal end-of-course completion when `CX_STOP_WHEN_NO_NEXT=true`.
- Added learning-task processing inside `main.py`: each current task page processes all detected `<video>` elements in sequence; no-video pages are treated as courseware/non-video tasks with quick open/return handling.
- Added `--fast-actions` and `CX_MIN_ACTION_DELAY_SECONDS` / `CX_MAX_ACTION_DELAY_SECONDS` so authorized test runs do not wait 2-5 seconds between every click/input.
- Fixed Chaoxing next-task detection for same-URL transitions by accepting page-content signature changes as successful advancement.
- Added playback recovery in `main.py`: when video pauses, playback rate drifts, or progress stalls for configured polls, the script re-applies mute/playbackRate and calls `play()` again.
- Hardened Chaoxing next-section handling: `#prevNextFocusNext` is only used when visible and not disabled; after click or onclick fallback, URL must change before the script treats the next-section transition as successful.
- Added failure screenshots for login/course/chapter/video/next-section failures and unexpected exceptions, saved under `logs/screenshots` by default.
- Updated `README.md` with course watcher runtime settings and recovery behavior.
- Verified `main.py` syntax, environment-variable config parsing, and a local `#prevNextFocusNext` navigation smoke test.
- Updated `README.md`, `docs/STATUS.md`, `docs/TASKS.md`, and `docs/DECISIONS.md` to reflect that assignment tester safety defaults are out of sync with the original staging-only model.
- Verified first course-selection slice locally: `python -m py_compile main.py assignment_tester.py`, `python main.py --help`, `.\run_chaoxing.ps1 --help`, CLI config override parsing, and conflicting `--headless --headed` rejection.
- Live-tested `中国近现代史纲要` with `python -u main.py --course "中国近现代史纲要" --max-chapters 1 --headless --fast-actions` while using the same arguments supported by `run_chaoxing.ps1`: login succeeded, course opened, one task page with 1 video was processed, the 52.5s video reached 100% at 2x speed, and the next-task click was accepted via same-URL page-content change.
- Live-tested `中国近现代史纲要` with `python -u main.py --course "中国近现代史纲要" --max-chapters 5 --headless --fast-actions`: completed 5 learning task points, processed 8 videos to 100% at 2x speed, handled one no-video task with short wait, handled one courseware/non-video task by opening the courseware entry and continuing, accepted same-URL page-content transitions, and used the onclick fallback when a completion overlay intercepted the normal next-button click. Log: `logs/live_china_history_5tasks_20260427_134618.out.log`; stderr was empty.
- 2026-04-28 OpenClaw Feishu-triggered live run reached this runner with `python -u main.py --course 中国近现代史纲要 --headless --fast-actions`. It logged in, opened the course, processed 3 learning task points, observed 2x video progress, and saved screenshots when the third video progress locator timed out near completion.
- Fixed `main.py` so failure paths return process exit code 1 instead of silent process success, and video progress reads retry by re-locating the indexed video before failing.
- 2026-04-28 fresh OpenClaw Feishu-triggered run after the stale-locator fix passed the previous failure point: task point 3 video 3/3 completed, task points 4 and 5 advanced, and task point 6 videos 1-5 completed.
- That fresh run was intentionally stopped from OpenClaw when task point 6 video 6/7 reported duration `7238.0s`; this was a quality-test run, not a full-course completion run.
- Created tutai deployment documentation at `D:\infra-vault\servers\tutai\course-rpa-node.md`.
- Created local tutai deployment archive at `dist\course-rpa-node-tutai-20260427.zip`; archive contents were checked and exclude `.env`, `logs`, and `__pycache__`.
- Verified tutai SSH host key fingerprint and added it to local `known_hosts`.
- Configured dedicated SSH key access for tutai; non-interactive SSH now works for `administrator@47.110.36.32`.
- Installed the deployment archive on tutai under `D:\services\course-rpa-node`.
- Installed Python dependencies on tutai. Playwright `1.48.0` installed successfully but its Chromium build cannot run on Windows Server 2012 R2, so the tutai runtime was downgraded to Playwright `1.29.1` with Chromium `109.0.5414.46`.
- Verified tutai after the downgrade: `python -m py_compile main.py assignment_tester.py`, `python main.py --help`, and a headless Playwright Chromium smoke test all passed.
- Synced the local ignored `.env` to tutai `D:\services\course-rpa-node\.env` with UTF-8 no BOM; contents were not printed or written to docs.
- Ran tutai `中国近现代史纲要 --max-chapters 1 --headless --fast-actions` smoke. The script reached the login navigation step, but Chaoxing returned `net::ERR_TOO_MANY_REDIRECTS` and saved `logs\screenshots\20260427_164408_login_failed.png`.
- Probed the tutai Chaoxing login redirect chain without credentials. `passport2.chaoxing.com/login...` redirects to `https://passport2-api.chaoxing.com/views/error/passport403.html`, and that 403 page redirects to itself. This indicates a Chaoxing access block for tutai's cloud-server environment/IP, not a selector or credential failure.
- Removed the tutai deployment directory `D:\services\course-rpa-node`; this also removed the synced remote `.env` and remote logs/screenshots. Confirmed the previous SFTP upload location `D:\qampp\htdocs\course-rpa-node-tutai-20260427.zip` is absent.
- Added system browser launch support to `main.py` for slow Playwright browser downloads: use `--browser-channel chrome`, `--browser-channel msedge`, `CX_BROWSER_CHANNEL`, or `CX_BROWSER_EXECUTABLE_PATH`.
- Updated docs on 2026-05-31 to record the current assignment tester experiment stance: the hard-block drift is intentional for now, not the next blocker, and must be restored after the experiment phase.
- Optimized assignment tester timing for the temporary experiment phase: default click/fill delays are now `0.05-0.15s`, next/submit reading delays are `0.1-0.3s`, networkidle waits are disabled by default, submit confirmation uses short polling, and incomplete-answer blocking is configurable instead of sleeping for 7200 seconds by default.
- Optimized course watcher timing: video completion polling now wakes early based on remaining duration and playback rate, and `--fast-actions` also caps progress polling at 3 seconds and non-video courseware hold time at 0.2 seconds.
- Initialized local Git repository, created GitHub repository `O-right/course-rpa-node`, uploaded source/docs while excluding `.env`, `logs/`, `dist/`, `__pycache__/`, and synced local `main` with `origin/main` after normal GitHub HTTPS connectivity recovered.
- Inspected remote `glm` LXC `chat2api`: `chat2api.service`, `cloudflared-api-tunnel.service`, and `mihomo.service` are running; `api.2070814.xyz` routes through Cloudflare Tunnel to `127.0.0.1:5005`; `/v1/models` returns 200 locally and publicly.
- Diagnosed current assignment AI endpoint degradation: authenticated `/v1/chat/completions` returns 500; `chat2api` logs show `Request token is empty, use no-auth 3.5`, `Unusual activity has been detected`, and intermittent `SSL_ERROR_SYSCALL` to `chatgpt.com`; `chat2api-session-refresh.service` is failed and `data/token.txt` is effectively empty.

## Next Action

- Run `.\run_chaoxing.ps1` for a live headed check, or set `CX_HEADLESS=true` / `CX_SLOW_MO_MS=0` for background operation.
- Use `.\run_chaoxing.ps1 --course "课程名称关键词"` to target the course to watch.
- If Playwright Chromium is missing or downloading too slowly, use the installed browser path: `.\run_chaoxing.ps1 --course "“四史”专题课" --headless --fast-actions --browser-channel chrome`.
- Let the script continue beyond `--max-chapters 5` on `中国近现代史纲要` or another authorized course to validate longer unattended operation and full-course completion.
- Do not treat tutai as a current Chaoxing runner; its previous deployment and remote `.env` have been removed.
- If a suitable network path/proxy is configured on tutai, rerun `python -u main.py --course "中国近现代史纲要" --max-chapters 1 --headless --fast-actions` before any longer run.
- For now, use the local machine as the verified runner for `中国近现代史纲要`; local 5-task validation remains the strongest end-to-end evidence.
- Keep tutai on Playwright `1.29.1` / Chromium `109` while it remains Windows Server 2012 R2, unless the OS is upgraded and browser compatibility is revalidated.
- Continue course watcher validation locally if full-course completion evidence is needed.
- During the temporary assignment tester experiment, keep runs explicit and bounded with environment variables; record any live behavior and restore the real-site hard-block when the experiment ends.
- For fastest assignment experiments, use the new `ASSIGNMENT_*_DELAY_SECONDS`, `ASSIGNMENT_SETTLE_WAIT_MS`, `ASSIGNMENT_NEXT_BUTTON_TIMEOUT_MS`, `ASSIGNMENT_CONFIRMATION_*`, and `ASSIGNMENT_BLOCK_ON_INCOMPLETE=false` controls.
- Restore `glm/chat2api` health before relying on live AI answer generation: refresh a valid ChatGPT access/session token, rerun `chat2api-session-refresh.service`, and re-smoke authenticated `/v1/chat/completions`.
- If `chat2api` still reports `Unusual activity` after token refresh, switch or repair the `mihomo` `AI/Proxies` route before rerunning assignment AI tests.
- Configure `assignment_tester.py` selectors only against authorized pages.
- Keep live runs constrained with `ASSIGNMENT_MAX_SCAN_ROUNDS=1` and `ASSIGNMENT_MAX_CANDIDATES_PER_ROUND=1` when doing manual Inbox pressure tests.
- Use localhost or another controlled fixture to validate live AI answer selection, real clicking behavior, text `.fill()`, and submit confirmation behavior when possible.

## Blockers

- `.env` contains local credentials and is ignored by `.gitignore`; do not commit or share it.
- Full-course completion still needs a longer unattended run; the first 5 task points of `中国近现代史纲要` are verified, and a later OpenClaw-triggered run reached task point 6 before being intentionally stopped at a 7238s video.
- tutai deployment has been removed. Re-deploy only after deciding on a viable network path; the previous real course smoke was blocked by Chaoxing returning the self-looping `passport403.html` redirect from tutai's cloud-server network.
- tutai is Windows Server 2012 R2; current Playwright/Chromium releases are incompatible. Reinstalling unpinned `playwright` may upgrade back to an incompatible browser unless the runtime is pinned or the OS is upgraded.
- `assignment_tester.py` currently has a documented safety configuration drift: code defaults allow non-dry-run behavior and real-site AI/actions more broadly than the original staging-only design. This is accepted temporarily for the current experiment by user direction, but must be restored before returning to normal operation.
- Assignment AI endpoint currently cannot be trusted for live answers: Cloudflare Tunnel and `/v1/models` are up, but authenticated `/v1/chat/completions` returns 500 because `glm/chat2api` lacks a valid token and is hitting ChatGPT no-auth/proxy friction.
- Login credentials are stored only in local ignored `.env`; do not share or commit it.
- `assignment_tester.py` has no course fallback by design; if the forced Inbox URL changes, update `ASSIGNMENT_INBOX_URL`.

## Validation Expectations

- Local syntax checks can pass immediately.
- Latest timing optimization checks passed: `python -m py_compile main.py assignment_tester.py`, `python main.py --help`, `.\run_chaoxing.ps1 --help`, course fast-action config override smoke, assignment fast default config smoke, and a local two-question assignment fixture that selected answers and submitted in 0.844s using system Chrome headless.
- GitHub sync checks passed: `git push -u origin main` succeeded after network recovery, local branch is clean and tracks `origin/main`, and remote tree contains only source/docs/script files, not `.env`, `logs/`, `dist/`, or caches.
- `glm/chat2api` checks passed for ingress only: SSH to `glm` works, services are running, public `/v1/models` is 200, and unauthenticated chat returns 403 as expected; authenticated chat smoke currently returns 500 and remains unresolved.
- End-of-video next-task handling is verified on `中国近现代史纲要` for 8 videos across 5 task points, including same-URL transitions and an onclick fallback after overlay interception.
- Full-course completion is not yet verified.
- Local course-watcher checks passed: syntax check, env config parsing, and simulated `#prevNextFocusNext` URL-change smoke test.
- Latest course-watcher CLI checks passed: syntax check, direct help output, launcher help forwarding, argument override parsing, and invalid headless/headed conflict handling.
- Latest OpenClaw-triggered runner fix checks passed: `python -m py_compile main.py assignment_tester.py` and `python main.py --help`.
- Latest OpenClaw-triggered live check passed the previous stale-locator failure point and was intentionally stopped at a 7238s video; this validates the re-located video progress read for the old failure path but does not validate full-course completion.
- tutai remote checks passed on 2026-04-27 after downgrading to Playwright `1.29.1`: syntax check, direct help output, and headless Chromium browser smoke.
- tutai real course smoke was attempted on 2026-04-27 and failed at login navigation because Chaoxing redirected tutai to `passport403.html`; no course page or video was reached.
- tutai cleanup verification passed: `D:\services\course-rpa-node` no longer exists, and the prior upload path `D:\qampp\htdocs\course-rpa-node-tutai-20260427.zip` also does not exist.
- Assignment tester now has one live dry-run Inbox-to-dowork validation against a read Chaoxing notice; no answer was submitted.
- Live API connectivity check now passes; fake API parsing tests for choice and text answers pass; local submit confirmation fixtures pass.
- Latest assignment submit checks passed locally: `python -m py_compile main.py assignment_tester.py`, native `confirm()` auto-accept fixture, and custom HTML `.bluebtn` confirmation fixture.
- Latest multi-step submit checks passed locally: native dialog does not re-click the main submit button, custom `确定` confirmation works, custom popup `提交` confirmation works, and a two-step `确定` then `提交` flow works.
- Monitor mode is live-verified for one pure Inbox scan round after login navigation retry; long-running hourly operation was not left running.
- Course next-chapter transition is integration-verified without waiting for another full video completion.

## Active Files

- `main.py`
- `assignment_tester.py`
- `requirements.txt`
- `run_chaoxing.ps1`
- `dist/course-rpa-node-tutai-20260427.zip`
- `.env` (local ignored credentials)
- `README.md`
- `.gitignore`
- `docs/TASKS.md`
- `docs/STATUS.md`
- `docs/DECISIONS.md`
