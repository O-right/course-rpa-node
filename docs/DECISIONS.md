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

## 2026-06-01: Assignment AI Decisions Are Audited And Multi-Select Reviewed

Decision: During the temporary assignment experiment phase, `assignment_tester.py` logs raw AI response content, normalized answers, and a pre-submit answer summary. Multiple-choice questions receive a second AI review pass by default through `ASSIGNMENT_AI_REVIEW_MULTIPLE=true`; callers can disable raw response logging with `ASSIGNMENT_AI_LOG_RAW_RESPONSE=false`.

Reason: A real authorized experiment submitted `作业:《思想道德与法治》2023版第五章第一节` and scored 90/100 because one multiple-choice question selected `ABC` while the correct answer was `ABCD`. A second deterministic review pass makes this class of miss easier to catch, and the logs make future failures attributable to extraction, model output, normalization, or clicking.

## 2026-06-01: Image Questions Use Browser Screenshots

Decision: For assignment questions containing images, SVGs, canvases, or CSS background images, `assignment_tester.py` captures the rendered question container as an in-memory PNG and sends it to the AI as a `data:image/png;base64,...` multimodal `image_url` part. It does not pass private Chaoxing image URLs directly to the remote API.

Reason: Chaoxing media URLs can depend on browser cookies, referers, temporary tokens, or same-origin state that the remote `glm/chat2api` service does not have. A Playwright screenshot captures what the logged-in browser actually sees and avoids persisting image artifacts to the repository.

## 2026-06-01: Low-Confidence Assignment Answers Halt Before Submit

Decision: `assignment_tester.py` asks the AI to return a `confidence` field, treats missing confidence as low confidence by default, and stops before next/submit when confidence is below `ASSIGNMENT_AI_MIN_CONFIDENCE` or the model marks the answer uncertain. The default threshold is `0.75`, controlled by `ASSIGNMENT_STOP_ON_LOW_CONFIDENCE`, `ASSIGNMENT_AI_REQUIRE_CONFIDENCE`, and `ASSIGNMENT_HOLD_BROWSER_ON_LOW_CONFIDENCE`.

Reason: During temporary authorized assignment experiments, a low-confidence model answer can turn into a poor score if the automation blindly submits. A conservative halt keeps the browser on the current page for manual inspection instead of continuing with weak evidence.

## 2026-06-01: Guarded Assignment Runs Stop On Unanswerable Or Low Score

Decision: Real assignment experiment runs stop before submit when a question cannot be extracted, no usable answer is available, or not all processed questions are selected/mapped. After submit, result pages are scanned for score text such as `90/100` or `得分：90分`; scores below `ASSIGNMENT_MIN_ACCEPTABLE_SCORE` stop further scanning. Defaults are `ASSIGNMENT_STOP_ON_UNANSWERABLE=true`, `ASSIGNMENT_STOP_ON_LOW_SCORE=true`, and `ASSIGNMENT_MIN_ACCEPTABLE_SCORE=80`.

Reason: The current goal is not just to answer quickly, but to avoid continuing after weak evidence, broken extraction, or a poor observed score.

Consequence: Malformed question extraction is also guarded by `ASSIGNMENT_MAX_OPTIONS_PER_QUESTION` so a broken container cannot produce hundreds of synthetic option letters and continue toward submit.

## 2026-06-01: Chaoxing Shared-Option Questions Are Structured

Decision: Treat Chaoxing `共用选项题` as `shared_options`: extract the shared A-E option block from `.stem_answer`, extract each sub-question from `.B-answer-ct`, and click the per-sub-question `.B-answerCon span` matching the ordered AI answer list. Shared-option answers preserve list order and do not de-duplicate or alphabetically sort.

Reason: The previous generic option extractor flattened shared-option DOM into malformed option lists. Screenshot/vision can help with visual recognition, but this question type still requires structured control mapping so each sub-question receives its own A-E selection.

