from __future__ import annotations

import argparse
import os
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

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


CONFIG: Dict[str, Any] = {
    # 账号和密码从本地 .env 或环境变量读取，避免把真实凭据写入代码。
    "login_url": os.getenv(
        "CX_LOGIN_URL",
        "https://passport2.chaoxing.com/login?fid=&newversion=true&refer=https%3A%2F%2Fi.chaoxing.com",
    ),
    "username": os.getenv("CX_USERNAME", ""),
    "password": os.getenv("CX_PASSWORD", ""),
    "course_keyword": os.getenv("CX_COURSE_KEYWORD", "“四史”专题课"),
    "chapter_keyword": os.getenv("CX_CHAPTER_KEYWORD", ""),
    "playback_rate": env_float("CX_PLAYBACK_RATE", 2.0),
    "browser_channel": os.getenv("CX_BROWSER_CHANNEL", ""),
    "browser_executable_path": os.getenv("CX_BROWSER_EXECUTABLE_PATH", ""),
    "headless": env_flag("CX_HEADLESS"),
    "slow_mo_ms": env_int("CX_SLOW_MO_MS", 100),
    "timeout_ms": env_int("CX_TIMEOUT_MS", 15_000),
    "lookup_timeout_ms": env_int("CX_LOOKUP_TIMEOUT_MS", 30_000),
    "delay_range_seconds": (
        env_float("CX_MIN_ACTION_DELAY_SECONDS", 2.0),
        env_float("CX_MAX_ACTION_DELAY_SECONDS", 5.0),
    ),
    "progress_poll_seconds": env_float("CX_PROGRESS_POLL_SECONDS", 10.0),
    "progress_min_poll_seconds": env_float("CX_PROGRESS_MIN_POLL_SECONDS", 0.5),
    "progress_completion_margin_seconds": env_float("CX_PROGRESS_COMPLETION_MARGIN_SECONDS", 0.8),
    "progress_stall_polls": env_int("CX_PROGRESS_STALL_POLLS", 3),
    "progress_stall_epsilon_seconds": env_float("CX_PROGRESS_STALL_EPSILON_SECONDS", 0.5),
    "max_video_wait_seconds": env_int("CX_MAX_VIDEO_WAIT_SECONDS", 6 * 60 * 60),
    "max_chapters": env_int("CX_MAX_CHAPTERS", 100),
    "stop_when_no_next": env_flag("CX_STOP_WHEN_NO_NEXT", "true"),
    "auto_commitment": env_flag("CX_AUTO_COMMITMENT", "true"),
    "commitment_timeout_ms": env_int("CX_COMMITMENT_TIMEOUT_MS", 10_000),
    "next_navigation_timeout_ms": env_int("CX_NEXT_NAVIGATION_TIMEOUT_MS", 10_000),
    "courseware_hold_seconds": env_float("CX_COURSEWARE_HOLD_SECONDS", 1.0),
    "completion_settle_seconds": env_float("CX_COMPLETION_SETTLE_SECONDS", 5.0),
    "video_initial_wait_seconds": env_float("CX_VIDEO_INITIAL_WAIT_SECONDS", 12.0),
    "screenshot_dir": os.getenv("CX_SCREENSHOT_DIR", "logs/screenshots"),
    "selectors": {
        "username_input": "#phone",
        "password_input": "#pwd",
        "login_button": "#loginBtn",
        # 支持 {course_keyword} 占位符；真实站点建议替换成更稳定的卡片选择器。
        "course_card": ".course-info a:has-text(\"{course_keyword}\"), .course_name:has-text(\"{course_keyword}\"), a.color1:has-text(\"{course_keyword}\"), h3:has-text(\"{course_keyword}\"), span:has-text(\"{course_keyword}\"), a:has-text(\"{course_keyword}\")",
        "chapters_tab": "#nav_7061, li:has-text('章节')",
        "commitment_modal": "#showCommitmentId, .commitment-content-dialog",
        "commitment_checkbox": "text=我已完整知晓并自愿遵守上述内容",
        "commitment_start": "a.agreeStart, .agreeStart, a:has-text('开始学习')",
        "chapter_item": ".chapter_item[onclick*='toOld']",
        "video": "video",
        "learning_content": "video, iframe, embed, object, .ans-attach-online, .ans-job-icon",
        "courseware_open": (
            "a:has-text('课件'), button:has-text('课件'), "
            "a:has-text('查看'), button:has-text('查看'), "
            "a:has-text('预览'), button:has-text('预览'), "
            "a:has-text('打开'), button:has-text('打开'), "
            ".ans-attach-online, .ans-job-icon, .file-name, .resource, .courseware"
        ),
        "next_chapter": (
            ".prev_next.next, div.next:has-text('下一节'), "
            "button:has-text('下一章'), a:has-text('下一章'), "
            "button:has-text('下一节'), a:has-text('下一节'), "
            "a:has-text('下一任务点'), button:has-text('下一任务点')"
        ),
    },
}


