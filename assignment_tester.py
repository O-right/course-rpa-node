import json
import logging
import os
import random
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


load_dotenv()


def env_flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_list(name: str, default: List[str]) -> List[str]:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return [item.strip() for item in raw_value.split(",") if item.strip()]


CONFIG: Dict[str, Any] = {
    "login_url": os.getenv(
        "ASSIGNMENT_LOGIN_URL",
        "https://passport2.chaoxing.com/login?fid=&newversion=true&refer=https%3A%2F%2Fi.chaoxing.com",
    ),
    "username": os.getenv("ASSIGNMENT_USERNAME", ""),
    "password": os.getenv("ASSIGNMENT_PASSWORD", ""),
    "inbox_url": os.getenv("ASSIGNMENT_INBOX_URL", "https://i.chaoxing.com/base?t=1777187587609"),
    "api_url": os.getenv("ASSIGNMENT_AI_API_URL", "https://api.2070814.xyz/v1/chat/completions"),
    "api_key": os.getenv("ASSIGNMENT_AI_API_KEY", ""),
    "model": os.getenv("ASSIGNMENT_AI_MODEL", "gpt-5.5"),
    "server_mode": env_flag("ASSIGNMENT_SERVER_MODE"),
    "headless": env_flag("ASSIGNMENT_HEADLESS", os.getenv("ASSIGNMENT_SERVER_MODE", "false")),
    "browser_channel": os.getenv("ASSIGNMENT_BROWSER_CHANNEL", "chrome"),
    "browser_executable_path": os.getenv("ASSIGNMENT_BROWSER_EXECUTABLE_PATH", ""),
    "timeout_ms": env_int("ASSIGNMENT_TIMEOUT_MS", 15_000),
    "lookup_timeout_ms": env_int("ASSIGNMENT_LOOKUP_TIMEOUT_MS", 12_000),
    "locator_probe_timeout_ms": env_int("ASSIGNMENT_LOCATOR_PROBE_TIMEOUT_MS", 300),
    "locator_retry_interval_seconds": env_float("ASSIGNMENT_LOCATOR_RETRY_INTERVAL_SECONDS", 0.1),
    "action_timeout_ms": env_int("ASSIGNMENT_ACTION_TIMEOUT_MS", 5_000),
    "api_timeout_seconds": env_int("ASSIGNMENT_AI_TIMEOUT_SECONDS", 30),
    "delay_range_seconds": (
        env_float("ASSIGNMENT_MIN_ACTION_DELAY_SECONDS", 0.05),
        env_float("ASSIGNMENT_MAX_ACTION_DELAY_SECONDS", 0.15),
    ),
    "reading_delay_seconds": (
        env_float("ASSIGNMENT_MIN_READING_DELAY_SECONDS", 0.1),
        env_float("ASSIGNMENT_MAX_READING_DELAY_SECONDS", 0.3),
    ),
    "settle_wait_ms": env_int("ASSIGNMENT_SETTLE_WAIT_MS", 300),
    "wait_for_networkidle": env_flag("ASSIGNMENT_WAIT_FOR_NETWORKIDLE", "false"),
    "next_button_timeout_ms": env_int("ASSIGNMENT_NEXT_BUTTON_TIMEOUT_MS", 800),
    "submit_button_timeout_ms": env_int("ASSIGNMENT_SUBMIT_BUTTON_TIMEOUT_MS", 3_000),
    "submit_pre_click_wait_ms": env_int("ASSIGNMENT_SUBMIT_PRE_CLICK_WAIT_MS", 100),
    "submit_after_click_wait_ms": env_int("ASSIGNMENT_SUBMIT_AFTER_CLICK_WAIT_MS", 500),
    "confirmation_initial_wait_ms": env_int("ASSIGNMENT_CONFIRMATION_INITIAL_WAIT_MS", 250),
    "confirmation_timeout_ms": env_int("ASSIGNMENT_CONFIRMATION_TIMEOUT_MS", 800),
    "confirmation_poll_ms": env_int("ASSIGNMENT_CONFIRMATION_POLL_MS", 100),
    "confirmation_candidate_timeout_ms": env_int("ASSIGNMENT_CONFIRMATION_CANDIDATE_TIMEOUT_MS", 100),
    "max_confirmation_rounds": env_int("ASSIGNMENT_MAX_CONFIRMATION_ROUNDS", 3),
    "block_on_incomplete": env_flag("ASSIGNMENT_BLOCK_ON_INCOMPLETE", "false"),
    "incomplete_block_seconds": env_int("ASSIGNMENT_INCOMPLETE_BLOCK_SECONDS", 7200),
    "hold_browser_on_exit": env_flag("ASSIGNMENT_HOLD_BROWSER_ON_EXIT", "false"),
    "max_questions": env_int("ASSIGNMENT_MAX_QUESTIONS", 50),
    "scan_interval_seconds": env_int("ASSIGNMENT_SCAN_INTERVAL_SECONDS", 3600),
    "max_scan_rounds": env_int("ASSIGNMENT_MAX_SCAN_ROUNDS", 0),
    "max_candidates_per_round": env_int("ASSIGNMENT_MAX_CANDIDATES_PER_ROUND", 10),
    "inbox_keywords": ["作业：", "作业:"],
    "dry_run": env_flag("ASSIGNMENT_DRY_RUN", "false"),
    "allow_submission": env_flag("ASSIGNMENT_ALLOW_SUBMISSION", "true"),
    "allow_live_ai_on_real_site": env_flag("ASSIGNMENT_ALLOW_LIVE_AI_ON_REAL_SITE", "true"),
    "allowed_hosts_for_actions": [
        "localhost", "127.0.0.1", "example.test", 
        "chaoxing.com", "mooc1-api.chaoxing.com", "mooc1.chaoxing.com"
    ],
    "allowed_hosts_for_live_ai": [
        "localhost", "127.0.0.1", "example.test", 
        "chaoxing.com", "mooc1-api.chaoxing.com", "mooc1.chaoxing.com"
    ],
    "blocked_real_assignment_hosts": sorted(
        set(env_list("ASSIGNMENT_BLOCKED_REAL_ASSIGNMENT_HOSTS", []))
    ),
    "selectors": {
        "username_input": "#phone",
        "password_input": "#pwd",
        "login_button": "#loginBtn",
        "iframe_roots": ["iframe#iframe", "iframe[name='iframe']", "iframe"],
        "inbox_loaded": "li.dataBody_item, body",
        "inbox_nav_entry": "[title='收件箱'], .label-item:has-text('收件箱'), li:has-text('收件箱')",
        "inbox_item": "li.dataBody_item",
        "inbox_item_title": "a.notice_title",
        "inbox_item_open": ".openNotice",
        "question_container": (
            ".questionLi, .question, .question-item, [data-question-id], .exam-question, "
            ".TiMu, .Py_tk, div:has(.Py_answer)"
        ),
        "question_text": ".mark_name, .Py_tk, .question-title, .question-text, .stem, [data-role='question-text']",
        "option_item": (
            ".answerBg[role='radio'], .answerBg[role='checkbox'], .Py_answer li, .Py_answer .clearfix, .option, .answer-option, "
            "li:has(input[type='radio']), li:has(input[type='checkbox'])"
        ),
        "option_input": "input[type='radio'], input[type='checkbox'], [role='radio'], [role='checkbox']",
        "option_label": "label, .option-text, .answer-text, .Py_answer",
        "text_answer_input": "input[type='text'], textarea",
        "next_button": "button:has-text('下一题'), a:has-text('下一题'), button:has-text('下一步')",
        "submit_button": (
            ".Btn_blue_1:has-text('提交'), a.btnSubmit, "
            "a:has-text('提交'), button:has-text('提交'), input[type='submit']"
        ),
        "confirm_submit_button": (
            ".layui-layer-btn a:has-text('提交'), .layui-layer-btn button:has-text('提交'), "
            ".layui-layer-btn a:has-text('确认提交'), .layui-layer-btn button:has-text('确认提交'), "
            ".layui-layer-btn0, .aui_state_highlight, .layui-layer .bluebtn, "
            ".aui_buttons a:has-text('提交'), .aui_buttons button:has-text('提交'), "
            ".modal-footer button:has-text('提交'), .modal-footer a:has-text('提交'), "
            ".dialog-footer button:has-text('提交'), .dialog-footer a:has-text('提交'), "
            ".el-message-box button:has-text('提交'), .el-message-box button:has-text('确定'), "
            ".dialog-confirm:has-text('提交'), .dialog-confirm:has-text('确定'), "
            ".Btn_blue_1:has-text('提交'), .Btn_blue_1:has-text('确定'), .Btn_blue_1:has-text('确认'), "
            "button:has-text('确认提交'), a:has-text('确认提交'), "
            "button:has-text('确定'), a:has-text('确定'), "
            "button:has-text('确认'), a:has-text('确认'), "
            "button:has-text('提交'), a:has-text('提交'), "
            "[role='button']:has-text('确定'), [role='button']:has-text('确认'), "
            "[role='button']:has-text('提交'), input[type='button'][value='提交'], "
            "input[type='button'][value='确定'], input[type='button'][value='确认'], "
            "input[type='submit'][value='提交'], input[type='submit'][value='确定'], "
            "input[type='submit'][value='确认']"
        ),
    },
}