## 2026-06-01: Assignment AI Uses Review Consensus And Risk Budget

Decision: `assignment_tester.py` now treats `ASSIGNMENT_AI_MIN_CONFIDENCE` / `ASSIGNMENT_AI_ACCEPT_CONFIDENCE` as the high-confidence acceptance line, sends medium-confidence answers through enhanced review, records accepted medium-confidence answers against an estimated point-risk budget before submit, retries transient AI request failures, and retries flaky login-page navigation. Defaults are `ASSIGNMENT_AI_ENHANCED_REVIEW=true`, `ASSIGNMENT_AI_REVIEW_SAMPLES=3`, `ASSIGNMENT_AI_REVIEW_CONFIDENCE=0.55`, `ASSIGNMENT_AI_CONSENSUS_RATIO=0.66`, `ASSIGNMENT_RISK_BUDGET_POINTS=5`, `ASSIGNMENT_SUBMIT_WITHIN_RISK_BUDGET=true`, `ASSIGNMENT_AI_REQUEST_RETRIES=2`, and `ASSIGNMENT_NAVIGATION_RETRIES=2`.

Reason: A single self-reported confidence threshold stopped the latest live run at a recoverable medium-confidence question. Lowering the threshold globally would risk poor submissions, so the runner now uses repeated review and a pre-submit risk budget to continue through stable medium-confidence answers while still stopping on unstable, very low-confidence, unanswerable, or over-budget cases.

Consequence: `ASSIGNMENT_MAX_QUESTIONS` now defaults to 120, and hitting that cap is treated as an incomplete run that stops before submit instead of submitting a partially processed page.

## 2026-06-01: Chat2API Recovery Requires A Valid Access Token

Decision: Treat a ChatGPT session cookie update as incomplete until `chatgpt.com/api/auth/session` returns an `accessToken` and an authenticated `/v1/chat/completions` smoke succeeds. A session-token-only file, even with `__Secure-next-auth.session-token.0/.1` split cookies, is not enough evidence that `glm/chat2api` is usable.

Reason: During the assignment real-run continuation, the user-provided `__Secure-next-auth.session-token` and explicit split cookie reached the session endpoint but returned only `WARNING_BANNER`, not `accessToken`. `chat2api` therefore kept falling back to expired or empty tokens and local assignment AI calls failed with HTTP 401.

Consequence: Before resuming real assignment scans, restore a usable AI backend by supplying a complete current ChatGPT cookie header, a direct `accessToken`, a 45-character refresh token, or another working OpenAI-compatible API configuration, then run the assignment AI smoke.

## 2026-06-02: Chat2API Uses A Project-Local Mihomo Proxy

Decision: Keep `chat2api` using `PROXY_URL=http://127.0.0.1:7890` and run the user-provided chained proxy through the local `mihomo.service` bound to loopback ports `7890`, `7891`, and `9090`.

Reason: The ChatGPT upstream path needs a working AI-capable network route, but the proxy must stay scoped to this `chat2api` deployment rather than becoming a container-wide proxy.

Consequence: Updating the proxy means replacing `/home/ubuntu/proxy/config.yaml` and restarting `mihomo.service`; do not set global shell, systemd manager, or container-wide proxy environment variables for unrelated workloads.

## 2026-06-02: Assignment AI Responses Are Parsed Defensively

Decision: `assignment_tester.py` treats AI responses as potentially noisy transport text, not guaranteed pure JSON. It extracts the first JSON object from Markdown-fenced, citation-marked, or otherwise prefixed responses, and normalizes returned answers by mapping unique option text/value matches back to option letters.

Reason: A real assignment run produced AI output wrapped in a fenced block before the JSON, and another response returned a literal option value such as `"6"` for a single-choice question whose controls require `A`/`B`/`C` letters.