class CourseAutoTester:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.page: Optional[Page] = None
        self.browser = None
        self.context = None
        self.visited_urls: set[str] = set()

    @property
    def selectors(self) -> Dict[str, str]:
        return self.config["selectors"]

    def random_delay(self) -> None:
        min_seconds, max_seconds = self.config["delay_range_seconds"]
        if min_seconds > max_seconds:
            min_seconds, max_seconds = max_seconds, min_seconds
        delay = random.uniform(min_seconds, max_seconds)
        print(f"等待 {delay:.1f} 秒...")
        time.sleep(delay)

    def start_browser(self) -> None:
        self.playwright = sync_playwright().start()
        launch_options: Dict[str, Any] = {
            "headless": self.config["headless"],
            "slow_mo": self.config["slow_mo_ms"],
        }
        if self.config.get("browser_executable_path"):
            launch_options["executable_path"] = self.config["browser_executable_path"]
        elif self.config.get("browser_channel"):
            launch_options["channel"] = self.config["browser_channel"]
        self.browser = self.playwright.chromium.launch(**launch_options)
        self.context = self.browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="zh-CN",
        )
        self.page = self.context.new_page()
        self.page.set_default_timeout(self.config["timeout_ms"])

    def close(self) -> None:
        for resource in (self.context, self.browser):
            if resource:
                try:
                    resource.close()
                except PlaywrightError as exc:
                    print(f"关闭资源时出现异常: {exc}")
        if hasattr(self, "playwright"):
            self.playwright.stop()

    def save_debug_screenshot(self, label: str) -> None:
        if not self.page:
            return

        try:
            screenshot_dir = Path(self.config["screenshot_dir"])
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            safe_label = "".join(char if char.isalnum() else "_" for char in label).strip("_") or "debug"
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            path = screenshot_dir / f"{timestamp}_{safe_label}.png"
            self.page.screenshot(path=str(path), full_page=True)
            print(f"已保存调试截图: {path}")
        except (OSError, PlaywrightError) as exc:
            print(f"保存调试截图失败 [{label}]: {exc}")

    def locator(self, selector: str, **values: str) -> Locator:
        if not self.page:
            raise RuntimeError("浏览器页面尚未初始化")
        resolved = selector.format(**values)
        return self.page.locator(resolved).first

    def course_keyword_terms(self, keyword: str) -> list[str]:
        terms: list[str] = []

        def add(term: str) -> None:
            term = term.strip()
            if term and term not in terms:
                terms.append(term)

        add(keyword)
        add(keyword.replace("“", '"').replace("”", '"'))
        add(keyword.replace("“", "").replace("”", "").replace('"', ""))

        for quoted in re.findall(r"[“\"]([^”\"]+)[”\"]", keyword):
            add(quoted)
        for suffix in ("专题课", "课程", "课"):
            if keyword.endswith(suffix):
                add(keyword[: -len(suffix)])
        return terms

    def find_course_link(self, keyword_terms: list[str]) -> tuple[Optional[Locator], str, str]:
        if not self.page:
            return None, "", ""

        link_selectors = [
            ".course-info a.color1",
            ".course-info a",
            ".course a.color1",
            ".course a[target='_blank']",
            "a.color1",
            "a[target='_blank']",
        ]
        containers = [self.page] + self.page.frames
        for container in containers:
            for term in keyword_terms:
                for selector in link_selectors:
                    candidate = container.locator(selector).filter(has_text=term).first
                    try:
                        candidate.wait_for(state="visible", timeout=1_000)
                        return candidate, term, selector
                    except (PlaywrightTimeoutError, PlaywrightError):
                        continue

        # Last resort for non-Chaoxing layouts: avoid huge page containers that only
        # match because they contain the course list.
        for container in containers:
            for term in keyword_terms:
                candidates = container.get_by_text(term, exact=False)
                try:
                    count = min(candidates.count(), 10)
                except PlaywrightError:
                    continue
                for index in range(count):
                    candidate = candidates.nth(index)
                    try:
                        candidate.wait_for(state="visible", timeout=500)
                        text_length = candidate.evaluate(
                            "el => ((el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim()).length"
                        )
                        if text_length > 120:
                            continue
                        return candidate, term, "text fallback"
                    except (PlaywrightTimeoutError, PlaywrightError):
                        continue

        return None, "", ""

    def find_locator_in_page_or_frames(
        self,
        selector: str,
        description: str,
        state: str = "visible",
        timeout_ms: Optional[int] = None,
        log_missing: bool = True,
        **values: str,
    ) -> Optional[Locator]:
        if not self.page:
            return None

        resolved = selector.format(**values)
        deadline = time.monotonic() + (timeout_ms or self.config["lookup_timeout_ms"]) / 1000
        last_frame_count = 0

        while time.monotonic() < deadline:
            candidates = [self.page.locator(resolved).first]
            frames = self.page.frames
            last_frame_count = len(frames)
            candidates.extend(frame.locator(resolved).first for frame in frames)

            for candidate in candidates:
                try:
                    candidate.wait_for(state=state, timeout=1_000)
                    return candidate
                except (PlaywrightTimeoutError, PlaywrightError):
                    continue

            time.sleep(0.5)

        if log_missing:
            current_url = self.page.url if self.page else ""
            current_title = ""
            try:
                current_title = self.page.title() if self.page else ""
            except PlaywrightError:
                current_title = "<无法读取标题>"
            print(
                f"未找到元素 [{description}]，selector={resolved}，"
                f"title={current_title}，url={current_url}，frames={last_frame_count}"
            )
        return None

    def safe_fill(self, selector: str, value: str, description: str) -> bool:
        if not self.page:
            return False
        if not value:
            print(f"配置缺失: {description} 为空，请先设置环境变量或配置值。")
            return False
        try:
            target = self.find_locator_in_page_or_frames(selector, description)
            if not target:
                return False
            self.random_delay()
            target.fill(value)
            print(f"已输入: {description}")
            return True
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            print(f"输入失败 [{description}]: {exc}")
            return False

    def safe_click(self, target: Locator, description: str) -> bool:
        try:
            target.wait_for(state="visible")
            self.random_delay()
            target.click()
            print(f"已点击: {description}")
            return True
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            print(f"点击失败 [{description}]: {exc}")
            return False

    def safe_click_selector(self, selector: str, description: str, **values: str) -> bool:
        target = self.find_locator_in_page_or_frames(selector, description, **values)
        if not target:
            return False
        return self.safe_click(target, description)

    def scroll_catalogs_down(self) -> None:
        if not self.page:
            return

        containers = [self.page] + self.page.frames
        for container in containers:
            try:
                container.evaluate(
                    """() => {
                        const scrollables = [
                            document.scrollingElement,
                            document.documentElement,
                            document.body,
                            ...Array.from(document.querySelectorAll('*')).filter(element => {
                                const style = window.getComputedStyle(element);
                                return /(auto|scroll)/.test(style.overflowY)
                                    && element.scrollHeight > element.clientHeight + 20;
                            })
                        ].filter(Boolean);
                        const seen = new Set();
                        for (const element of scrollables) {
                            if (seen.has(element)) {
                                continue;
                            }
                            seen.add(element);
                            element.scrollTop = Math.min(
                                element.scrollHeight,
                                element.scrollTop + Math.max(500, element.clientHeight * 0.8)
                            );
                        }
                    }"""
                )
            except PlaywrightError:
                continue

    def find_text_in_page_or_frames_with_scroll(self, text: str, description: str) -> Optional[Locator]:
        if not self.page:
            return None

        deadline = time.monotonic() + self.config["lookup_timeout_ms"] / 1000
        attempts = 0
        while time.monotonic() < deadline:
            containers = [self.page] + self.page.frames
            for container in containers:
                candidate = container.get_by_text(text, exact=False).first
                try:
                    candidate.wait_for(state="visible", timeout=700)
                    return candidate
                except (PlaywrightTimeoutError, PlaywrightError):
                    continue

            attempts += 1
            print(f"未找到 [{description}: {text}]，向下滚动目录继续查找（第 {attempts} 次）。")
            self.scroll_catalogs_down()
            time.sleep(0.5)

        current_url = self.page.url if self.page else ""
        print(f"滚动查找后仍未找到 [{description}: {text}]，url={current_url}")
        return None

    def safe_click_with_optional_popup(self, target: Locator, description: str) -> bool:
        if not self.page:
            return False

        clicked = False
        try:
            with self.page.expect_popup(timeout=5_000) as popup_info:
                clicked = self.safe_click(target, description)
            if not clicked:
                return False
            self.page = popup_info.value
            self.page.set_default_timeout(self.config["timeout_ms"])
            self.page.wait_for_load_state("domcontentloaded")
            print(f"已切换到新页面: {self.page.title()}")
            return True
        except PlaywrightTimeoutError:
            print(f"{description} 未打开新窗口，继续使用当前页面。")
            return clicked
        except PlaywrightError as exc:
            print(f"处理新窗口失败 [{description}]: {exc}")
            return False

    def login(self) -> bool:
        if not self.page:
            return False
        try:
            self.page.goto(self.config["login_url"], wait_until="domcontentloaded")
            print("已打开登录页")
        except PlaywrightError as exc:
            print(f"打开登录页失败: {exc}")
            return False

        filled_username = self.safe_fill(
            self.selectors["username_input"],
            self.config["username"],
            "账号",
        )
        filled_password = self.safe_fill(
            self.selectors["password_input"],
            self.config["password"],
            "密码",
        )
        if not filled_username or not filled_password:
            return False

        if not self.safe_click_selector(self.selectors["login_button"], "登录按钮"):
            return False

        self.wait_for_page_settle("登录后页面")
        return True

    def open_course(self) -> bool:
        keyword = self.config["course_keyword"]
        if not self.page:
            return False

        keyword_terms = self.course_keyword_terms(keyword)
        deadline = time.monotonic() + self.config["lookup_timeout_ms"] / 1000
        course: Optional[Locator] = None
        matched_term = keyword
        matched_source = ""

        while time.monotonic() < deadline:
            course, matched_term, matched_source = self.find_course_link(keyword_terms)
            if course:
                break
            time.sleep(0.5)

        if not course:
            print(
                f"未找到元素 [课程卡片: {keyword}]（模糊匹配），"
                f"尝试关键词={keyword_terms}，url={self.page.url}"
            )
            self.save_debug_screenshot("open_course_failed")
            return False

        if matched_term != keyword:
            print(f"课程关键词 [{keyword}] 未直接命中，已用 [{matched_term}] 匹配。")
        if matched_source:
            print(f"课程入口匹配来源: {matched_source}")
        before_url = self.page.url
        course_href = ""
        try:
            course_href = course.get_attribute("href") or ""
        except PlaywrightError:
            course_href = ""
        if not self.safe_click_with_optional_popup(course, f"课程卡片: {keyword}"):
            return False
        if self.page and self.page.url == before_url and course_href:
            try:
                print("课程链接点击后仍停留在课程列表，改用课程链接直接打开。")
                self.page.goto(course_href, wait_until="domcontentloaded", timeout=self.config["timeout_ms"])
            except PlaywrightError as exc:
                print(f"直接打开课程链接失败: {exc}")
                return False
        self.wait_for_page_settle("课程页")
        return True

    def open_video_chapter(self) -> bool:
        if not self.page:
            return False

        self.safe_click_selector(self.selectors["chapters_tab"], "章节页签")
        self.wait_for_page_settle("章节页")
        if not self.handle_commitment_if_present():
            return False

        chapter_keyword = self.config.get("chapter_keyword", "").strip()
        if chapter_keyword:
            chapter = self.find_text_in_page_or_frames_with_scroll(chapter_keyword, "章节")
            clicked = self.safe_click_with_optional_popup(chapter, f"章节: {chapter_keyword}") if chapter else False
        else:
            chapter = self.find_locator_in_page_or_frames(self.selectors["chapter_item"], "视频章节")
            clicked = self.safe_click_with_optional_popup(chapter, "视频章节") if chapter else False

        if not clicked:
            print("未能点击章节；如果课程页默认已显示视频，将继续尝试查找 video 元素。")
            return self.wait_for_video()

        self.wait_for_page_settle("视频章节页")
        return self.wait_for_learning_content()

    def handle_commitment_if_present(self) -> bool:
        if not self.config.get("auto_commitment", True):
            return True

        modal = self.find_locator_in_page_or_frames(
            self.selectors["commitment_modal"],
            "在线学习诚信承诺书",
            state="visible",
            timeout_ms=self.config["commitment_timeout_ms"],
            log_missing=False,
        )
        if not modal:
            return True

        print("检测到在线学习诚信承诺书，尝试自动确认并开始学习。")
        checkbox = self.find_locator_in_page_or_frames(
            self.selectors["commitment_checkbox"],
            "承诺书确认文本",
            timeout_ms=3_000,
        )
        if checkbox:
            self.safe_click(checkbox, "承诺书确认")

        start_button = self.find_locator_in_page_or_frames(
            self.selectors["commitment_start"],
            "开始学习按钮",
            timeout_ms=5_000,
        )
        if not start_button:
            print("未找到承诺书开始学习按钮。")
            return False

        return self.safe_click(start_button, "开始学习")

    def wait_for_video(self) -> bool:
        video = self.video_locator()
        if video:
            print("已检测到 video 元素")
            return True
        print("未检测到 video 元素")
        return False

    def wait_for_learning_content(self) -> bool:
        content = self.find_locator_in_page_or_frames(
            self.selectors["learning_content"],
            "学习内容",
            state="attached",
            timeout_ms=self.config["lookup_timeout_ms"],
            log_missing=False,
        )
        if content:
            print("已检测到学习内容")
            return True
        print("未检测到学习内容")
        return False

    def video_locator(self) -> Optional[Locator]:
        return self.find_locator_in_page_or_frames(
            self.selectors["video"],
            "video 元素",
            state="attached",
        )

    def video_locators(self) -> list[Locator]:
        if not self.page:
            return []

        videos: list[Locator] = []
        selector = self.selectors["video"]
        containers = [self.page] + [frame for frame in self.page.frames if frame != self.page.main_frame]
        for frame in containers:
            try:
                locator = frame.locator(selector)
                count = locator.count()
            except PlaywrightError:
                continue

            for index in range(count):
                video = locator.nth(index)
                try:
                    video.wait_for(state="attached", timeout=500)
                    videos.append(video)
                except (PlaywrightTimeoutError, PlaywrightError):
                    continue
        return videos

    def wait_for_video_locators(self) -> list[Locator]:
        deadline = time.monotonic() + max(0.0, float(self.config.get("video_initial_wait_seconds", 0.0)))
        while True:
            videos = self.video_locators()
            if videos:
                return videos
            if time.monotonic() >= deadline:
                return []
            time.sleep(0.5)

    def incomplete_learning_signals(self) -> list[str]:
        if not self.page:
            return []

        signals: list[str] = []
        containers = [self.page] + [frame for frame in self.page.frames if frame != self.page.main_frame]
        for index, container in enumerate(containers):
            try:
                result = container.evaluate(
                    """() => {
                        const visible = element => {
                            const style = window.getComputedStyle(element);
                            const box = element.getBoundingClientRect();
                            return style.display !== 'none'
                                && style.visibility !== 'hidden'
                                && box.width > 0
                                && box.height > 0;
                        };
                        const textOf = element => (element.innerText || element.textContent || '').replace(/\\s+/g, ' ').trim();
                        const classOf = element => {
                            const parts = [];
                            let current = element;
                            for (let depth = 0; current && depth < 3; depth += 1) {
                                parts.push(String(current.className || ''));
                                current = current.parentElement;
                            }
                            return parts.join(' ');
                        };
                        const found = [];
                        const activeSelectors = [
                            '.posCatalog_select',
                            '.active',
                            '.current',
                            '.curmark',
                            '.selected',
                            '[aria-current="true"]'
                        ];
                        for (const selector of activeSelectors) {
                            for (const active of Array.from(document.querySelectorAll(selector)).filter(visible)) {
                                const activeText = textOf(active).slice(0, 80);
                                const activeClass = classOf(active);
                                const incompleteMarker = active.querySelector(
                                    '.jobCount, [class*="jobCount"], [class*="orange"], [class*="unfinish"], [class*="unfinished"], [class*="incomplete"], [class*="notFinish"], [class*="not-finish"]'
                                );
                                if (incompleteMarker && visible(incompleteMarker)) {
                                    found.push(`当前目录项仍有未完成标记: ${activeText || activeClass}`);
                                }
                            }
                        }

                        for (const marker of Array.from(document.querySelectorAll(
                            '.jobCount, [class*="jobCount"], [class*="orange"], [class*="unfinish"], [class*="unfinished"], [class*="incomplete"], [class*="notFinish"], [class*="not-finish"]'
                        )).filter(visible)) {
                            const markerText = textOf(marker).slice(0, 40);
                            const markerClass = classOf(marker);
                            found.push(`页面仍有未完成标记: ${markerText || markerClass}`);
                            if (found.length >= 5) {
                                break;
                            }
                        }

                        return found;
                    }"""
                )
                for signal in result:
                    label = f"frame#{index}: {signal}"
                    if label not in signals:
                        signals.append(label)
            except PlaywrightError:
                continue
        return signals

    def wait_for_incomplete_signals_to_clear(self) -> list[str]:
        settle_seconds = max(0.0, float(self.config.get("completion_settle_seconds", 0.0)))
        deadline = time.monotonic() + settle_seconds
        last_signals = self.incomplete_learning_signals()
        while last_signals and time.monotonic() < deadline:
            print("检测到当前任务可能仍未完成，等待平台状态刷新...")
            time.sleep(min(1.0, max(0.1, deadline - time.monotonic())))
            last_signals = self.incomplete_learning_signals()
        return last_signals

    def set_video_speed_and_play(self, video: Optional[Locator] = None) -> bool:
        try:
            target = video or self.video_locator()
            if not target:
                return False
            return self.recover_video_playback(target, "初始播放")
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            print(f"设置视频倍速失败: {exc}")
            return False

    def recover_video_playback(self, video: Locator, reason: str) -> bool:
        try:
            playback_rate = self.config["playback_rate"]
            video.evaluate(
                """async (element, rate) => {
                    element.muted = true;
                    element.playbackRate = rate;
                    element.defaultPlaybackRate = rate;
                    try {
                        await element.play();
                    } catch (error) {
                        console.warn("video.play() was blocked", error);
                    }
                }""",
                playback_rate,
            )
            print(f"已设置视频倍速: {playback_rate}，触发原因: {reason}")
            return True
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            print(f"恢复视频播放失败 [{reason}]: {exc}")
            return False

    def read_video_state(self, video: Optional[Locator], video_index: Optional[int] = None) -> Optional[Dict[str, Any]]:
        candidates: list[Locator] = []
        if video:
            candidates.append(video)
        if video_index is not None:
            videos = self.video_locators()
            if video_index < len(videos):
                candidates.append(videos[video_index])

        seen: set[int] = set()
        for candidate in candidates:
            candidate_id = id(candidate)
            if candidate_id in seen:
                continue
            seen.add(candidate_id)
            try:
                return candidate.evaluate(
                    """element => ({
                        currentTime: element.currentTime || 0,
                        duration: Number.isFinite(element.duration) ? element.duration : 0,
                        ended: element.ended,
                        paused: element.paused,
                        playbackRate: element.playbackRate
                    })"""
                )
            except (PlaywrightTimeoutError, PlaywrightError) as exc:
                print(f"读取视频进度失败，尝试重新定位 video: {exc}")
                continue
        return None

    def wait_until_video_finished(self, video: Optional[Locator] = None, video_index: Optional[int] = None) -> bool:
        started_at = time.monotonic()
        max_wait = self.config["max_video_wait_seconds"]
        poll_seconds = float(self.config["progress_poll_seconds"])
        min_poll_seconds = max(0.1, float(self.config.get("progress_min_poll_seconds", 0.5)))
        completion_margin = max(0.0, float(self.config.get("progress_completion_margin_seconds", 0.8)))
        stall_polls = 0
        last_current: Optional[float] = None

        while time.monotonic() - started_at < max_wait:
            target = video or self.video_locator()
            if not target:
                return False
            state = self.read_video_state(target, video_index)
            if not state:
                print("读取视频进度失败: 重新定位 video 后仍无法读取。")
                return False

            current = float(state["currentTime"])
            duration = float(state["duration"])
            ended = bool(state["ended"])
            paused = bool(state["paused"])
            playback_rate = float(state["playbackRate"])
            if duration > 0:
                percent = min(current / duration * 100, 100)
                print(
                    f"播放进度: {current:.1f}/{duration:.1f}s "
                    f"({percent:.1f}%), 倍速 {playback_rate}, paused={paused}"
                )
            else:
                print(f"播放进度: {current:.1f}s, 等待视频时长信息...")

            if ended or (duration > 0 and current >= duration - 1):
                print("当前视频已播放完成")
                return True

            if last_current is not None and current <= last_current + self.config["progress_stall_epsilon_seconds"]:
                stall_polls += 1
            else:
                stall_polls = 0
            last_current = current

            rate_changed = abs(playback_rate - float(self.config["playback_rate"])) > 0.05
            if paused or rate_changed or stall_polls >= self.config["progress_stall_polls"]:
                reason = "paused" if paused else "倍速漂移" if rate_changed else f"播放进度停滞 {stall_polls} 次"
                print(f"检测到视频播放异常: {reason}，尝试恢复播放。")
                if not self.recover_video_playback(target, reason):
                    self.save_debug_screenshot("video_recover_failed")
                    return False
                stall_polls = 0

            sleep_seconds = poll_seconds
            if duration > 0 and playback_rate > 0:
                remaining_media_seconds = max(0.0, duration - current - completion_margin)
                estimated_remaining_wall_seconds = remaining_media_seconds / max(playback_rate, 0.1) + 0.2
                sleep_seconds = min(poll_seconds, max(min_poll_seconds, estimated_remaining_wall_seconds))
            time.sleep(sleep_seconds)

        print("等待视频播放完成超时")
        self.save_debug_screenshot("video_wait_timeout")
        return False

    def process_current_learning_unit(self) -> bool:
        videos = self.wait_for_video_locators()
        if videos:
            print(f"当前学习页检测到 {len(videos)} 个 video 元素，将逐个处理。")
            for index, video in enumerate(videos, start=1):
                print(f"开始处理当前页第 {index}/{len(videos)} 个视频")
                if not self.set_video_speed_and_play(video):
                    self.save_debug_screenshot(f"set_video_speed_failed_inline_{index}")
                    return False
                if not self.wait_until_video_finished(video, index - 1):
                    self.save_debug_screenshot(f"video_wait_failed_inline_{index}")
                    return False
            return True

        return self.handle_courseware_or_non_video_unit()

    def handle_courseware_or_non_video_unit(self) -> bool:
        if not self.page:
            return False

        print("当前学习页未检测到视频，按课件/非视频任务处理。")
        opener = self.find_locator_in_page_or_frames(
            self.selectors["courseware_open"],
            "课件入口",
            timeout_ms=3_000,
            log_missing=False,
        )
        if opener:
            return self.quick_open_and_return(opener, "课件/非视频任务")

        hold_ms = max(0, int(float(self.config["courseware_hold_seconds"]) * 1000))
        if hold_ms:
            self.page.wait_for_timeout(hold_ms)
        print("未找到明确课件入口，已短暂停留后继续。")
        return True

    def quick_open_and_return(self, target: Locator, description: str) -> bool:
        if not self.page:
            return False

        before_url = self.page.url
        clicked = False
        try:
            with self.page.expect_popup(timeout=3_000) as popup_info:
                clicked = self.safe_click(target, description)
            if not clicked:
                return False
            popup = popup_info.value
            popup.wait_for_load_state("domcontentloaded", timeout=self.config["timeout_ms"])
            popup.wait_for_timeout(max(0, int(float(self.config["courseware_hold_seconds"]) * 1000)))
            popup.close()
            print(f"已点开并关闭: {description}")
            return True
        except PlaywrightTimeoutError:
            if not clicked:
                clicked = self.safe_click(target, description)
            if not clicked:
                return False

            self.page.wait_for_timeout(max(0, int(float(self.config["courseware_hold_seconds"]) * 1000)))
            if self.page.url != before_url:
                try:
                    self.page.go_back(wait_until="domcontentloaded", timeout=self.config["timeout_ms"])
                    print(f"已点开并返回: {description}")
                except (PlaywrightTimeoutError, PlaywrightError) as exc:
                    print(f"课件返回失败 [{description}]: {exc}")
                    return False
            else:
                print(f"已点开课件入口并继续: {description}")
            return True
        except PlaywrightError as exc:
            print(f"课件快速处理失败 [{description}]: {exc}")
            return False

    def click_next_chapter(self) -> str:
        chaoxing_result = self.click_chaoxing_next_control()
        if chaoxing_result == "advanced":
            self.wait_for_page_settle("下一章节页")
            self.wait_for_learning_content()
            return "advanced"
        if chaoxing_result in {"completed", "failed"}:
            return chaoxing_result

        next_button = self.find_locator_in_page_or_frames(
            self.selectors["next_chapter"],
            "下一章/下一节",
            timeout_ms=5_000,
            log_missing=False,
        )
        if not next_button:
            print("没有找到下一节控件，尝试返回章节列表进入下一章...")
            return self.try_navigate_next_from_chapter_list()

        if not self.safe_click(next_button, "下一章/下一节"):
            return "failed"
        self.wait_for_page_settle("下一章节页")
        self.wait_for_learning_content()
        return "advanced"

    def try_navigate_next_from_chapter_list(self) -> str:
        """在当前学习页面的左侧章节目录中找到下一个未完成的节点并点击。"""
        if not self.page:
            return "failed"

        # 超星学习页面左侧章节目录可能在 iframe 中，也可能在主页面
        # 常见选择器：章节树节点、课程目录项
        chapter_tree_selectors = [
            ".chapter_item[onclick]",
            ".posCatalog_select .posCatalog_name",
            ".ncells .articlename",
            ".prevNextFocusNext",
            "span.posCatalog_name",
            ".chapter_unit .chapter_small_title",
        ]

        containers = [self.page] + self.page.frames
        for container in containers:
            for selector in chapter_tree_selectors:
                try:
                    items = container.locator(selector)
                    count = items.count()
                    if count == 0:
                        continue
                    # 找到当前活跃项之后的第一个可点击项
                    found_current = False
                    for i in range(count):
                        item = items.nth(i)
                        try:
                            # 检查是否是当前活跃/选中的节点
                            class_name = item.evaluate("el => (el.className || '') + ' ' + (el.parentElement?.className || '')")
                            is_active = any(k in class_name for k in ("active", "current", "curmark", "selected"))
                            if is_active:
                                found_current = True
                                continue
                            if not found_current:
                                continue
                            # 找到当前节点之后的下一个，点击它
                            item.wait_for(state="visible", timeout=2_000)
                            item.click(timeout=3_000)
                            print(f"已点击章节目录中的下一项（第{i+1}项）")
                            self.wait_for_page_settle("下一章节页")
                            if self.wait_for_learning_content():
                                return "advanced"
                        except (PlaywrightTimeoutError, PlaywrightError):
                            continue
                except (PlaywrightTimeoutError, PlaywrightError):
                    continue

        # 备选方案：如果找不到活跃项，尝试找未完成标记的任务点
        for container in containers:
            try:
                # 超星未完成任务点通常没有 .finished / .pass 类
                unfinished = container.locator(".chapter_item[onclick]:not(.pass):not(.finished)")
                count = unfinished.count()
                for i in range(count):
                    item = unfinished.nth(i)
                    try:
                        item.wait_for(state="visible", timeout=2_000)
                        # 跳过已访问的
                        onclick_val = item.get_attribute("onclick") or ""
                        if any(url_part in onclick_val for url_part in self.visited_urls if url_part):
                            continue
                        item.click(timeout=3_000)
                        print(f"已点击未完成章节项（第{i+1}项）")
                        self.wait_for_page_settle("下一章节页")
                        if self.wait_for_learning_content():
                            return "advanced"
                    except (PlaywrightTimeoutError, PlaywrightError):
                        continue
            except (PlaywrightTimeoutError, PlaywrightError):
                continue

        print("章节列表中没有找到可进入的下一章节，课程可能已全部完成。")
        incomplete_signals = self.wait_for_incomplete_signals_to_clear()
        if incomplete_signals:
            print("没有下一节控件，但当前学习任务仍显示未完成，不能判定全课完成。")
            for signal in incomplete_signals[:5]:
                print(f"未完成信号: {signal}")
            self.save_debug_screenshot("no_next_but_incomplete")
            return "failed"
        self.save_debug_screenshot("no_next_chapter_in_list")
        return "completed" if self.config.get("stop_when_no_next", True) else "failed"

    def click_chaoxing_next_control(self) -> str:
        if not self.page:
            return "failed"

        try:
            next_control = self.find_locator_in_page_or_frames(
                "#prevNextFocusNext",
                "超星下一节控件",
                state="visible",
                timeout_ms=5_000,
                log_missing=False,
            )
            if not next_control:
                return "not_found"
            if not self.is_next_control_usable(next_control):
                print("超星下一节控件当前不可用，尝试从章节目录找下一章...")
                return "not_found"

            before_url = self.page.url
            before_signature = self.learning_page_signature()
            self.random_delay()
            next_control.scroll_into_view_if_needed(timeout=3_000)
            try:
                next_control.click(timeout=5_000)
                print("已点击: 超星下一节控件")
            except (PlaywrightTimeoutError, PlaywrightError) as click_exc:
                print(f"常规点击超星下一节失败，尝试执行 onclick: {click_exc}")
                next_control.evaluate(
                    """element => {
                        const handler = element.getAttribute('onclick');
                        if (!handler) {
                            throw new Error('next control has no onclick handler');
                        }
                        Function(handler).call(element);
                    }"""
                )
                print("已执行: 超星下一节 onclick")
            return "advanced" if self.wait_for_next_transition(before_url, before_signature) else "failed"
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            print(f"超星下一节控件不可用: {exc}")
            return "failed"

    def is_next_control_usable(self, next_control: Locator) -> bool:
        try:
            state = next_control.evaluate(
                """element => {
                    const style = window.getComputedStyle(element);
                    const className = String(element.className || '');
                    return {
                        disabled: Boolean(element.disabled),
                        ariaDisabled: element.getAttribute('aria-disabled') === 'true',
                        classDisabled: /disabled|disable|forbid|noClick/i.test(className),
                        pointerBlocked: style.pointerEvents === 'none',
                        hidden: style.display === 'none' || style.visibility === 'hidden',
                        text: (element.innerText || element.textContent || '').trim()
                    };
                }"""
            )
            if any(
                bool(state[key])
                for key in ("disabled", "ariaDisabled", "classDisabled", "pointerBlocked", "hidden")
            ):
                print(f"下一节控件不可点击，状态={state}")
                return False
            return True
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            print(f"读取下一节控件状态失败: {exc}")
            return False

    def learning_page_signature(self) -> str:
        if not self.page:
            return ""
        try:
            return self.page.evaluate(
                """() => {
                    const bodyText = (document.body ? document.body.innerText : '')
                        .replace(/\\s+/g, ' ')
                        .trim()
                        .slice(0, 2000);
                    return `${location.href}|${document.title}|${bodyText}`;
                }"""
            )
        except PlaywrightError:
            return self.page.url

    def wait_for_next_transition(self, before_url: str, before_signature: str) -> bool:
        if not self.page:
            return False

        deadline = time.monotonic() + self.config["next_navigation_timeout_ms"] / 1000
        while time.monotonic() < deadline:
            if self.page.url != before_url:
                print(f"已进入下一节页面: {self.page.url}")
                return True
            current_signature = self.learning_page_signature()
            if current_signature and current_signature != before_signature:
                print("已进入下一任务点: 页面内容已变化，URL 保持不变。")
                return True
            time.sleep(0.5)

        print("点击下一节后 URL 和页面内容均未变化，判定为未成功进入下一节。")
        self.save_debug_screenshot("next_transition_no_change")
        return False

    def wait_for_page_settle(self, description: str) -> None:
        if not self.page:
            return
        try:
            self.page.wait_for_load_state("networkidle", timeout=self.config["timeout_ms"])
        except PlaywrightTimeoutError:
            print(f"{description} 未达到 networkidle，继续执行后续步骤。")

    def run(self) -> bool:
        try:
            self.start_browser()
            if not self.login():
                self.save_debug_screenshot("login_failed")
                return False
            if not self.open_course():
                self.save_debug_screenshot("open_course_failed")
                return False
            if not self.open_video_chapter():
                self.save_debug_screenshot("open_video_chapter_failed")
                return False

            for chapter_index in range(1, self.config["max_chapters"] + 1):
                print(f"开始处理第 {chapter_index} 个学习任务点")
                if self.page:
                    self.visited_urls.add(self.page.url)
                if not self.process_current_learning_unit():
                    self.save_debug_screenshot(f"learning_unit_failed_{chapter_index}")
                    return False
                next_result = self.click_next_chapter()
                if next_result == "advanced":
                    continue
                if next_result == "completed":
                    print(f"课程 [{self.config['course_keyword']}] 已处理到最后一节，自动看课流程完成。")
                    return True
                if next_result == "failed":
                    self.save_debug_screenshot(f"next_chapter_failed_{chapter_index}")
                    return False
            print(
                f"已达到最大章节数 CX_MAX_CHAPTERS={self.config['max_chapters']}，"
                "为避免无限循环，流程已停止。"
            )
            return True
        except KeyboardInterrupt:
            print("收到中断信号，准备退出。")
            return False
        except Exception as exc:
            print(f"自动化流程出现未预期异常: {exc}")
            self.save_debug_screenshot("unexpected_error")
            return False
        finally:
            self.close()