SYSTEM_PROMPT = (
    "你是一个授权测试环境中的自动化交互决策引擎，请根据题目和选项输出答案，必须严格只返回 JSON 格式。"
    "你是一个大学教授。请先在心里一步步分析每个选项的对错，然后再给出最终的正确选项字母。"
    "选择题返回选项字母，例如单选返回 {\"answer\": [\"A\"]}，多选返回 {\"answer\": [\"A\", \"C\"]}。"
    "如果是填空题或简答题，请直接返回答案文本，例如 {\"answer\": [\"答案文本\"]}。不要包含其他字符。"
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("assignment_tester")


def ask_ai_brain(
    question_text: str,
    options_dict: Dict[str, str],
    question_type: Any = "unknown",
    config: Optional[Dict[str, Any]] = None,
) -> Optional[List[str]]:
    """Ask the configured decision API. Returns None on recoverable failure."""
    if isinstance(question_type, dict) and config is None:
        config = question_type
        question_type = "unknown"
    question_type = str(question_type)
    cfg = config or CONFIG
    headers = {"Content-Type": "application/json"}
    if cfg.get("api_key"):
        headers["Authorization"] = f"Bearer {cfg['api_key']}"

    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {"question_type": question_type, "question": question_text, "options": options_dict},
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0,
    }

    try:
        response = requests.post(
            cfg["api_url"],
            headers=headers,
            json=payload,
            timeout=cfg["api_timeout_seconds"],
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        answers = parsed.get("answer")
        if isinstance(answers, str) and question_type == "text":
            answers = [answers]
        if not isinstance(answers, list):
            raise ValueError("AI response JSON does not contain a list field named 'answer'")
        if question_type == "text":
            normalized = [str(item).strip() for item in answers if str(item).strip()]
        else:
            normalized = [str(item).strip().upper() for item in answers if str(item).strip()]
        return normalized or None
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        LOGGER.warning("AI decision failed; skipping current question. reason=%s", exc)
        return None


class AssignmentAutoTester:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.page: Optional[Page] = None
        self._dialog_auto_accept_page: Optional[Page] = None
        self.browser = None
        self.context = None

    @property
    def selectors(self) -> Dict[str, str]:
        return self.config["selectors"]

    def start_browser(self) -> None:
        self.playwright = sync_playwright().start()
        launch_options: Dict[str, Any] = {"headless": self.config["headless"]}
        if self.config.get("browser_executable_path"):
            launch_options["executable_path"] = self.config["browser_executable_path"]
        elif self.config.get("browser_channel"):
            launch_options["channel"] = self.config["browser_channel"]
        self.browser = self.playwright.chromium.launch(**launch_options)
        self.context = self.browser.new_context(viewport={"width": 1366, "height": 768}, locale="zh-CN")
        self.page = self.context.new_page()
        self.page.set_default_timeout(self.config["timeout_ms"])
        self.ensure_dialog_auto_accept()

    def ensure_dialog_auto_accept(self) -> None:
        if not self.page or self._dialog_auto_accept_page is self.page:
            return
        self.page.on("dialog", self.accept_browser_dialog)
        self._dialog_auto_accept_page = self.page

    def accept_browser_dialog(self, dialog: Any) -> None:
        LOGGER.info("[Action] 处理确认弹窗: %s", dialog.message)
        try:
            dialog.accept()
        except PlaywrightError as exc:
            LOGGER.warning("[Action] 处理确认弹窗失败: %s", exc)

    def close(self) -> None:
        for resource in (self.context, self.browser):
            if resource:
                try:
                    resource.close()
                except PlaywrightError as exc:
                    LOGGER.warning("Failed closing resource: %s", exc)
        if hasattr(self, "playwright"):
            self.playwright.stop()

    def random_delay(self) -> None:
        low, high = self.config["delay_range_seconds"]
        if low > high:
            low, high = high, low
        if high <= 0:
            return
        delay = random.uniform(low, high)
        LOGGER.info("Interaction delay %.2fs", delay)
        time.sleep(delay)

    def reading_delay(self) -> None:
        low, high = self.config["reading_delay_seconds"]
        if low > high:
            low, high = high, low
        if high <= 0:
            return
        delay = random.uniform(low, high)
        LOGGER.info("Reading delay %.2fs before next/submit", delay)
        time.sleep(delay)

    def find_locator(
        self,
        selector: str,
        state: str = "visible",
        timeout_ms: Optional[int] = None,
        log_missing: bool = True,
    ) -> Optional[Locator]:
        if not self.page:
            return None

        deadline = time.monotonic() + (timeout_ms or self.config["lookup_timeout_ms"]) / 1000
        probe_timeout_ms = max(50, int(self.config.get("locator_probe_timeout_ms", 300)))
        retry_interval = max(0.02, float(self.config.get("locator_retry_interval_seconds", 0.1)))
        last_frame_count = 0
        while time.monotonic() < deadline:
            frames = self.page.frames
            last_frame_count = len(frames)
            candidates = [self.page.locator(selector).first]
            candidates.extend(frame.locator(selector).first for frame in frames)
            for iframe_selector in self.selectors.get("iframe_roots", []):
                try:
                    candidates.append(self.page.frame_locator(iframe_selector).locator(selector).first)
                except PlaywrightError:
                    continue

            for candidate in candidates:
                try:
                    remaining_ms = int((deadline - time.monotonic()) * 1000)
                    if remaining_ms <= 0:
                        break
                    candidate.wait_for(state=state, timeout=min(probe_timeout_ms, remaining_ms))
                    return candidate
                except (PlaywrightTimeoutError, PlaywrightError):
                    continue
            time.sleep(retry_interval)

        if log_missing:
            LOGGER.warning(
                "Element not found: %s url=%s frames=%s",
                selector,
                self.page.url if self.page else "",
                last_frame_count,
            )
        return None

    def find_all_locators(self, selector: str, timeout_ms: Optional[int] = None) -> List[Locator]:
        if not self.page:
            return []

        deadline = time.monotonic() + (timeout_ms or self.config["lookup_timeout_ms"]) / 1000
        retry_interval = max(0.02, float(self.config.get("locator_retry_interval_seconds", 0.1)))
        while time.monotonic() < deadline:
            for root in [self.page, *self.page.frames]:
                try:
                    locator = root.locator(selector)
                    if locator.count() > 0:
                        return locator.all()
                except PlaywrightError:
                    continue
            time.sleep(retry_interval)
        return []

    def safe_click(self, target: Optional[Locator], description: str) -> bool:
        if not target:
            return False
        try:
            action_timeout_ms = self.config.get("action_timeout_ms", 5_000)
            target.wait_for(state="visible", timeout=action_timeout_ms)
            self.random_delay()
            target.click(timeout=action_timeout_ms)
            LOGGER.info("Clicked %s", description)
            return True
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            LOGGER.warning("Click failed: %s reason=%s", description, exc)
            return False

    def safe_fill(self, selector: str, value: str, description: str) -> bool:
        if not value:
            LOGGER.warning("Missing config value for %s", description)
            return False
        target = self.find_locator(selector)
        if not target:
            return False
        try:
            self.random_delay()
            target.fill(value, timeout=self.config.get("action_timeout_ms", 5_000))
            LOGGER.info("Filled %s", description)
            return True
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            LOGGER.warning("Fill failed: %s reason=%s", description, exc)
            return False

    def login(self) -> bool:
        if not self.page:
            return False
        try:
            self.page.goto(self.config["login_url"], wait_until="domcontentloaded")
            LOGGER.info("Opened login page")
        except PlaywrightError as exc:
            LOGGER.error("Open login page failed: %s", exc)
            return False

        if not self.safe_fill(self.selectors["username_input"], self.config["username"], "username"):
            return False
        if not self.safe_fill(self.selectors["password_input"], self.config["password"], "password"):
            return False
        if not self.safe_click(self.find_locator(self.selectors["login_button"]), "login button"):
            return False
        try:
            self.page.wait_for_url("**://i.chaoxing.com/**", timeout=self.config["timeout_ms"])
        except PlaywrightTimeoutError:
            LOGGER.info("Login did not visibly reach i.chaoxing.com before timeout; continuing with explicit Inbox navigation.")
        self.wait_for_page_settle("after login")
        return True

    def open_inbox(self) -> bool:
        if not self.page:
            return False
        try:
            for attempt in range(1, 3):
                try:
                    self.page.goto(self.config["inbox_url"], wait_until="domcontentloaded")
                    self.wait_for_page_settle("inbox direct url")
                    if not self.find_locator(
                        self.selectors["inbox_item_title"],
                        state="attached",
                        timeout_ms=3_000,
                        log_missing=False,
                    ):
                        inbox_nav = self.find_locator(
                            self.selectors["inbox_nav_entry"],
                            timeout_ms=8_000,
                            log_missing=False,
                        )
                        if inbox_nav:
                            self.safe_click(inbox_nav, "inbox navigation entry")
                            self.wait_for_page_settle("inbox navigation entry")
                    self.find_locator(self.selectors["inbox_loaded"], timeout_ms=8_000, log_missing=False)
                    LOGGER.info("Opened inbox via forced URL: %s", self.config["inbox_url"])
                    return True
                except PlaywrightError as exc:
                    LOGGER.warning("Forced inbox URL attempt %s failed: %s", attempt, exc)
                    time.sleep(2)
        except PlaywrightError as exc:
            LOGGER.warning("Forced inbox URL failed: %s", exc)
            return False
        return False

    def scan_inbox(self) -> List[Dict[str, str]]:
        """Scan Inbox only. Does not leave the Inbox path or submit real work."""
        LOGGER.info("开始扫描: %s", time.strftime("%Y-%m-%d %H:%M:%S"))
        if not self.open_inbox():
            LOGGER.warning("Inbox 打开失败，本轮扫描结束。")
            return []

        items = self.find_all_locators(self.selectors["inbox_item"], timeout_ms=8_000)
        candidates: List[Dict[str, str]] = []
        for index, item in enumerate(items, start=1):
            try:
                title = item.locator(self.selectors["inbox_item_title"]).first
                title_text = title.inner_text(timeout=2_000).strip()
            except (PlaywrightTimeoutError, PlaywrightError):
                continue

            if not self.is_inbox_candidate(title_text):
                continue

            href = ""
            try:
                open_notice = item.locator(self.selectors["inbox_item_open"]).first
                href = open_notice.get_attribute("data-url") or title.get_attribute("href") or ""
            except (PlaywrightTimeoutError, PlaywrightError):
                href = ""
            if href.strip() in {"", "#"} or href.lower().startswith("javascript:"):
                href = ""
            elif href.startswith("/"):
                href = f"https://notice.chaoxing.com{href}"

            candidates.append({"index": str(index), "title": title_text, "text": title_text, "href": href})

        LOGGER.info("扫描结果: %s 条作业候选", len(candidates))
        for candidate in candidates:
            LOGGER.info(
                "[Found] 作业：#%s href=%s title=%s",
                candidate["index"],
                candidate["href"] or "<no href>",
                candidate["title"][:120].replace("\n", " "),
            )
        return candidates

    def is_inbox_candidate(self, text: str) -> bool:
        normalized = re.sub(r"\s+", "", text)
        return any(keyword in normalized for keyword in self.config["inbox_keywords"])

    def process_inbox_candidate(self, candidate: Dict[str, str]) -> bool:
        if not self.page:
            return False

        href = candidate.get("href", "")
        inbox_url = self.page.url
        LOGGER.info("开始处理 Inbox 作业候选: %s", time.strftime("%Y-%m-%d %H:%M:%S"))
        if not href:
            if not self.click_inbox_candidate_by_index(candidate.get("index", "")):
                LOGGER.warning("Inbox 候选没有 href，且无法点击，跳过。")
                return False
            LOGGER.info("Opened inbox candidate by clicking current Inbox item: %s", self.page.url)
        else:
            try:
                self.page.goto(href, wait_until="domcontentloaded")
                self.wait_for_page_settle("inbox candidate page")
                LOGGER.info("Opened inbox candidate page: %s", self.page.url)
            except PlaywrightError as exc:
                LOGGER.warning("Failed to open inbox candidate href=%s reason=%s", href, exc)
                return False

        extracted = self.extract_question()
        if not extracted and self.open_notice_assignment_attachment():
            extracted = self.extract_question()

        if not extracted:
            if self.is_completed_or_closed_page():
                LOGGER.info("Detected completed/closed assignment page; skipping candidate gracefully.")
            else:
                LOGGER.info("No question DOM found on inbox candidate page; skipping candidate gracefully.")
            return False

        result = self.process_all_questions(first_extracted=extracted)
        LOGGER.info("完成做题 dry-run: %s result=%s", time.strftime("%Y-%m-%d %H:%M:%S"), result)
        try:
            self.page.goto(inbox_url, wait_until="domcontentloaded")
            self.wait_for_page_settle("return to inbox")
        except PlaywrightError as exc:
            LOGGER.warning("Failed returning to inbox url=%s reason=%s", inbox_url, exc)
        return result

    def open_notice_assignment_attachment(self) -> bool:
        if not self.page:
            return False

        for frame in self.page.frames:
            try:
                attachment_url = frame.evaluate(
                    """() => {
                        const attWebUrl = window.att_web && window.att_web.url;
                        const screenOpenUrl = window.screenOpenUrl;
                        return attWebUrl || screenOpenUrl || "";
                    }"""
                )
            except PlaywrightError:
                continue

            if not isinstance(attachment_url, str) or not attachment_url.startswith("http"):
                continue

            LOGGER.info("Found notice assignment attachment URL: %s", attachment_url)
            try:
                self.page.goto(attachment_url, wait_until="domcontentloaded")
                self.wait_for_page_settle("notice assignment attachment")
                LOGGER.info("Opened notice assignment attachment: %s", self.page.url)
                return True
            except PlaywrightError as exc:
                LOGGER.warning("Failed opening notice assignment attachment: %s", exc)
                return False
        return False

    def click_inbox_candidate_by_index(self, index_value: str) -> bool:
        if not self.page:
            return False
        try:
            index = int(index_value) - 1
        except ValueError:
            return False

        for root in [self.page, *self.page.frames]:
            try:
                items = root.locator(self.selectors["inbox_item"])
                if items.count() <= index:
                    continue
                item = items.nth(index)
                target = item.locator(self.selectors["inbox_item_open"]).first
                if self.safe_click(target, f"inbox candidate #{index_value}"):
                    self.wait_for_page_settle(f"inbox candidate #{index_value}")
                    return True
            except (PlaywrightTimeoutError, PlaywrightError) as exc:
                LOGGER.warning("Failed clicking inbox candidate #%s in one root: %s", index_value, exc)
        return False

    def is_completed_or_closed_page(self) -> bool:
        if not self.page:
            return False

        keywords = ("已完成", "已提交", "已批阅", "作业已完成", "已结束", "暂无可做", "不能作答")
        roots = [self.page, *self.page.frames]
        for root in roots:
            try:
                body_text = root.locator("body").inner_text(timeout=2_000)
            except (PlaywrightTimeoutError, PlaywrightError):
                continue
            normalized = re.sub(r"\s+", "", body_text)
            if any(keyword in normalized for keyword in keywords):
                return True
        return False

    def current_question_container(self) -> Optional[Locator]:
        priority_selectors = [
            ".questionLi",
            ".question",
            ".question-item",
            "[data-question-id]",
            ".exam-question",
            ".Py_tk",
            "div:has(.Py_answer)",
            ".TiMu",
        ]
        for selector in priority_selectors:
            found = self.find_locator(selector, timeout_ms=4_000, log_missing=False)
            if found:
                return found
        LOGGER.warning(
            "Element not found: %s url=%s frames=%s",
            self.selectors["question_container"],
            self.page.url if self.page else "",
            len(self.page.frames) if self.page else 0,
        )
        return None

    def all_question_containers(self) -> List[Locator]:
        if not self.page:
            return []

        for selector in [".questionLi", ".question", ".question-item", "[data-question-id]", ".exam-question"]:
            containers = self.find_all_locators(selector, timeout_ms=4_000)
            if containers:
                return containers[: self.config["max_questions"]]
        current = self.current_question_container()
        return [current] if current else []

    def extract_question(self) -> Optional[Tuple[str, Dict[str, str], str, Dict[str, Locator]]]:
        container = self.current_question_container()
        if not container:
            return None
        return self.extract_question_from_container(container)

    def extract_question_from_container(
        self,
        container: Locator,
    ) -> Optional[Tuple[str, Dict[str, str], str, Dict[str, Locator]]]:
        try:
            question_text = container.locator(self.selectors["question_text"]).first.inner_text(timeout=2_000).strip()
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            try:
                question_text = container.inner_text(timeout=2_000).strip()
            except (PlaywrightTimeoutError, PlaywrightError) as inner_exc:
                LOGGER.warning("Question extraction failed: %s / %s", exc, inner_exc)
                return None

        option_items = container.locator(self.selectors["option_item"]).all()
        if not option_items:
            text_control = self.find_text_answer_control(container)
            if text_control:
                LOGGER.info("[探测到简答题] found text input control")
                return question_text, {}, "text", {"__text__": text_control}
            option_items = self.find_all_locators(self.selectors["option_item"], timeout_ms=3_000)

        options: Dict[str, str] = {}
        controls: Dict[str, Locator] = {}
        question_type = "unknown"

        for index, item in enumerate(option_items):
            letter = chr(ord("A") + index)
            try:
                item_role = (item.get_attribute("role") or "").lower()
                if item_role in {"radio", "checkbox"}:
                    control = item
                    input_type = item_role
                else:
                    control = item.locator(self.selectors["option_input"]).first
                    input_type = (control.get_attribute("type") or control.get_attribute("role") or "").lower()
                label = self.extract_option_text(item, letter)
            except (PlaywrightTimeoutError, PlaywrightError) as exc:
                LOGGER.warning("Option extraction failed at %s: %s", letter, exc)
                continue

            if input_type == "radio":
                question_type = "single"
            elif input_type == "checkbox":
                question_type = "multiple"
            options[letter] = label
            controls[letter] = control

        if not question_text or not options:
            LOGGER.warning("Incomplete question data; skipping")
            return None
        LOGGER.info("Extracted %s question with options=%s", question_type, list(options.keys()))
        return question_text, options, question_type, controls

    def find_text_answer_control(self, container: Locator) -> Optional[Locator]:
        try:
            controls = container.locator(self.selectors["text_answer_input"]).all()
        except PlaywrightError:
            return None

        for control in controls:
            try:
                input_type = (control.get_attribute("type") or "").lower()
                if input_type in {"hidden", "submit", "button", "checkbox", "radio"}:
                    continue
                if control.is_visible():
                    return control
            except PlaywrightError:
                continue
        return controls[0] if controls else None

    def extract_option_text(self, item: Locator, letter: str) -> str:
        try:
            role = (item.get_attribute("role") or "").lower()
            class_name = item.get_attribute("class") or ""
            if role in {"radio", "checkbox"} or "answerBg" in class_name:
                label = item.inner_text(timeout=1_000).strip()
                return re.sub(rf"^\s*{letter}\s*[:：.、]?\s*", "", label, flags=re.IGNORECASE)
        except (PlaywrightTimeoutError, PlaywrightError):
            pass

        try:
            label = item.locator(self.selectors["option_label"]).first.inner_text(timeout=2_000).strip()
        except (PlaywrightTimeoutError, PlaywrightError):
            label = item.inner_text(timeout=2_000).strip()
        return re.sub(rf"^\s*{letter}\s*[:：.、]?\s*", "", label, flags=re.IGNORECASE)

    def actions_allowed(self) -> bool:
        if self.config["dry_run"]:
            return False
        if not self.page:
            return False
        hostname = urlparse(self.page.url).hostname or ""
        if self.is_blocked_real_assignment_host(hostname):
            LOGGER.warning("Real assignment host is blocked for answer clicks/submission: %s", hostname)
            return False
        allowed_hosts = self.config.get("allowed_hosts_for_actions", [])
        return any(hostname == allowed or hostname.endswith(f".{allowed}") for allowed in allowed_hosts)

    def apply_answers(self, answers: List[str], controls: Dict[str, Locator]) -> bool:
        selected_any = False
        for letter in answers:
            control = controls.get(letter)
            if not control:
                LOGGER.warning("AI answer %s has no matching option control", letter)
                continue
            if not self.actions_allowed():
                LOGGER.info("Dry-run: would click answer %s", letter)
                selected_any = True
                continue
            selected_any = self.safe_click(control, f"answer {letter}") or selected_any
        return selected_any

    def apply_text_answer(self, answer_text: str, controls: Dict[str, Locator]) -> bool:
        answer_text = answer_text.strip()
        if not answer_text:
            LOGGER.warning("Text answer is empty; skipping text input.")
            return False

        control = controls.get("__text__")
        if not control:
            LOGGER.warning("Text question has no input control; skipping text answer.")
            return False

        LOGGER.info("[探测到简答题] 准备填入内容：%s", answer_text)
        if not self.actions_allowed():
            return True

        try:
            self.random_delay()
            control.fill(answer_text, timeout=self.config.get("action_timeout_ms", 5_000))
            LOGGER.info("Filled text answer")
            return True
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            LOGGER.warning("Fill text answer failed: %s", exc)
            return False

    def click_next_or_submit(self) -> bool:
        self.reading_delay()
        if not self.actions_allowed() or not self.config["allow_submission"]:
            LOGGER.info("Dry-run: would click next/submit")
            return True

        next_button = self.find_locator(
            self.selectors["next_button"],
            timeout_ms=self.config.get("next_button_timeout_ms", 800),
            log_missing=False,
        )
        if next_button and self.safe_click(next_button, "next question"):
            self.wait_for_page_settle("next question")
            return True

        return self.submit_current_page()

    def submit_current_page(self) -> bool:
        if not self.page:
            raise RuntimeError("Cannot submit without an initialized page.")
        if not self.actions_allowed() or not self.config["allow_submission"]:
            LOGGER.info("Dry-run: would click submit")
            return True

        LOGGER.info("[Action] 正在定位提交按钮...")
        submit_button = self.find_locator(
            self.selectors["submit_button"],
            state="visible",
            timeout_ms=self.config.get("submit_button_timeout_ms", 3_000),
            log_missing=False,
        )
        if not submit_button:
            raise RuntimeError(f"Submit button not found: {self.selectors['submit_button']}")

        try:
            self.ensure_dialog_auto_accept()
            action_timeout_ms = self.config.get("action_timeout_ms", 5_000)
            submit_button.scroll_into_view_if_needed(timeout=action_timeout_ms)
            submit_button_box = submit_button.bounding_box(timeout=1_000)
            self.page.wait_for_timeout(max(0, int(self.config.get("submit_pre_click_wait_ms", 100))))
            LOGGER.info("[Action] 点击提交...")
            submit_button.click(timeout=action_timeout_ms)
            self.handle_custom_submit_confirmation(skip_box=submit_button_box)
            self.page.wait_for_timeout(max(0, int(self.config.get("submit_after_click_wait_ms", 500))))
            LOGGER.info("[Action] 提交动作已完成，等待页面稳定...")
            self.wait_for_page_settle("submit")
            return True
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            raise RuntimeError(f"Submit action failed: {exc}") from exc

    def handle_custom_submit_confirmation(
        self,
        skip_box: Optional[Dict[str, float]] = None,
        max_rounds: Optional[int] = None,
    ) -> bool:
        if not self.page:
            return False

        max_rounds = max_rounds or int(self.config.get("max_confirmation_rounds", 3))
        clicked_any = False
        for round_index in range(1, max_rounds + 1):
            LOGGER.info("[Action] 处理提交确认弹窗 %s/%s...", round_index, max_rounds)
            self.page.wait_for_timeout(max(0, int(self.config.get("confirmation_initial_wait_ms", 250))))
            confirm_button = self.find_visible_confirmation_button(
                skip_box=skip_box,
                timeout_ms=int(self.config.get("confirmation_timeout_ms", 800)),
            )
            if not confirm_button:
                if clicked_any:
                    LOGGER.info("[Action] 未检测到更多提交确认按钮。")
                else:
                    LOGGER.info("[Action] 未检测到自定义确认按钮，可能已由 JS dialog 监听处理。")
                return clicked_any

            try:
                action_timeout_ms = self.config.get("action_timeout_ms", 5_000)
                confirm_button.scroll_into_view_if_needed(timeout=action_timeout_ms)
                confirm_button.click(timeout=action_timeout_ms)
                clicked_any = True
                LOGGER.info("[Action] 已点击第 %s 层提交/确认按钮。", round_index)
            except (PlaywrightTimeoutError, PlaywrightError) as exc:
                raise RuntimeError(f"Confirm submit action failed: {exc}") from exc

        return clicked_any

    def find_visible_confirmation_button(
        self,
        skip_box: Optional[Dict[str, float]] = None,
        timeout_ms: int = 4_000,
    ) -> Optional[Locator]:
        if not self.page:
            return None

        selectors = [
            selector.strip()
            for selector in self.selectors["confirm_submit_button"].split(",")
            if selector.strip()
        ]
        deadline = time.monotonic() + timeout_ms / 1000
        poll_ms = max(50, int(self.config.get("confirmation_poll_ms", 100)))
        candidate_timeout_ms = max(50, int(self.config.get("confirmation_candidate_timeout_ms", 100)))
        while time.monotonic() < deadline:
            roots = [self.page, *self.page.frames]
            for selector in selectors:
                for root in roots:
                    try:
                        locator = root.locator(selector)
                        count = min(locator.count(), 20)
                    except PlaywrightError:
                        continue

                    for index in range(count - 1, -1, -1):
                        candidate = locator.nth(index)
                        try:
                            remaining_ms = int((deadline - time.monotonic()) * 1000)
                            if remaining_ms <= 0:
                                break
                            timeout = min(candidate_timeout_ms, remaining_ms)
                            candidate.wait_for(state="visible", timeout=timeout)
                            if not candidate.is_enabled(timeout=timeout):
                                continue
                            if skip_box and self.matches_box(candidate, skip_box):
                                continue
                            return candidate
                        except (PlaywrightTimeoutError, PlaywrightError):
                            continue
            self.page.wait_for_timeout(poll_ms)
        return None

    def matches_box(self, locator: Locator, reference_box: Dict[str, float]) -> bool:
        try:
            box = locator.bounding_box(timeout=max(50, int(self.config.get("confirmation_candidate_timeout_ms", 100))))
        except (PlaywrightTimeoutError, PlaywrightError):
            return False
        if not box:
            return False
        return all(abs(float(box[key]) - float(reference_box[key])) < 1 for key in ("x", "y", "width", "height"))

    def process_current_question(
        self,
        extracted: Optional[Tuple[str, Dict[str, str], str, Dict[str, Locator]]] = None,
    ) -> bool:
        extracted = extracted or self.extract_question()
        if not extracted:
            return False

        question_text, options, question_type, controls = extracted
        LOGGER.info("Question type=%s text=%s", question_type, question_text[:80])
        answers = self.decide_answers(question_text, options, question_type)
        if not answers:
            LOGGER.warning("No usable AI answer; skipping question")
            return self.click_next_or_submit()

        if question_type == "text":
            self.apply_text_answer(answers[0], controls)
        else:
            self.apply_answers(answers, controls)
        return self.click_next_or_submit()

    def process_all_questions(
        self,
        first_extracted: Optional[Tuple[str, Dict[str, str], str, Dict[str, Locator]]] = None,
    ) -> bool:
        containers = self.all_question_containers()
        if not containers:
            if not first_extracted:
                return False
            containers = []

        processed = 0
        selected = 0
        if first_extracted and not containers:
            containers_to_process: List[Optional[Locator]] = [None]
        else:
            containers_to_process = containers

        for index, container in enumerate(containers_to_process, start=1):
            if index > self.config["max_questions"]:
                LOGGER.info("Reached max_questions=%s; stopping question loop.", self.config["max_questions"])
                break

            extracted = first_extracted if container is None else self.extract_question_from_container(container)
            first_extracted = None
            if not extracted:
                LOGGER.warning("Question #%s extraction failed; skipping.", index)
                continue

            question_text, options, question_type, controls = extracted
            processed += 1
            LOGGER.info("Question #%s type=%s text=%s", index, question_type, question_text[:80])
            answers = self.decide_answers(question_text, options, question_type)
            if not answers:
                LOGGER.warning("Question #%s has no usable answer; skipping.", index)
                continue
            if question_type == "text":
                applied = self.apply_text_answer(answers[0], controls)
            else:
                applied = self.apply_answers(answers, controls)
            if applied:
                selected += 1

        LOGGER.info("Processed %s question(s); selected/mapped %s question(s).", processed, selected)
        if selected < processed:
            LOGGER.warning("Question loop incomplete: processed=%s selected_or_mapped=%s", processed, selected)
            if self.config.get("block_on_incomplete"):
                print("\n" + "=" * 60)
                print("检测到漏答，已按 ASSIGNMENT_BLOCK_ON_INCOMPLETE=true 暂停。")
                print("请在浏览器中手动检查后再继续。")
                print("=" * 60 + "\n")
                time.sleep(max(0, int(self.config.get("incomplete_block_seconds", 7200))))
                return False
        if processed == 0:
            return False
        return self.click_next_or_submit()

    def decide_answers(self, question_text: str, options: Dict[str, str], question_type: str) -> Optional[List[str]]:
        if self.live_ai_allowed():
            return ask_ai_brain(question_text, options, question_type, self.config)

        first_option = next(iter(options), None)
        if question_type == "text":
            LOGGER.info(
                "Dry-run real-site mode: live AI disabled; would send text question to AI in authorized staging. "
                "Using deterministic placeholder text for fill-path test."
            )
            return ["dry-run text answer placeholder"]
        if first_option:
            LOGGER.info(
                "Dry-run real-site mode: live AI disabled; would send question to AI in authorized staging. "
                "Using deterministic mock answer %s for mapping test.",
                first_option,
            )
            return [first_option]
        return None

    def live_ai_allowed(self) -> bool:
        if not self.page:
            return False
        hostname = urlparse(self.page.url).hostname or ""
        if self.is_blocked_real_assignment_host(hostname):
            LOGGER.info("Live AI disabled on real assignment host: %s", hostname)
            return False
        if self.config.get("allow_live_ai_on_real_site"):
            return True
        allowed_hosts = self.config.get("allowed_hosts_for_live_ai", [])
        return any(hostname == allowed or hostname.endswith(f".{allowed}") for allowed in allowed_hosts)

    def is_blocked_real_assignment_host(self, hostname: str) -> bool:
        blocked_hosts = self.config.get("blocked_real_assignment_hosts", [])
        return any(hostname == blocked or hostname.endswith(f".{blocked}") for blocked in blocked_hosts)

    def wait_for_page_settle(self, description: str) -> None:
        if not self.page:
            return
        if self.config.get("wait_for_networkidle"):
            try:
                self.page.wait_for_load_state("networkidle", timeout=self.config["timeout_ms"])
                return
            except PlaywrightTimeoutError:
                LOGGER.info("%s did not reach networkidle; continuing", description)
        settle_wait_ms = max(0, int(self.config.get("settle_wait_ms", 300)))
        if settle_wait_ms:
            self.page.wait_for_timeout(settle_wait_ms)

    def run_monitor(self) -> None:
        rounds_completed = 0
        try:
            self.start_browser()
            if not self.login():
                return

            while True:
                rounds_completed += 1
                LOGGER.info("Monitor scan round %s started at %s", rounds_completed, time.strftime("%Y-%m-%d %H:%M:%S"))
                candidates = self.scan_inbox()
                if not candidates:
                    LOGGER.info("扫描完毕，暂无作业，准备休眠")
                max_candidates = self.config.get("max_candidates_per_round", 0)
                candidates_to_process = candidates[:max_candidates] if max_candidates else candidates
                if max_candidates and len(candidates) > max_candidates:
                    LOGGER.info(
                        "Limiting this scan to %s candidate(s); %s remaining candidate(s) left untouched.",
                        max_candidates,
                        len(candidates) - max_candidates,
                    )
                for candidate in candidates_to_process:
                    self.process_inbox_candidate(candidate)
                # ... 前面的代码不变 ...
                LOGGER.info("Monitor scan round %s completed at %s", rounds_completed, time.strftime("%Y-%m-%d %H:%M:%S"))

                max_rounds = self.config.get("max_scan_rounds", 0)
                if max_rounds and rounds_completed >= max_rounds:
                    LOGGER.info("Reached max_scan_rounds=%s; exiting monitor.", max_rounds)
                    
                    # 👉 核心拦截逻辑加在这里：在退出(return)前拦住它！
                    if self.config.get("hold_browser_on_exit") and not self.config.get("allow_submission"):
                        print("\n" + "="*50)
                        print("👉 答题已完成，浏览器已悬停！")
                        print("请在网页上手动检查 AI 填写的答案。")
                        print("确认无误后，请自己点击网页上的【提交作业】按钮。")
                        print("="*50 + "\n")
                        input("按回车键 (Enter) 结束程序并关闭浏览器...") 
                        
                    return

                interval = self.config["scan_interval_seconds"]
                LOGGER.info("Sleeping %s seconds before next inbox scan.", interval)
                time.sleep(interval)
                
        except KeyboardInterrupt:
            LOGGER.info("Monitor interrupted by user")
        except Exception as exc:
            LOGGER.exception("Unexpected monitor error: %s", exc)
        finally:
            # 只有你按了回车，程序才会走到这里关掉浏览器
            self.close()

if __name__ == "__main__":
    AssignmentAutoTester(CONFIG).run_monitor()