Consequence: Prompting still asks for JSON-only output, but parser correctness no longer depends on the model obeying that instruction exactly. Ambiguous value matches remain rejected so the runner does not click an arbitrary option. If the answer field is recoverable but surrounding JSON or confidence text is malformed, the answer is preserved only as a low-confidence result so manual-review and halt guardrails still apply.

## 2026-06-02: High-Risk Assignment Questions Require Review Consensus

Decision: During the temporary assignment experiment phase, math-like, true/false, and media-backed questions go through enhanced review even when the primary AI answer reports high confidence. High-risk review defaults to stricter consensus, can require the primary answer to agree with the review consensus, and labels media screenshots as `media-node-N` in the AI payload so image order can be tied to option order.

Reason: A real `作业:《2026春-线性代数》2026.0528作业` submission scored 70/100. Result-page inspection showed three wrong high-confidence answers, including one pure text linear-algebra concept question and two image/formula-dependent questions. Self-reported confidence alone was not enough evidence to submit.

Consequence: Future real assignment runs may stop more often on high-risk question disagreement, but this is intentional; the guardrail should surface unstable answers before submit instead of continuing to a low-score halt. For high-risk text/image fill-in questions, a later single adjudication response must not override multi-sample review disagreement.

## 2026-06-03: Assignment Actions Must Verify Persisted State

Decision: In real assignment experiment runs, a successful Playwright click/fill is not enough evidence that an answer was applied. Choice and shared-option clicks must verify a selected state in the DOM before the question is counted as mapped, and hidden multi-blank text controls must be ordered by their visible editor/input position rather than raw hidden textarea DOM order.

Reason: Incident review found two distinct failure modes. `作业:《2025-2026-2细胞生物学》作业9-细胞C` was submitted as 0分 with blank answers after an old run logged 54 answer clicks but never verified selected state. `作业:《英语02》课后作业Book2 Unit 5` scored 44.4/100 because two fill-in sections were cyclically shifted despite the intended answers being logged.

Consequence: Real runs should halt more readily when a click does not produce a verifiable selected state or when text control ordering is ambiguous. This is preferred over submitting a page whose browser interaction looked successful but whose answers were not actually persisted in the form state. After text controls are sorted by visible position, any synthetic blank keys such as `__text_10__` must be sorted by numeric blank index, not lexicographically, so later blanks cannot be filled before earlier blanks.

## 2026-06-03: No Next Control Is Not Completion Evidence

Decision: The course watcher must not report full-course completion solely because it cannot find a next-task control or catalog entry. Before returning completion on a no-next path, it waits briefly for Chaoxing completion state to refresh and scans the current page/catalog for unfinished-task markers.

Reason: A `“四史”专题课` stop screenshot showed the current `6.1` task still had an orange unfinished marker while the page had no visible next control. The old logic treated that as normal completion because `CX_STOP_WHEN_NO_NEXT=true`.

Consequence: A no-next page with unfinished markers now fails and saves `no_next_but_incomplete` evidence instead of printing "自动看课流程完成". Full completion still requires either a real successful end-of-course run or a no-next page without detected unfinished signals.

## 2026-06-03: Course Cards Must Use Real Links

Decision: Course selection should prefer real course-card anchors, especially Chaoxing's `.course-info a.color1`, before falling back to generic text matching. If clicking a target `_blank` course link does not open a popup and the current page URL does not change, the watcher may navigate directly to the link href.

Reason: `--course 四史` originally matched a broad course-list container on the personal-space page. The script logged "已点击: 课程卡片" but stayed on `https://i.chaoxing.com/base...`, so chapter lookup then failed on the wrong page.

Consequence: Generic text matching remains only a last resort for non-Chaoxing layouts. For deep starts such as `--chapter "6.1"`, chapter lookup scrolls the catalog while searching instead of assuming the target chapter is already visible.

## 2026-06-03: Video Detection Waits For Nested Iframes

Decision: After entering a Chaoxing learning page, the watcher waits briefly for nested video iframes to inject a real `<video>` element before falling back to non-video courseware handling.