def build_config_from_args(base_config: Dict[str, Any]) -> Dict[str, Any]:
    parser = argparse.ArgumentParser(description="Chaoxing course watcher")
    parser.add_argument("--course", help="要自动观看的课程关键词，会覆盖 CX_COURSE_KEYWORD")
    parser.add_argument("--chapter", help="起始章节关键词，会覆盖 CX_CHAPTER_KEYWORD")
    parser.add_argument("--max-chapters", type=int, help="最多连续处理的章节数，会覆盖 CX_MAX_CHAPTERS")
    parser.add_argument("--headless", action="store_true", help="使用无头浏览器运行")
    parser.add_argument("--headed", action="store_true", help="使用可见浏览器运行")
    parser.add_argument("--fast-actions", action="store_true", help="将点击/输入、课件停留、视频完成轮询缩短，用于授权测试")
    parser.add_argument("--progress-poll-seconds", type=float, help="视频进度轮询间隔，会覆盖 CX_PROGRESS_POLL_SECONDS")
    parser.add_argument("--courseware-hold-seconds", type=float, help="非视频课件打开后的停留时间，会覆盖 CX_COURSEWARE_HOLD_SECONDS")
    parser.add_argument("--browser-channel", help="使用系统浏览器通道，例如 chrome 或 msedge")
    parser.add_argument("--browser-executable", help="使用指定的系统浏览器可执行文件路径")
    args = parser.parse_args()

    config = dict(base_config)
    config["selectors"] = dict(base_config["selectors"])
    if args.course:
        config["course_keyword"] = args.course
    if args.chapter:
        config["chapter_keyword"] = args.chapter
    if args.max_chapters is not None:
        config["max_chapters"] = args.max_chapters
    if args.headless and args.headed:
        parser.error("--headless 和 --headed 不能同时使用")
    if args.headless:
        config["headless"] = True
    if args.headed:
        config["headless"] = False
    if args.fast_actions:
        config["delay_range_seconds"] = (0.1, 0.3)
        config["slow_mo_ms"] = 0
        config["progress_poll_seconds"] = min(float(config["progress_poll_seconds"]), 3.0)
        config["courseware_hold_seconds"] = min(float(config["courseware_hold_seconds"]), 0.2)
    if args.progress_poll_seconds is not None:
        config["progress_poll_seconds"] = max(0.1, args.progress_poll_seconds)
    if args.courseware_hold_seconds is not None:
        config["courseware_hold_seconds"] = max(0.0, args.courseware_hold_seconds)
    if args.browser_channel and args.browser_executable:
        parser.error("--browser-channel 和 --browser-executable 不能同时使用")
    if args.browser_channel:
        config["browser_channel"] = args.browser_channel
        config["browser_executable_path"] = ""
    if args.browser_executable:
        config["browser_executable_path"] = args.browser_executable
        config["browser_channel"] = ""
    return config


if __name__ == "__main__":
    raise SystemExit(0 if CourseAutoTester(build_config_from_args(CONFIG)).run() else 1)