Reason: `“四史”专题课` 6.1 initially exposed the outer `.ans-attach-online` iframe before the inner `ananas/modules/video` iframe finished loading. The watcher treated the page as non-video courseware even though `video#video_html5_api` appeared shortly afterward.

Consequence: `CX_VIDEO_INITIAL_WAIT_SECONDS` controls this wait. Completion detection no longer treats static rule text such as `未完成任务点前，当前视频不可拖拽` as an unfinished signal; visible task/catalog markers are the evidence.

## 2026-06-03: API Recovery Stays Outside The Repository

Decision: The current `glm/chat2api` token/backend recovery is handled outside this repository by the user. Repo maintenance must not add replacement API keys, ChatGPT access tokens, cookies, proxy secrets, or recovered `.env` values to tracked files.

Reason: The API issue is operational credential state, not source code. Keeping it outside the repo prevents accidental secret persistence while still allowing local bounded runs to use process-level environment overrides.

Consequence: Future agents should treat API health as an external prerequisite before live assignment experiments. They may document pass/fail evidence, but must not commit token material or print secret values.

## 2026-06-06: Same-URL Assignment Result Pages Are Submission Evidence

Decision: `assignment_tester.py` treats Chaoxing `dowork` pages containing submitted-result markers such as `我的答案` and `正确答案` as submission/result evidence, even when the URL remains on `dowork` and a submit/retry control is still visible. Pages containing `未达到及格线` plus retry wording halt under the low-score guard if no numeric score can be parsed.

Reason: A real submit on 2026-06-06 stayed on the same `dowork` URL, displayed answer review text, and offered a retry because the score did not meet the passing line. The old completion check expected URL changes, score text, or submit-button disappearance, so it raised `Submit completion was not verified after click` even though Chaoxing had already graded the attempt.

Consequence: Result/retry pages should not be reprocessed as fresh unanswered question pages. Continuing after a low-score/retry result requires an explicit manual-review or guard-change decision rather than silent scanning.

## 2026-06-06: Real Assignment Submits Require Manual Pre-Submit Review

Decision: During the temporary real-assignment experiment phase, do not perform a real submit solely from newly generated AI answers. Before each submit, inspect the fixed answer set, correct obvious bad answers, verify the browser selected state for every answer, and only then enable submission.

Reason: The biology 作业11 pre-submit review caught an obvious wrong answer before submit and improved the final result. The user explicitly requested manual review before every submit to reduce obvious low-score risk.

Consequence: `ASSIGNMENT_REQUIRE_MANUAL_REVIEW_BEFORE_SUBMIT=true` is now the default. Without `ASSIGNMENT_REVIEWED_ANSWER_FILE`, `assignment_tester.py` writes a pre-submit review report under `ASSIGNMENT_REVIEW_OUTPUT_DIR` and halts before submit. Submit runs should point `ASSIGNMENT_REVIEWED_ANSWER_FILE` at a fixed reviewed answer map; the runner title-checks that file against the current assignment, applies those answers instead of re-querying AI, verifies selected state, and only then submits. The biology 作业10 continuation used this path after correcting Q83 and submitted with score `95.5/100`.

## 2026-06-08: Course Playback Recovery Prioritizes Real Player State

Decision: Course video recovery should click the real player controls before falling back to JS `video.play()`, re-locate `<video>` elements after overlay dismissal or iframe recreation, and treat the configured playback rate as best-effort when a task page explicitly says speed-up is not allowed.

Reason: The `2026春-线性代数` `2.4 克拉默法则` task repeatedly paused because Video.js required a `.vjs-big-play-button` click and the page text said `未完成任务点前，当前视频不可倍速、不可拖拽`. Forcing `playbackRate=2` caused the platform to pause or clamp the video, while a real player-control click allowed the task to finish at the platform-allowed speed.

Consequence: Playback rate drift alone is no longer a recovery trigger when media time is progressing. Recovery remains strict on paused or stalled playback, but full-course completion is favored over repeatedly forcing a blocked 2x rate. Logs should distinguish platform-limited 1x playback from actual playback failure.

## 2026-06-09: Course Playback Waits Only On True No-Source Videos

Decision: Video readiness checks should treat `networkState=3` with no usable media metadata as a broken or missing source, while allowing ordinary loading states such as `networkState=1` to proceed into the normal click-and-play path.

Reason: The `2026春-线性代数` retry showed that a valid first video can sit at `readyState=0` and `networkState=1` before play is clicked, but the earlier failure at task point 2 video 4/6 surfaced as `networkState=3` with `NotSupportedError: The element has no supported sources.`

Consequence: `main.py` now reserves the extra source-wait path for true no-source states, using `CX_VIDEO_SOURCE_READY_WAIT_SECONDS` only when the element looks broken instead of blocking normal video startup.

## 2026-06-13: Course Watcher Skips Confirmed Completed Current Tasks

Decision: Before processing videos on the current learning page, `main.py` reads the active chapter/catalog item and skips playback only when that current item is explicitly marked completed.

Reason: A course can reopen on a task point that is already complete. Processing the visible `<video>` again wastes time and can cause duplicate course-watching behavior.

Consequence: The skip is conservative: unknown catalog state still falls back to normal processing, and completion/unfinished text is scoped to the current catalog item so sibling task labels such as `未完成` do not contaminate the current task's status. Chaoxing active-state classes such as `poscatalog_active` are treated as active catalog items.

## 2026-06-14: No-Source Course Videos Try Alternate Routes

Decision: When a course video reports a true no-source state (`networkState=3` with no duration/current time/ready metadata) and the page visibly offers alternate playback routes such as `公网1` / `公网2`, the watcher switches to an unselected route and waits again for media metadata before failing the task.

Reason: The `道德与法治` `6.5 恋爱、婚姻家庭中的道德规范` run stopped with `networkState=3`, `duration=0`, and a platform error that offered other routes. The page exposed an intended recovery control, so switching route is more accurate than treating the first source failure as terminal.

Consequence: Route switching is scoped to pages with visible route/error hints and only runs once per media-readiness wait. If no alternate route is visible or the alternate route still cannot load metadata, the watcher preserves the existing failure screenshots and non-zero exit path.

## 2026-06-14: Course Video Completion Requires A Real End State

Decision: Do not treat `currentTime >= duration - 1` as enough evidence that a course video is complete. The watcher should wait for the browser video element to report `ended`, or for the video to be near the end and paused, then pause briefly before advancing.

Reason: Follow-up `道德与法治` audits showed `6.5` could reappear as unfinished in a new session after the watcher left at roughly `702.1/702.4s` while playback was still running. Waiting until `702.4/702.4s` with `paused=True` produced a later fresh-session audit with no unfinished task points.

Consequence: `CX_VIDEO_COMPLETION_SETTLE_SECONDS` controls the short post-completion wait. This adds a small delay at the end of each video, but it is preferable to advancing before Chaoxing has persisted task completion.

## 2026-06-14: Course Chapters May Contain Multiple Resource Cards

Decision: Treat Chaoxing `#prev_tab` / `.prev_list` resource cards inside one chapter as part of the same learning unit. When a page shows multiple cards such as `1课件 / 2视频`, process each visible card in order and re-run video detection after switching cards before advancing to the next chapter.

Reason: `2025-2026(2) 物理学` `5.1 物质的微观模型` initially loaded only the `num=0` PDF/课件 card, while the actual video was hidden behind a second `2视频` card. The old no-video path handled the PDF and then advanced, leaving the video task unplayed.

Consequence: Non-video cards still get the quick courseware handling, but video cards are now reached through the same chapter page. `CX_LEARNING_CARD_SWITCH_WAIT_SECONDS` controls the brief wait after changing cards.
