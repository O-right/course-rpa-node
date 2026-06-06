import base64
import json
import logging
import os
import random
import re
import time
import unicodedata
from dataclasses import dataclass
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
    "ai_review_multiple": env_flag("ASSIGNMENT_AI_REVIEW_MULTIPLE", "true"),
    "ai_log_raw_response": env_flag("ASSIGNMENT_AI_LOG_RAW_RESPONSE", "true"),
    "ai_enable_images": env_flag("ASSIGNMENT_AI_ENABLE_IMAGES", "true"),
    "ai_max_images_per_question": env_int("ASSIGNMENT_AI_MAX_IMAGES_PER_QUESTION", 6),
    "ai_max_image_bytes": env_int("ASSIGNMENT_AI_MAX_IMAGE_BYTES", 1_500_000),
    "ai_min_confidence": env_float("ASSIGNMENT_AI_MIN_CONFIDENCE", 0.75),
    "ai_accept_confidence": env_float(
        "ASSIGNMENT_AI_ACCEPT_CONFIDENCE",
        env_float("ASSIGNMENT_AI_MIN_CONFIDENCE", 0.75),
    ),
    "ai_review_confidence": env_float("ASSIGNMENT_AI_REVIEW_CONFIDENCE", 0.55),
    "ai_enhanced_review": env_flag("ASSIGNMENT_AI_ENHANCED_REVIEW", "true"),
    "ai_review_high_risk": env_flag("ASSIGNMENT_AI_REVIEW_HIGH_RISK", "true"),
    "ai_review_media": env_flag("ASSIGNMENT_AI_REVIEW_MEDIA", "true"),
    "ai_review_math": env_flag("ASSIGNMENT_AI_REVIEW_MATH", "true"),
    "ai_review_true_false": env_flag("ASSIGNMENT_AI_REVIEW_TRUE_FALSE", "true"),
    "ai_review_samples": env_int("ASSIGNMENT_AI_REVIEW_SAMPLES", 3),
    "ai_consensus_ratio": env_float("ASSIGNMENT_AI_CONSENSUS_RATIO", 0.66),
    "ai_high_risk_consensus_ratio": env_float("ASSIGNMENT_AI_HIGH_RISK_CONSENSUS_RATIO", 1.0),
    "ai_high_risk_require_primary_consensus": env_flag(
        "ASSIGNMENT_AI_HIGH_RISK_REQUIRE_PRIMARY_CONSENSUS",
        "true",
    ),
    "ai_review_temperature": env_float("ASSIGNMENT_AI_REVIEW_TEMPERATURE", 0.2),
    "ai_require_confidence": env_flag("ASSIGNMENT_AI_REQUIRE_CONFIDENCE", "true"),
    "stop_on_low_confidence": env_flag("ASSIGNMENT_STOP_ON_LOW_CONFIDENCE", "true"),
    "hold_browser_on_low_confidence": env_flag("ASSIGNMENT_HOLD_BROWSER_ON_LOW_CONFIDENCE", "true"),
    "risk_budget_points": env_float("ASSIGNMENT_RISK_BUDGET_POINTS", 5.0),
    "submit_within_risk_budget": env_flag("ASSIGNMENT_SUBMIT_WITHIN_RISK_BUDGET", "true"),
    "stop_on_low_score": env_flag("ASSIGNMENT_STOP_ON_LOW_SCORE", "true"),
    "min_acceptable_score": env_float("ASSIGNMENT_MIN_ACCEPTABLE_SCORE", 80.0),
    "require_manual_review_before_submit": env_flag(
        "ASSIGNMENT_REQUIRE_MANUAL_REVIEW_BEFORE_SUBMIT",
        "true",
    ),
    "review_output_dir": os.getenv("ASSIGNMENT_REVIEW_OUTPUT_DIR", "logs/reviews"),
    "reviewed_answer_file": os.getenv("ASSIGNMENT_REVIEWED_ANSWER_FILE", ""),
    "retry_with_visible_correct_answers": env_flag(
        "ASSIGNMENT_RETRY_WITH_VISIBLE_CORRECT_ANSWERS",
        "true",
    ),
    "stop_on_unanswerable": env_flag("ASSIGNMENT_STOP_ON_UNANSWERABLE", "true"),
    "skip_unanswerable_candidate": env_flag("ASSIGNMENT_SKIP_UNANSWERABLE_CANDIDATE", "false"),
    "server_mode": env_flag("ASSIGNMENT_SERVER_MODE"),
    "headless": env_flag("ASSIGNMENT_HEADLESS", os.getenv("ASSIGNMENT_SERVER_MODE", "false")),
    "device_scale_factor": env_float("ASSIGNMENT_DEVICE_SCALE_FACTOR", 2.0),
    "browser_channel": os.getenv("ASSIGNMENT_BROWSER_CHANNEL", "chrome"),
    "browser_executable_path": os.getenv("ASSIGNMENT_BROWSER_EXECUTABLE_PATH", ""),
    "timeout_ms": env_int("ASSIGNMENT_TIMEOUT_MS", 15_000),
    "navigation_retries": env_int("ASSIGNMENT_NAVIGATION_RETRIES", 2),
    "navigation_retry_delay_seconds": env_float("ASSIGNMENT_NAVIGATION_RETRY_DELAY_SECONDS", 3.0),
    "lookup_timeout_ms": env_int("ASSIGNMENT_LOOKUP_TIMEOUT_MS", 12_000),
    "locator_probe_timeout_ms": env_int("ASSIGNMENT_LOCATOR_PROBE_TIMEOUT_MS", 300),
    "locator_retry_interval_seconds": env_float("ASSIGNMENT_LOCATOR_RETRY_INTERVAL_SECONDS", 0.1),
    "action_timeout_ms": env_int("ASSIGNMENT_ACTION_TIMEOUT_MS", 5_000),
    "api_timeout_seconds": env_int("ASSIGNMENT_AI_TIMEOUT_SECONDS", 30),
    "ai_request_retries": env_int("ASSIGNMENT_AI_REQUEST_RETRIES", 2),
    "ai_retry_delay_seconds": env_float("ASSIGNMENT_AI_RETRY_DELAY_SECONDS", 2.0),
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
    "submit_completion_timeout_ms": env_int("ASSIGNMENT_SUBMIT_COMPLETION_TIMEOUT_MS", 12_000),
    "confirmation_initial_wait_ms": env_int("ASSIGNMENT_CONFIRMATION_INITIAL_WAIT_MS", 500),
    "confirmation_timeout_ms": env_int("ASSIGNMENT_CONFIRMATION_TIMEOUT_MS", 12_000),
    "confirmation_poll_ms": env_int("ASSIGNMENT_CONFIRMATION_POLL_MS", 100),
    "confirmation_candidate_timeout_ms": env_int("ASSIGNMENT_CONFIRMATION_CANDIDATE_TIMEOUT_MS", 100),
    "max_confirmation_rounds": env_int("ASSIGNMENT_MAX_CONFIRMATION_ROUNDS", 3),
    "block_on_incomplete": env_flag("ASSIGNMENT_BLOCK_ON_INCOMPLETE", "false"),
    "incomplete_block_seconds": env_int("ASSIGNMENT_INCOMPLETE_BLOCK_SECONDS", 7200),
    "max_options_per_question": env_int("ASSIGNMENT_MAX_OPTIONS_PER_QUESTION", 12),
    "hold_browser_on_exit": env_flag("ASSIGNMENT_HOLD_BROWSER_ON_EXIT", "false"),
    "max_questions": env_int("ASSIGNMENT_MAX_QUESTIONS", 120),
    "scan_interval_seconds": env_int("ASSIGNMENT_SCAN_INTERVAL_SECONDS", 3600),
    "max_scan_rounds": env_int("ASSIGNMENT_MAX_SCAN_ROUNDS", 0),
    "max_candidates_per_round": env_int("ASSIGNMENT_MAX_CANDIDATES_PER_ROUND", 10),
    "exit_when_no_unsubmitted": env_flag("ASSIGNMENT_EXIT_WHEN_NO_UNSUBMITTED", "false"),
    "inbox_keywords": ["作业：", "作业:", "作业", "测试", "练习题"],
    "inbox_exclude_keywords": ["作业结束提醒"],
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
        "question_media": "img, svg, canvas, [style*='background-image']",
        "next_button": "button:has-text('下一题'), a:has-text('下一题'), button:has-text('下一步')",
        "submit_button": (
            ".Btn_blue_1:has-text('提交'), a.btnSubmit, "
            "a:has-text('提交'), button:has-text('提交'), input[type='submit']"
        ),
        "confirm_submit_button": (
            "#workpop #popok, #popok, .popBottom #popok, "
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
    "选择题返回选项字母，例如单选返回 {\"answer\": [\"A\"], \"confidence\": 0.92}，"
    "多选返回 {\"answer\": [\"A\", \"C\"], \"confidence\": 0.86}。"
    "如果是填空题或简答题，请直接返回答案文本，例如 {\"answer\": [\"答案文本\"], \"confidence\": 0.8}。"
    "如果是共用选项题，请按每个小题的顺序返回选项字母列表，例如 4 个小题返回 "
    "{\"answer\": [\"A\", \"C\", \"B\", \"E\"], \"confidence\": 0.82}。"
    "confidence 必须是 0 到 1 之间的小数，表示你对最终答案正确性的把握；"
    "如果题干/图片/选项信息不足或把握较低，也要给出最佳猜测，但 confidence 必须降低，并附加短字段 reason 和 evidence。"
    "不要包含 JSON 以外的其他字符，不要使用 Markdown 代码块，不要添加引用标记。"
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger("assignment_tester")


@dataclass
class QuestionMedia:
    label: str
    data_url: str
    byte_size: int
    source: str


@dataclass
class QuestionData:
    text: str
    options: Dict[str, str]
    question_type: str
    controls: Dict[str, Locator]
    media: List[QuestionMedia]
    sub_questions: Optional[List[str]] = None


@dataclass
class AIAnswerResult:
    answers: List[str]
    confidence: Optional[float]
    low_confidence: bool
    reason: str
    risk_points: float = 0.0
    consensus_ratio: float = 1.0
    attempts: int = 1
    review_required: bool = False
    accepted_with_risk: bool = False


def ask_ai_brain(
    question_text: str,
    options_dict: Dict[str, str],
    question_type: Any = "unknown",
    config: Optional[Dict[str, Any]] = None,
    media: Optional[List[QuestionMedia]] = None,
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

    try:
        decision = ask_ai_brain_decision(
            question_text,
            options_dict,
            question_type,
            cfg,
            media,
            headers=headers,
        )
        if not decision or decision.low_confidence:
            return None
        return decision.answers or None
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        LOGGER.warning("AI decision failed; skipping current question. reason=%s", exc)
        return None


def ask_ai_brain_decision(
    question_text: str,
    options_dict: Dict[str, str],
    question_type: Any = "unknown",
    config: Optional[Dict[str, Any]] = None,
    media: Optional[List[QuestionMedia]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Optional[AIAnswerResult]:
    """Ask the configured decision API and include confidence metadata."""
    if isinstance(question_type, dict) and config is None:
        config = question_type
        question_type = "unknown"
    question_type = str(question_type)
    cfg = config or CONFIG
    request_headers = headers or {"Content-Type": "application/json"}
    if cfg.get("api_key") and "Authorization" not in request_headers:
        request_headers["Authorization"] = f"Bearer {cfg['api_key']}"

    try:
        decision = request_ai_answers(
            cfg,
            request_headers,
            question_type,
            question_text,
            options_dict,
            media or [],
            label="primary",
        )
        high_risk_review = question_requires_high_risk_review(
            cfg,
            question_type,
            question_text,
            options_dict,
            media or [],
        )
        review_needed = should_run_enhanced_review(
            cfg,
            question_type,
            question_text,
            decision,
            options_dict,
            media or [],
            high_risk_review,
        )
        if review_needed:
            decision = run_enhanced_ai_review(
                cfg,
                request_headers,
                question_type,
                question_text,
                options_dict,
                media or [],
                decision,
                high_risk_review=high_risk_review,
            )
        elif (
            question_type == "multiple"
            and cfg.get("ai_review_multiple")
            and decision.answers
            and len(options_dict) >= 2
        ):
            reviewed_decision = request_ai_answers(
                cfg,
                request_headers,
                question_type,
                question_text,
                options_dict,
                media or [],
                label="multiple-review",
                first_answer=decision.answers,
            )
            if reviewed_decision.answers:
                if reviewed_decision.answers != decision.answers:
                    LOGGER.info(
                        "AI multiple-review adjusted answer %s -> %s",
                        decision.answers,
                        reviewed_decision.answers,
                    )
                decision = reviewed_decision
        LOGGER.info(
            "AI final answer type=%s options=%s answer=%s confidence=%s low_confidence=%s "
            "risk_points=%.2f consensus=%.2f attempts=%s media=%s question=%s",
            question_type,
            list(options_dict.keys()),
            decision.answers,
            decision.confidence,
            decision.low_confidence,
            decision.risk_points,
            decision.consensus_ratio,
            decision.attempts,
            len(media or []),
            re.sub(r"\s+", " ", question_text)[:120],
        )
        return decision
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        LOGGER.warning("AI decision failed; skipping current question. reason=%s", exc)
        return None


def request_ai_answers(
    cfg: Dict[str, Any],
    headers: Dict[str, str],
    question_type: str,
    question_text: str,
    options_dict: Dict[str, str],
    media: List[QuestionMedia],
    label: str,
    first_answer: Optional[List[str]] = None,
    instruction: str = "",
    temperature: Optional[float] = None,
) -> AIAnswerResult:
    accuracy_instruction = build_accuracy_instruction(cfg, question_type, question_text, options_dict, media)
    user_payload: Dict[str, Any] = {
        "question_type": question_type,
        "question": question_text,
        "options": options_dict,
    }
    if media:
        user_payload["media_order"] = [
            {"label": item.label, "source": item.source, "byte_size": item.byte_size}
            for item in media
        ]
    if accuracy_instruction:
        user_payload["accuracy_instruction"] = accuracy_instruction
    if first_answer is not None:
        user_payload.update(
            {
                "first_answer": first_answer,
                "review_instruction": (
                    "请独立复核这道多选题的完整正确选项。不要默认 first_answer 正确；"
                    "如果存在漏选或多选，请返回修正后的完整选项列表。"
                ),
            }
        )
    if instruction:
        user_payload["review_instruction"] = (
            f"{instruction}\n{accuracy_instruction}" if accuracy_instruction else instruction
        )

    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_ai_user_content(user_payload, media)},
        ],
        "temperature": 0 if temperature is None else temperature,
    }
    response = post_ai_request_with_retries(cfg, headers, payload, label)
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    if cfg.get("ai_log_raw_response"):
        LOGGER.info("AI %s raw response: %s", label, content)
    parsed = parse_ai_response_json(content)
    answers = parsed.get("answer")
    normalized = normalize_ai_answers(answers, question_type, options_dict)
    if not normalized:
        raise ValueError(f"AI {label} response did not contain usable answer")
    confidence = parse_ai_confidence(parsed)
    parse_warning = str(parsed.get("_parse_warning") or "").strip()
    unusable_confidence = has_unusable_ai_confidence(parsed, confidence)
    low_confidence, reason = evaluate_ai_confidence(cfg, parsed, confidence)
    if parse_warning:
        low_confidence = True
        reason = f"{parse_warning}; {reason}" if reason else parse_warning
    if unusable_confidence:
        low_confidence = True
        warning = "AI confidence field was present but could not be parsed"
        reason = f"{warning}; {reason}" if reason else warning
    evidence = str(parsed.get("evidence") or "").strip()
    if evidence:
        reason = f"{reason}; evidence={evidence}" if reason else f"evidence={evidence}"
    LOGGER.info(
        "AI %s normalized answer=%s confidence=%s low_confidence=%s reason=%s",
        label,
        normalized,
        confidence,
        low_confidence,
        reason,
    )
    return AIAnswerResult(normalized, confidence, low_confidence, reason)


def post_ai_request_with_retries(
    cfg: Dict[str, Any],
    headers: Dict[str, str],
    payload: Dict[str, Any],
    label: str,
) -> requests.Response:
    max_retries = max(0, int(cfg.get("ai_request_retries", 2)))
    retry_delay = max(0.0, float(cfg.get("ai_retry_delay_seconds", 2.0)))
    last_exc: Optional[requests.RequestException] = None
    for attempt in range(1, max_retries + 2):
        try:
            response = requests.post(
                cfg["api_url"],
                headers=headers,
                json=payload,
                timeout=cfg["api_timeout_seconds"],
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_exc = exc
            LOGGER.warning(
                "AI %s request attempt %s/%s failed: %s",
                label,
                attempt,
                max_retries + 1,
                exc,
            )
            if attempt > max_retries:
                break
            time.sleep(retry_delay * attempt)
    if last_exc:
        raise last_exc
    raise RuntimeError("AI request failed without exception")


def question_requires_high_risk_review(
    cfg: Dict[str, Any],
    question_type: str,
    question_text: str,
    options_dict: Dict[str, str],
    media: List[QuestionMedia],
) -> bool:
    if not cfg.get("ai_review_high_risk"):
        return False
    if cfg.get("ai_review_media") and media:
        return True
    if cfg.get("ai_review_true_false") and is_true_false_question(question_type, options_dict):
        return True
    if cfg.get("ai_review_math") and is_math_like_question(question_text):
        return True
    return False


def is_true_false_question(question_type: str, options_dict: Dict[str, str]) -> bool:
    if question_type not in {"single", "unknown"} or len(options_dict) != 2:
        return False
    normalized_options = {normalize_answer_text(value) for value in options_dict.values()}
    return bool(normalized_options & {"对", "错", "正确", "错误", "TRUE", "FALSE"})


def is_math_like_question(question_text: str) -> bool:
    compact = normalize_answer_text(question_text)
    math_markers = (
        "矩阵",
        "行列式",
        "线性",
        "方程组",
        "特征值",
        "特征向量",
        "向量组",
        "相似",
        "合同",
        "秩",
        "AX=B",
        "R(A",
        "Λ",
        "λ",
    )
    return any(normalize_answer_text(marker) in compact for marker in math_markers)


def build_accuracy_instruction(
    cfg: Dict[str, Any],
    question_type: str,
    question_text: str,
    options_dict: Dict[str, str],
    media: List[QuestionMedia],
) -> str:
    instructions: List[str] = []
    if media:
        instructions.append(
            "图片按 media_order 和随后的图像顺序一一对应；如果选项文字为空且图片数量等于选项数量，"
            "请按 A/B/C/D 对应 media-node-1/media-node-2/media-node-3/media-node-4 的顺序判断。"
            "如果题干中的公式或结论只在图片里，请必须依据图片判断；如果图片证据不足，请降低 confidence。"
        )
    if is_true_false_question(question_type, options_dict):
        instructions.append(
            "判断题必须先还原完整命题再判断真假；如果“则”后面的公式、矩阵或结论缺失且图片也无法确认，"
            "不要高置信猜测。"
        )
    if cfg.get("ai_review_math") and is_math_like_question(question_text):
        instructions.append(
            "数学/线性代数题请逐项检查必要条件和充分条件，不要把常见定理漏掉前提。"
            "非齐次线性方程组 AX=b 有解等价于 rank(A)=rank(A|b)；若 A 是 m×n 且 rank(A)=m，"
            "则 A 的列空间为 R^m，所以对给定 b∈R^m 方程组相容；rank(A)=n 只能在已相容时推出唯一解。"
            "涉及相似、合同、伴随矩阵、特征值或秩时，请分别核对定义和反例。"
        )
    return "\n".join(instructions)


def should_run_enhanced_review(
    cfg: Dict[str, Any],
    question_type: str,
    question_text: str,
    decision: AIAnswerResult,
    options_dict: Dict[str, str],
    media: List[QuestionMedia],
    high_risk_review: bool = False,
) -> bool:
    if not cfg.get("ai_enhanced_review"):
        return False
    if not decision.answers:
        return False
    if high_risk_review:
        LOGGER.info(
            "AI enhanced review required for high-risk question: type=%s media=%s question=%s",
            question_type,
            len(media),
            re.sub(r"\s+", " ", question_text)[:120],
        )
        return True
    if question_type in {"multiple", "shared_options"} and len(options_dict) >= 2:
        return True
    confidence = decision.confidence
    if confidence is None:
        return bool(cfg.get("ai_require_confidence"))
    accept_confidence = float(cfg.get("ai_accept_confidence", cfg.get("ai_min_confidence", 0.75)))
    review_confidence = float(cfg.get("ai_review_confidence", 0.55))
    return review_confidence <= confidence < accept_confidence


def run_enhanced_ai_review(
    cfg: Dict[str, Any],
    headers: Dict[str, str],
    question_type: str,
    question_text: str,
    options_dict: Dict[str, str],
    media: List[QuestionMedia],
    primary: AIAnswerResult,
    high_risk_review: bool = False,
) -> AIAnswerResult:
    requested_samples = max(1, int(cfg.get("ai_review_samples", 3)))
    samples = [primary]
    review_temperature = float(cfg.get("ai_review_temperature", 0.2))
    instruction = (
        "这是增强复核。请重新独立判断，不要默认前一次答案正确。"
        "如果题干、选项或图片证据不足，请降低 confidence，并在 reason 中说明。"
        "多选题必须返回完整选项集合；共用选项题必须按小题顺序返回。"
    )
    for sample_index in range(2, requested_samples + 1):
        try:
            samples.append(
                request_ai_answers(
                    cfg,
                    headers,
                    question_type,
                    question_text,
                    options_dict,
                    media,
                    label=f"enhanced-review-{sample_index}",
                    instruction=instruction,
                    temperature=review_temperature,
                )
            )
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            LOGGER.warning("AI enhanced-review-%s failed: %s", sample_index, exc)

    combined = combine_ai_review_samples(
        cfg,
        samples,
        question_type,
        high_risk_review=high_risk_review,
    )
    if question_type == "text" and combined.low_confidence and len(samples) > 1:
        candidate_answers = [sample.answers for sample in samples if sample.answers]
        adjudication_instruction = (
            "这是多空文本题的最终仲裁复核。前几次独立回答不完全一致，候选答案如下："
            + json.dumps(candidate_answers, ensure_ascii=False)
            + "。请重新依据题干和图片逐空判断，返回唯一最终 answer 数组。"
            "如果候选答案里有同义、大小写或词形差异，请选择最符合题图原文和语境的一项；"
            "如果证据仍不足，请降低 confidence 并说明原因。"
        )
        try:
            adjudicated = request_ai_answers(
                cfg,
                headers,
                question_type,
                question_text,
                options_dict,
                media,
                label="text-adjudication",
                instruction=adjudication_instruction,
                temperature=0,
            )
            adjudicated.attempts = len(samples) + 1
            adjudicated.review_required = True
            adjudicated.consensus_ratio = max(combined.consensus_ratio, 1.0 if not adjudicated.low_confidence else 0.0)
            LOGGER.info(
                "AI text adjudication summary answers=%s confidence=%s low_confidence=%s reason=%s",
                adjudicated.answers,
                adjudicated.confidence,
                adjudicated.low_confidence,
                adjudicated.reason,
            )
            if high_risk_review:
                combined.reason = (
                    f"{combined.reason}; high-risk text adjudication did not override review disagreement"
                    if combined.reason
                    else "high-risk text adjudication did not override review disagreement"
                )
                return combined
            if adjudicated.answers and not adjudicated.low_confidence:
                return adjudicated
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            LOGGER.warning("AI text-adjudication failed: %s", exc)
    return combined


def combine_ai_review_samples(
    cfg: Dict[str, Any],
    samples: List[AIAnswerResult],
    question_type: str,
    high_risk_review: bool = False,
) -> AIAnswerResult:
    usable = [sample for sample in samples if sample.answers]
    if not usable:
        return AIAnswerResult([], None, True, "enhanced review produced no usable answers", attempts=len(samples))

    grouped: Dict[Tuple[str, ...], List[AIAnswerResult]] = {}
    for sample in usable:
        key = tuple(sample.answers)
        grouped.setdefault(key, []).append(sample)

    top_key, top_group = max(grouped.items(), key=lambda item: (len(item[1]), average_confidence(item[1]) or -1.0))
    consensus_ratio = len(top_group) / len(usable)
    confidence = average_confidence(top_group)
    accept_confidence = float(cfg.get("ai_accept_confidence", cfg.get("ai_min_confidence", 0.75)))
    review_confidence = float(cfg.get("ai_review_confidence", 0.55))
    required_consensus = float(cfg.get("ai_consensus_ratio", 0.66))
    if high_risk_review:
        required_consensus = max(
            required_consensus,
            float(cfg.get("ai_high_risk_consensus_ratio", 1.0)),
        )
    low_confidence_reasons = [sample.reason for sample in top_group if sample.low_confidence and sample.reason]

    low_confidence = False
    reason_parts: List[str] = []
    if consensus_ratio < required_consensus:
        low_confidence = True
        reason_parts.append(f"consensus {consensus_ratio:.2f} < required {required_consensus:.2f}")
    if (
        high_risk_review
        and cfg.get("ai_high_risk_require_primary_consensus", True)
        and samples
        and tuple(samples[0].answers) != top_key
    ):
        low_confidence = True
        reason_parts.append("primary answer disagreed with review consensus on high-risk question")
    if confidence is None:
        if cfg.get("ai_require_confidence"):
            low_confidence = True
            reason_parts.append("missing confidence after review")
    elif confidence < review_confidence:
        low_confidence = True
        reason_parts.append(f"confidence {confidence:.2f} < review floor {review_confidence:.2f}")

    accepted_with_risk = False
    if not low_confidence and confidence is not None and confidence < accept_confidence:
        accepted_with_risk = True
        reason_parts.append(f"accepted by review with confidence {confidence:.2f} < {accept_confidence:.2f}")
    if not reason_parts and low_confidence_reasons:
        reason_parts.append("; ".join(low_confidence_reasons[:2]))

    answers = list(top_key)
    LOGGER.info(
        "AI enhanced review summary type=%s answers=%s consensus=%.2f confidence=%s "
        "attempts=%s accepted_with_risk=%s low_confidence=%s",
        question_type,
        answers,
        consensus_ratio,
        confidence,
        len(usable),
        accepted_with_risk,
        low_confidence,
    )
    return AIAnswerResult(
        answers,
        confidence,
        low_confidence,
        "; ".join(reason_parts),
        consensus_ratio=consensus_ratio,
        attempts=len(usable),
        review_required=True,
        accepted_with_risk=accepted_with_risk,
    )


def average_confidence(samples: List[AIAnswerResult]) -> Optional[float]:
    values = [sample.confidence for sample in samples if sample.confidence is not None]
    if not values:
        return None
    return sum(values) / len(values)


def build_ai_user_content(user_payload: Dict[str, Any], media: List[QuestionMedia]) -> Any:
    text = json.dumps(user_payload, ensure_ascii=False)
    if not media:
        return text

    content: List[Dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                text
                + "\n\n这道题包含图片信息。请结合附带的题目截图判断题干和选项，"
                "最终仍然严格只返回 JSON。"
            ),
        }
    ]
    for item in media:
        content.append(
            {
                "type": "text",
                "text": f"附图 {item.label}，来源={item.source}，按 DOM/页面出现顺序排列。",
            }
        )
        content.append({"type": "image_url", "image_url": {"url": item.data_url}})
    return content


def parse_ai_response_json(content: str) -> Dict[str, Any]:
    """Parse the first JSON object from an AI response.

    Chat2API sometimes returns valid JSON wrapped in Markdown fences, quotes, or
    citation markers. The downstream logic only needs the first JSON object.
    """
    stripped = content.strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        return parsed

    decoder = json.JSONDecoder()
    for index, char in enumerate(stripped):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(stripped[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    recovered = recover_ai_answer_from_malformed_json(stripped)
    if recovered is not None:
        recovered["_parse_warning"] = "recovered answer from malformed AI JSON"
        return recovered
    raise json.JSONDecodeError("AI response does not contain a JSON object", content, 0)


def recover_ai_answer_from_malformed_json(content: str) -> Optional[Dict[str, Any]]:
    """Recover a valid answer value when nearby metadata breaks JSON parsing."""
    decoder = json.JSONDecoder()
    answer_field = re.search(r"""(?:"answer"|'answer')\s*:""", content, flags=re.IGNORECASE)
    if not answer_field:
        return None

    try:
        answer_value, _ = decoder.raw_decode(content[answer_field.end() :].lstrip())
    except json.JSONDecodeError:
        return None
    if not isinstance(answer_value, (str, list, dict)):
        return None
    return {"answer": answer_value}


def normalize_ai_answers(answers: Any, question_type: str, options_dict: Dict[str, str]) -> List[str]:
    if isinstance(answers, str):
        if question_type == "text":
            values = [answers]
        else:
            letters = re.findall(r"[A-Z]", answers.upper())
            values = letters if letters else [answers]
    elif isinstance(answers, list):
        values = [str(item).strip() for item in answers if str(item).strip()]
    elif isinstance(answers, dict):
        values = [
            str(answers[key]).strip()
            for key in sorted(answers, key=lambda item: int(item) if str(item).isdigit() else str(item))
            if str(answers[key]).strip()
        ]
    else:
        raise ValueError("AI response JSON does not contain a string/list field named 'answer'")

    if question_type == "text":
        return [value.strip() for value in values if value.strip()]

    allowed_order = list(options_dict.keys())
    allowed = set(allowed_order)
    if question_type == "shared_options":
        mapped_values = []
        for value in values:
            letter = map_ai_answer_to_option_letter(value, options_dict)
            if letter:
                mapped_values.append(letter)
        return mapped_values

    seen = set()
    normalized: List[str] = []
    for value in values:
        letter = map_ai_answer_to_option_letter(value, options_dict)
        if letter not in allowed or letter in seen:
            continue
        seen.add(letter)
        normalized.append(letter)
    return sorted(normalized, key=allowed_order.index)


def map_ai_answer_to_option_letter(value: Any, options_dict: Dict[str, str]) -> str:
    raw = str(value).strip()
    if not raw:
        return ""

    allowed = set(options_dict)
    letter = raw.upper()
    if letter in allowed:
        return letter

    compact_value = normalize_answer_text(raw)
    if not compact_value:
        return ""

    exact_matches = [
        option_letter
        for option_letter, option_text in options_dict.items()
        if normalize_answer_text(option_text) == compact_value
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]

    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", compact_value):
        token_matches = []
        for option_letter, option_text in options_dict.items():
            option_tokens = re.findall(r"[-+]?\d+(?:\.\d+)?", normalize_answer_text(option_text))
            if compact_value in option_tokens:
                token_matches.append(option_letter)
        if len(token_matches) == 1:
            return token_matches[0]

    contains_matches = [
        option_letter
        for option_letter, option_text in options_dict.items()
        if compact_value and compact_value in normalize_answer_text(option_text)
    ]
    if len(contains_matches) == 1:
        return contains_matches[0]
    return ""


def normalize_answer_text(value: str) -> str:
    return re.sub(r"[\s\u00a0，,。.;；:：()（）\\[\\]【】{}\"'`]+", "", value).upper()


def parse_ai_confidence(parsed: Dict[str, Any]) -> Optional[float]:
    raw_value = parsed.get("confidence", parsed.get("confidence_score"))
    if raw_value is None:
        return None
    if isinstance(raw_value, (int, float)):
        value = float(raw_value)
    elif isinstance(raw_value, str):
        normalized = raw_value.strip().lower()
        label_map = {"high": 0.9, "medium": 0.6, "low": 0.3, "高": 0.9, "中": 0.6, "低": 0.3}
        if normalized in label_map:
            return label_map[normalized]
        percent_match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*%", normalized)
        if percent_match:
            value = float(percent_match.group(1)) / 100
        else:
            try:
                value = float(normalized)
            except ValueError:
                return None
    else:
        return None

    if value > 1 and value <= 100:
        value = value / 100
    return max(0.0, min(1.0, value))


def has_unusable_ai_confidence(parsed: Dict[str, Any], confidence: Optional[float]) -> bool:
    if confidence is not None:
        return False
    if "confidence" in parsed:
        raw_value = parsed.get("confidence")
    elif "confidence_score" in parsed:
        raw_value = parsed.get("confidence_score")
    else:
        return False
    if raw_value is None:
        return False
    return bool(str(raw_value).strip())


def parse_boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "low", "uncertain", "不确定"}
    return False


def compact_page_text(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def has_low_score_retry_marker(text: str) -> bool:
    compacted = compact_page_text(text)
    low_score_markers = ("未达到及格线", "未达及格线", "未及格", "不及格")
    retry_markers = ("请重做", "重做", "重新作答", "重新提交")
    return any(marker in compacted for marker in low_score_markers) and any(
        marker in compacted for marker in retry_markers
    )


def has_submitted_result_markers(text: str) -> bool:
    compacted = compact_page_text(text)
    has_answer_review = "我的答案" in compacted and (
        "正确答案" in compacted or "答案解析" in compacted
    )
    has_grading_context = "作答时间" in compacted and (
        "我的答案" in compacted or "正确答案" in compacted
    )
    return has_answer_review or has_grading_context or (
        has_low_score_retry_marker(text) and ("我的答案" in compacted or "正确答案" in compacted)
    )


def evaluate_ai_confidence(
    cfg: Dict[str, Any],
    parsed: Dict[str, Any],
    confidence: Optional[float],
) -> Tuple[bool, str]:
    if parse_boolish(parsed.get("low_confidence")) or parse_boolish(parsed.get("uncertain")):
        return True, str(parsed.get("reason") or "model marked answer uncertain")

    min_confidence = float(cfg.get("ai_accept_confidence", cfg.get("ai_min_confidence", 0.75)))
    if confidence is None:
        if cfg.get("ai_require_confidence"):
            return True, "missing confidence"
        return False, ""

    if confidence < min_confidence:
        return True, f"confidence {confidence:.2f} < threshold {min_confidence:.2f}"
    return False, str(parsed.get("reason") or "")


class AssignmentAutoTester:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.page: Optional[Page] = None
        self._dialog_auto_accept_page: Optional[Page] = None
        self.halt_requested = False
        self.halt_reason = ""
        self._halt_pause_handled = False
        self.completed_assignments = 0
        self.assignment_risks: List[Dict[str, Any]] = []
        self._reviewed_answer_map: Optional[Dict[int, List[str]]] = None
        self.current_candidate_title = ""
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
        self.context = self.browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="zh-CN",
            device_scale_factor=self.config.get("device_scale_factor", 2.0),
        )
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
        if not self.goto_with_retries(self.config["login_url"], "login page"):
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
        except PlaywrightError as exc:
            LOGGER.info(
                "Login navigation wait was interrupted (%s); continuing with explicit Inbox navigation.",
                exc,
            )
        self.wait_for_page_settle("after login")
        return True

    def goto_with_retries(self, url: str, description: str) -> bool:
        if not self.page:
            return False
        attempts = max(1, int(self.config.get("navigation_retries", 2)) + 1)
        retry_delay = max(0.0, float(self.config.get("navigation_retry_delay_seconds", 3.0)))
        last_error = ""
        for attempt in range(1, attempts + 1):
            try:
                self.page.goto(url, wait_until="domcontentloaded")
                LOGGER.info("Opened %s", description)
                return True
            except PlaywrightError as exc:
                last_error = str(exc)
                LOGGER.warning("Open %s attempt %s/%s failed: %s", description, attempt, attempts, exc)
                if attempt >= attempts:
                    break
                self.page.wait_for_timeout(int(retry_delay * attempt * 1000))
        LOGGER.error("Open %s failed after %s attempt(s): %s", description, attempts, last_error)
        return False

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
                    notice_url = self.extract_menu_data_url("收件箱")
                    if notice_url and notice_url.startswith("http") and "notice.chaoxing.com" in notice_url:
                        self.page.goto(notice_url, wait_until="domcontentloaded")
                        self.wait_for_page_settle("notice inbox direct url")
                    self.find_locator(self.selectors["inbox_loaded"], timeout_ms=15_000, log_missing=False)
                    LOGGER.info("Opened inbox via forced URL: %s", self.config["inbox_url"])
                    return True
                except PlaywrightError as exc:
                    LOGGER.warning("Forced inbox URL attempt %s failed: %s", attempt, exc)
                    time.sleep(2)
        except PlaywrightError as exc:
            LOGGER.warning("Forced inbox URL failed: %s", exc)
            return False
        return False

    def extract_menu_data_url(self, name: str) -> str:
        if not self.page:
            return ""
        try:
            value = self.page.evaluate(
                """(name) => {
                    const candidates = Array.from(document.querySelectorAll("[dataurl], [data-url], [onclick]"));
                    const target = candidates.find((element) => {
                        const text = element.getAttribute("name") || element.innerText || element.textContent || "";
                        return text.includes(name);
                    });
                    if (!target) return "";
                    const direct = target.getAttribute("dataurl") || target.getAttribute("data-url") || "";
                    if (direct) return direct;
                    const onclick = target.getAttribute("onclick") || "";
                    const match = onclick.match(/'(https?:[^']+)'/);
                    return match ? match[1] : "";
                }""",
                name,
            )
            return value if isinstance(value, str) else ""
        except PlaywrightError:
            return ""

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
                href = (
                    open_notice.get_attribute("data-url")
                    or open_notice.get_attribute("dataurl")
                    or title.get_attribute("href")
                    or ""
                )
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
        if any(keyword in normalized for keyword in self.config.get("inbox_exclude_keywords", [])):
            return False
        return any(keyword in normalized for keyword in self.config["inbox_keywords"])

    def iter_body_texts(self, timeout_ms: int = 2_000) -> List[str]:
        if not self.page:
            return []
        texts: List[str] = []
        for root in [self.page, *self.page.frames]:
            try:
                texts.append(root.locator("body").inner_text(timeout=timeout_ms))
            except (PlaywrightTimeoutError, PlaywrightError):
                continue
        return texts

    def is_submitted_result_page(self) -> bool:
        for body_text in self.iter_body_texts():
            if has_submitted_result_markers(body_text):
                LOGGER.info("Detected submitted assignment result page by answer/result markers.")
                return True
        return False

    def extract_low_score_retry_marker(self) -> Optional[str]:
        for body_text in self.iter_body_texts():
            if has_low_score_retry_marker(body_text):
                return re.sub(r"\s+", " ", body_text).strip()[:200]
        return None

    def handle_submitted_result_candidate(self, inbox_url: str) -> Optional[str]:
        if not self.is_submitted_result_page():
            return None

        LOGGER.info("Detected already-submitted result page; inspecting score before skipping candidate.")
        if self.config.get("retry_with_visible_correct_answers") and self.extract_low_score_retry_marker():
            completed_before = self.completed_assignments
            result = self.retry_submitted_result_page_with_visible_correct_answers()
            LOGGER.info("完成候选处理: %s result=%s", time.strftime("%Y-%m-%d %H:%M:%S"), result)
            if self.halt_requested:
                self.pause_for_low_confidence_halt()
                return "halt"
            try:
                self.page.goto(inbox_url, wait_until="domcontentloaded")
                self.wait_for_page_settle("return to inbox")
            except PlaywrightError as exc:
                LOGGER.warning("Failed returning to inbox url=%s reason=%s", inbox_url, exc)
            if result and self.completed_assignments > completed_before:
                return "processed_completed"
            return "processed" if result else "failed"
        self.inspect_score_after_submit()
        if self.halt_requested:
            self.pause_for_low_confidence_halt()
            return "halt"
        return "completed_or_closed"

    def process_inbox_candidate(self, candidate: Dict[str, str]) -> str:
        if not self.page:
            return "failed"

        href = candidate.get("href", "")
        inbox_url = self.page.url
        self.assignment_risks = []
        self.current_candidate_title = candidate.get("title", "")
        LOGGER.info("开始处理 Inbox 作业候选: %s", time.strftime("%Y-%m-%d %H:%M:%S"))
        if not href:
            if not self.click_inbox_candidate_by_index(candidate.get("index", "")):
                LOGGER.warning("Inbox 候选没有 href，且无法点击，跳过。")
                return "failed"
            LOGGER.info("Opened inbox candidate by clicking current Inbox item: %s", self.page.url)
        else:
            try:
                self.page.goto(href, wait_until="domcontentloaded")
                self.wait_for_page_settle("inbox candidate page")
                LOGGER.info("Opened inbox candidate page: %s", self.page.url)
            except PlaywrightError as exc:
                LOGGER.warning("Failed to open inbox candidate href=%s reason=%s", href, exc)
                return "failed"

        extracted: Optional[QuestionData] = None
        attachment_opened = self.open_notice_assignment_attachment()
        submitted_result = self.handle_submitted_result_candidate(inbox_url)
        if submitted_result:
            return submitted_result

        extracted = self.extract_question()
        if not extracted and not attachment_opened and self.open_notice_assignment_attachment():
            submitted_result = self.handle_submitted_result_candidate(inbox_url)
            if submitted_result:
                return submitted_result
            extracted = self.extract_question()

        submitted_result = self.handle_submitted_result_candidate(inbox_url)
        if submitted_result:
            return submitted_result

        if not extracted:
            if self.is_completed_or_closed_page():
                LOGGER.info("Detected completed/closed assignment page; skipping candidate gracefully.")
                return "completed_or_closed"
            if self.is_notice_only_page():
                LOGGER.info("Detected notice-only assignment reminder with no actionable attachment; skipping candidate gracefully.")
                return "notice_only"
            else:
                self.request_manual_halt("No question DOM found on inbox candidate page; treating as unresolved candidate.")
                return "no_question"

        completed_before = self.completed_assignments
        result = self.process_all_questions(first_extracted=extracted)
        LOGGER.info("完成候选处理: %s result=%s", time.strftime("%Y-%m-%d %H:%M:%S"), result)
        if self.halt_requested:
            if self.config.get("skip_unanswerable_candidate"):
                LOGGER.warning("Current candidate halted; returning to Inbox and continuing because ASSIGNMENT_SKIP_UNANSWERABLE_CANDIDATE=true.")
                self.halt_requested = False
            else:
                self.pause_for_low_confidence_halt()
                return "halt"
        try:
            self.page.goto(inbox_url, wait_until="domcontentloaded")
            self.wait_for_page_settle("return to inbox")
        except PlaywrightError as exc:
            LOGGER.warning("Failed returning to inbox url=%s reason=%s", inbox_url, exc)
        if result and self.completed_assignments > completed_before:
            return "processed_completed"
        return "processed" if result else "failed"

    def open_notice_assignment_attachment(self) -> bool:
        if not self.page:
            return False

        attempted_urls = set()
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
            if attachment_url in attempted_urls:
                continue
            attempted_urls.add(attachment_url)

            LOGGER.info("Found notice assignment attachment URL: %s", attachment_url)
            attempts = max(1, int(self.config.get("navigation_retries", 2)) + 1)
            retry_delay = max(0.0, float(self.config.get("navigation_retry_delay_seconds", 3.0)))
            timeout_ms = max(30_000, int(self.config.get("timeout_ms", 15_000)) * 2)
            for attempt in range(1, attempts + 1):
                try:
                    self.page.goto(attachment_url, wait_until="domcontentloaded", timeout=timeout_ms)
                    self.wait_for_page_settle("notice assignment attachment")
                    LOGGER.info("Opened notice assignment attachment: %s", self.page.url)
                    return True
                except PlaywrightError as exc:
                    LOGGER.warning(
                        "Open notice assignment attachment attempt %s/%s failed: %s",
                        attempt,
                        attempts,
                        exc,
                    )
                    self.wait_for_page_settle("notice assignment attachment after failed navigation")
                    if self.extract_question():
                        LOGGER.info("Notice assignment attachment reached a question page after navigation warning: %s", self.page.url)
                        return True
                    if attempt < attempts and retry_delay:
                        self.page.wait_for_timeout(int(retry_delay * attempt * 1000))
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

        current_url = self.page.url
        parsed_url = urlparse(current_url)
        path = parsed_url.path.lower()
        if "/mooc2/work/view" in path or "/mooc2/work/prompt" in path:
            LOGGER.info("Detected completed/closed assignment page by URL: %s", current_url)
            return True

        keywords = ("已完成", "已提交", "已批阅", "作业已完成", "已结束", "暂无可做", "不能作答")
        for body_text in self.iter_body_texts():
            normalized = compact_page_text(body_text)
            if any(keyword in normalized for keyword in keywords):
                return True
        return False

    def is_notice_only_page(self) -> bool:
        if not self.page:
            return False
        parsed_url = urlparse(self.page.url)
        if not parsed_url.hostname or not parsed_url.hostname.endswith("notice.chaoxing.com"):
            return False
        if "/pc/notice/" not in parsed_url.path.lower():
            return False
        roots = [self.page, *self.page.frames]
        for root in roots:
            try:
                body_text = root.locator("body").inner_text(timeout=2_000)
            except (PlaywrightTimeoutError, PlaywrightError):
                continue
            normalized = re.sub(r"\s+", "", body_text)
            if "通知" in normalized and ("评论" in normalized or "收件人" in normalized):
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

        cap = int(self.config.get("max_questions", 120))
        probe_limit = cap + 1 if cap > 0 else None
        for selector in [".questionLi", ".question", ".question-item", "[data-question-id]", ".exam-question"]:
            containers = self.find_all_locators(selector, timeout_ms=4_000)
            if containers:
                return containers[:probe_limit] if probe_limit else containers
        current = self.current_question_container()
        return [current] if current else []

    def extract_question(self) -> Optional[QuestionData]:
        container = self.current_question_container()
        if not container:
            return None
        return self.extract_question_from_container(container)

    def extract_question_from_container(
        self,
        container: Locator,
    ) -> Optional[QuestionData]:
        media = self.capture_question_media(container)
        try:
            question_text = container.locator(self.selectors["question_text"]).first.inner_text(timeout=2_000).strip()
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            try:
                question_text = container.inner_text(timeout=2_000).strip()
            except (PlaywrightTimeoutError, PlaywrightError) as inner_exc:
                LOGGER.warning("Question extraction failed: %s / %s", exc, inner_exc)
                return None

        shared_question = self.extract_shared_option_question(container, question_text, media)
        if shared_question:
            return shared_question

        option_items = container.locator(self.selectors["option_item"]).all()
        if not option_items:
            text_controls = self.find_text_answer_controls(container)
            if text_controls:
                blank_count = len(text_controls)
                LOGGER.info("[探测到简答题] found %s text input control(s)", blank_count)
                if blank_count > 1:
                    question_text = (
                        f"{question_text}\n填空数量：{blank_count}。"
                        "请按第1空到最后一空的顺序返回 answer 数组。"
                    )
                return QuestionData(question_text, {}, "text", text_controls, media)
            option_items = self.find_all_locators(self.selectors["option_item"], timeout_ms=3_000)

        max_options = int(self.config.get("max_options_per_question", 12))
        if len(option_items) > max_options:
            LOGGER.warning(
                "Question option extraction produced too many candidates; treating as unanswerable. count=%s max=%s",
                len(option_items),
                max_options,
            )
            return None

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
        LOGGER.info("Extracted %s question with options=%s media=%s", question_type, list(options.keys()), len(media))
        return QuestionData(question_text, options, question_type, controls, media)

    def extract_shared_option_question(
        self,
        container: Locator,
        question_text: str,
        media: List[QuestionMedia],
    ) -> Optional[QuestionData]:
        try:
            shared_groups = container.locator(".B-answer-ct").all()
            if not shared_groups:
                return None
            option_rows = container.locator(".stem_answer .clearfix").all()
            if not option_rows:
                return None
        except PlaywrightError:
            return None

        options: Dict[str, str] = {}
        for row in option_rows:
            try:
                text = re.sub(r"\s+", " ", row.inner_text(timeout=1_000)).strip()
            except (PlaywrightTimeoutError, PlaywrightError):
                continue
            match = re.match(r"^([A-Z])\s*[.．、:：]?\s*(.+)$", text)
            if match:
                options[match.group(1)] = match.group(2).strip()

        controls: Dict[str, Locator] = {}
        sub_questions: List[str] = []
        allowed = set(options.keys())
        for group_index, group in enumerate(shared_groups, start=1):
            try:
                group_text = re.sub(r"\s+", " ", group.inner_text(timeout=1_000)).strip()
            except (PlaywrightTimeoutError, PlaywrightError):
                group_text = f"({group_index})"
            sub_question_text = re.sub(r"\s+[A-Z](?:\s+[A-Z])*\s*$", "", group_text).strip()
            sub_questions.append(sub_question_text or f"({group_index})")

            try:
                spans = group.locator(".B-answerCon span").all()
            except PlaywrightError:
                spans = []
            for span in spans:
                try:
                    letter = span.inner_text(timeout=1_000).strip().upper()
                except (PlaywrightTimeoutError, PlaywrightError):
                    continue
                if letter in allowed:
                    controls[f"{group_index}:{letter}"] = span

        if not options or not sub_questions:
            return None
        expected_controls = len(options) * len(sub_questions)
        if len(controls) < expected_controls:
            LOGGER.warning(
                "Shared-option question controls incomplete; options=%s sub_questions=%s controls=%s",
                len(options),
                len(sub_questions),
                len(controls),
            )
            return None

        prompt_text = (
            question_text
            + "\n共用备选项："
            + json.dumps(options, ensure_ascii=False)
            + "\n小题："
            + json.dumps(sub_questions, ensure_ascii=False)
        )
        LOGGER.info(
            "Extracted shared_options question with options=%s sub_questions=%s media=%s",
            list(options.keys()),
            len(sub_questions),
            len(media),
        )
        return QuestionData(prompt_text, options, "shared_options", controls, media, sub_questions)

    def capture_question_media(self, container: Locator) -> List[QuestionMedia]:
        if not self.config.get("ai_enable_images"):
            return []
        max_images = int(self.config.get("ai_max_images_per_question", 1))
        if max_images <= 0:
            return []

        try:
            media_nodes = container.locator(self.selectors["question_media"]).count()
        except PlaywrightError:
            media_nodes = 0
        if media_nodes <= 0:
            return []

        max_bytes = int(self.config.get("ai_max_image_bytes", 1_500_000))
        captured: List[QuestionMedia] = []
        media_locator = container.locator(self.selectors["question_media"])
        for index in range(min(media_nodes, max_images)):
            try:
                media_node = media_locator.nth(index)
                action_timeout = max(1_000, int(self.config.get("action_timeout_ms", 5_000)))
                media_node.scroll_into_view_if_needed(timeout=action_timeout)
                media_node.wait_for(state="visible", timeout=action_timeout)
                media_node.evaluate(
                    """element => {
                        if (element.tagName !== "IMG") {
                            return true;
                        }
                        const img = element;
                        if (img.complete && img.naturalWidth > 0 && img.naturalHeight > 0) {
                            return true;
                        }
                        return new Promise((resolve, reject) => {
                            const timeout = setTimeout(() => reject(new Error("image load timeout")), 5000);
                            img.addEventListener("load", () => {
                                clearTimeout(timeout);
                                resolve(true);
                            }, { once: true });
                            img.addEventListener("error", () => {
                                clearTimeout(timeout);
                                reject(new Error("image load error"));
                            }, { once: true });
                        });
                    }""",
                    timeout=action_timeout + 5_000,
                )
                box = media_node.bounding_box(timeout=action_timeout)
                if not box or box.get("width", 0) < 10 or box.get("height", 0) < 10:
                    continue
                png_bytes = media_node.screenshot(
                    type="png",
                    timeout=action_timeout,
                )
            except (PlaywrightTimeoutError, PlaywrightError) as exc:
                LOGGER.warning("Question media node screenshot failed; trying next/fallback. index=%s reason=%s", index + 1, exc)
                continue
            if len(png_bytes) > max_bytes:
                LOGGER.warning(
                    "Question media node screenshot too large; skipping. index=%s bytes=%s max=%s",
                    index + 1,
                    len(png_bytes),
                    max_bytes,
                )
                continue
            data_url = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")
            LOGGER.info(
                "Question media captured: media_nodes=%s screenshot_bytes=%s source=media-node-%s",
                media_nodes,
                len(png_bytes),
                index + 1,
            )
            captured.append(QuestionMedia(f"media-node-{index + 1}", data_url, len(png_bytes), "screenshot"))
        if captured:
            return captured

        try:
            png_bytes = container.screenshot(
                type="png",
                timeout=max(1_000, int(self.config.get("action_timeout_ms", 5_000))),
            )
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            LOGGER.warning("Question media screenshot failed; falling back to text-only. reason=%s", exc)
            return []

        if len(png_bytes) > max_bytes:
            LOGGER.warning(
                "Question media screenshot too large; falling back to text-only. bytes=%s max=%s media_nodes=%s",
                len(png_bytes),
                max_bytes,
                media_nodes,
            )
            return []

        data_url = "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")
        LOGGER.info(
            "Question media captured: media_nodes=%s screenshot_bytes=%s source=question-container",
            media_nodes,
            len(png_bytes),
        )
        return [QuestionMedia("question-container", data_url, len(png_bytes), "screenshot")]

    def find_text_answer_control(self, container: Locator) -> Optional[Locator]:
        controls = self.find_text_answer_controls(container)
        return controls.get("__text_1__") or controls.get("__text__")

    def find_text_answer_controls(self, container: Locator) -> Dict[str, Locator]:
        try:
            raw_controls = container.locator(self.selectors["text_answer_input"]).all()
        except PlaywrightError:
            return {}

        eligible: List[Locator] = []
        visible: List[Locator] = []
        for control in raw_controls:
            try:
                input_type = (control.get_attribute("type") or "").lower()
                if input_type in {"hidden", "submit", "button", "checkbox", "radio"}:
                    continue
                eligible.append(control)
                if control.is_visible():
                    visible.append(control)
            except PlaywrightError:
                continue

        selected = visible or eligible
        selected = sorted(
            enumerate(selected, start=1),
            key=lambda item: self.text_answer_control_sort_key(item[1], item[0]),
        )
        selected_controls = [control for _, control in selected]
        return {f"__text_{index}__": control for index, control in enumerate(selected_controls, start=1)}

    def text_answer_control_sort_key(self, control: Locator, fallback_index: int) -> Tuple[int, float, float, int, int]:
        try:
            key = control.evaluate(
                """(el, fallbackIndex) => {
                    const rectFor = (node) => {
                        if (!node || !node.getBoundingClientRect) {
                            return null;
                        }
                        const rect = node.getBoundingClientRect();
                        if (rect.width <= 0 || rect.height <= 0) {
                            return null;
                        }
                        return { top: rect.top, left: rect.left };
                    };
                    const cssEscape = (value) => {
                        if (window.CSS && window.CSS.escape) {
                            return window.CSS.escape(value);
                        }
                        return String(value).replace(/["\\\\]/g, "\\\\$&");
                    };
                    const candidates = [];
                    const id = el.id || "";
                    if (id) {
                        const escapedId = cssEscape(id);
                        for (const selector of [
                            `#${escapedId}_iframe`,
                            `[data-editor-id="${escapedId}"]`,
                            `[data-control-id="${escapedId}"]`,
                            `[for="${escapedId}"]`,
                        ]) {
                            const node = document.querySelector(selector);
                            if (node) {
                                candidates.push(node);
                            }
                        }
                        if (window.UE) {
                            try {
                                const editor = window.UE.getEditor(id);
                                if (editor) {
                                    if (editor.container) {
                                        candidates.push(editor.container);
                                    }
                                    if (editor.iframe) {
                                        candidates.push(editor.iframe);
                                    }
                                }
                            } catch (error) {
                                // UEditor may throw while creating missing editors; ignore for ordering.
                            }
                        }
                    }
                    candidates.push(el);
                    for (const node of candidates) {
                        const rect = rectFor(node);
                        if (rect) {
                            return {
                                visibleRank: 0,
                                top: rect.top,
                                left: rect.left,
                                ordinal: Number.MAX_SAFE_INTEGER,
                                fallbackIndex,
                            };
                        }
                    }

                    const attrs = [
                        el.id || "",
                        el.name || "",
                        el.getAttribute("data-id") || "",
                        el.getAttribute("data-index") || "",
                        el.getAttribute("data-sort") || "",
                    ].join(" ");
                    const numbers = attrs.match(/\\d+/g) || [];
                    const ordinal = numbers.length ? Number(numbers[numbers.length - 1]) : Number.MAX_SAFE_INTEGER;
                    return {
                        visibleRank: 1,
                        top: Number.MAX_SAFE_INTEGER,
                        left: Number.MAX_SAFE_INTEGER,
                        ordinal,
                        fallbackIndex,
                    };
                }""",
                fallback_index,
                timeout=self.config.get("action_timeout_ms", 5_000),
            )
            return (
                int(key.get("visibleRank", 1)),
                float(key.get("top", 9_999_999)),
                float(key.get("left", 9_999_999)),
                int(key.get("ordinal", 9_999_999)),
                int(key.get("fallbackIndex", fallback_index)),
            )
        except (PlaywrightTimeoutError, PlaywrightError, TypeError, ValueError) as exc:
            LOGGER.warning("Text answer control ordering fallback used: %s", exc)
            return (1, 9_999_999.0, 9_999_999.0, 9_999_999, fallback_index)

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
            if not self.safe_click(control, f"answer {letter}"):
                continue
            if self.verify_answer_control_selected(control, f"answer {letter}"):
                selected_any = True
            else:
                LOGGER.warning("Answer %s click did not produce a verifiable selected state.", letter)
        return selected_any

    def apply_choice_answers_exact(
        self,
        answers: List[str],
        controls: Dict[str, Locator],
        question_type: str,
    ) -> bool:
        target = {str(answer).strip().upper() for answer in answers if str(answer).strip()}
        if not target:
            LOGGER.warning("Exact choice application received no target answers.")
            return False

        missing = sorted(letter for letter in target if letter not in controls)
        if missing:
            LOGGER.warning("Exact choice answers have no matching controls: %s", missing)
            return False

        if not self.actions_allowed():
            LOGGER.info("Dry-run: would set exact answer(s) %s", sorted(target))
            return True

        success = True
        for letter in sorted(target, key=lambda item: list(controls).index(item)):
            control = controls[letter]
            if self.answer_control_is_selected(control):
                continue
            if not self.safe_click(control, f"exact answer {letter}"):
                success = False
                continue
            if not self.verify_answer_control_selected(control, f"exact answer {letter}"):
                success = False

        if question_type != "single":
            for letter, control in controls.items():
                if letter in target or not self.answer_control_is_selected(control):
                    continue
                if not self.safe_click(control, f"deselect extra answer {letter}"):
                    success = False
                    continue
                if self.answer_control_is_selected(control):
                    LOGGER.warning("Extra answer %s remained selected after deselect click.", letter)
                    success = False

        for letter, control in controls.items():
            selected = self.answer_control_is_selected(control)
            should_select = letter in target
            if selected != should_select:
                LOGGER.warning(
                    "Exact answer final state mismatch for %s: selected=%s expected=%s",
                    letter,
                    selected,
                    should_select,
                )
                success = False
        return success

    def answer_control_is_selected(self, control: Locator) -> bool:
        try:
            return bool(
                control.evaluate(
                    """el => {
                        const truthy = value => String(value || "").toLowerCase() === "true";
                        const hasSelectedClass = node => {
                            if (!node || !node.className) {
                                return false;
                            }
                            const className = String(node.className).toLowerCase();
                            return /(^|[-_\\s])(checked|selected|active|current|cur|on|choose|chosen|check)([-_\\s]|$)/.test(className);
                        };
                        const isCheckedInput = node => {
                            return node
                                && node.matches
                                && node.matches("input[type='radio'], input[type='checkbox']")
                                && node.checked;
                        };
                        if (isCheckedInput(el) || truthy(el.getAttribute("aria-checked")) || hasSelectedClass(el)) {
                            return true;
                        }
                        const input = el.querySelector && el.querySelector("input[type='radio'], input[type='checkbox']");
                        if (isCheckedInput(input)) {
                            return true;
                        }
                        const ariaNode = el.querySelector && el.querySelector("[aria-checked='true']");
                        if (ariaNode) {
                            return true;
                        }
                        let node = el.parentElement;
                        let depth = 0;
                        while (node && depth < 4) {
                            if (hasSelectedClass(node)) {
                                return true;
                            }
                            node = node.parentElement;
                            depth += 1;
                        }
                        return false;
                    }""",
                    timeout=self.config.get("action_timeout_ms", 5_000),
                )
            )
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            LOGGER.warning("Selected-state read failed: %s", exc)
            return False

    def verify_answer_control_selected(self, control: Locator, description: str) -> bool:
        if self.answer_control_is_selected(control):
            return True
        LOGGER.warning("Selected-state verification failed for %s", description)
        return False

    def apply_text_answer(self, answer_text: str, controls: Dict[str, Locator]) -> bool:
        return self.apply_text_answers([answer_text], controls)

    def apply_text_answers(self, answers: List[str], controls: Dict[str, Locator]) -> bool:
        text_controls = [
            (key, controls[key])
            for key in sorted(controls, key=self.text_answer_key_sort_key)
            if key.startswith("__text_")
        ]
        if not text_controls and "__text__" in controls:
            text_controls = [("__text__", controls["__text__"])]
        if not text_controls:
            LOGGER.warning("Text question has no input control; skipping text answer.")
            return False

        if len(answers) != len(text_controls):
            LOGGER.warning(
                "Text answer count mismatch: answers=%s expected=%s",
                answers,
                len(text_controls),
            )
            return False

        applied = 0
        for index, ((_, control), answer_text) in enumerate(zip(text_controls, answers), start=1):
            if self.apply_single_text_answer(str(answer_text), control, index):
                applied += 1
        return applied == len(text_controls)

    def apply_single_text_answer(self, answer_text: str, control: Locator, index: int) -> bool:
        answer_text = answer_text.strip()
        if not answer_text:
            LOGGER.warning("Text answer is empty; skipping text input.")
            return False

        LOGGER.info("[探测到简答题] 准备填入第 %s 空：%s", index, answer_text)
        if not self.actions_allowed():
            return True

        try:
            self.random_delay()
            if control.is_visible(timeout=500):
                control.fill(answer_text, timeout=self.config.get("action_timeout_ms", 5_000))
                LOGGER.info("Filled text answer #%s", index)
                return True
            LOGGER.info("Text answer #%s control is hidden; using JS value fallback.", index)
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            LOGGER.warning("Fill text answer #%s precheck/fill failed; trying JS value fallback: %s", index, exc)
        try:
            control.evaluate(
                """(el, value) => {
                    el.value = value;
                    el.textContent = value;
                    el.dispatchEvent(new Event("input", { bubbles: true }));
                    el.dispatchEvent(new Event("change", { bubbles: true }));
                    if (window.UE && el.id) {
                        try {
                            const editor = window.UE.getEditor(el.id);
                            if (editor && editor.ready) {
                                editor.ready(() => {
                                    editor.setContent(value || "");
                                    editor.sync();
                                });
                            } else if (editor) {
                                editor.setContent(value || "");
                                editor.sync();
                            }
                        } catch (error) {
                            console.log(error);
                        }
                    }
                }""",
                answer_text,
                timeout=self.config.get("action_timeout_ms", 5_000),
            )
            LOGGER.info("Filled hidden text answer #%s via JS fallback", index)
            return True
        except (PlaywrightTimeoutError, PlaywrightError) as fallback_exc:
            LOGGER.warning("Fill text answer #%s JS fallback failed: %s", index, fallback_exc)
            return False

    def text_answer_key_sort_key(self, key: str) -> Tuple[int, str]:
        match = re.fullmatch(r"__text_(\d+)__", key)
        if not match:
            return (0, key)
        return (int(match.group(1)), key)

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

    def guard_risk_budget_before_submit(self) -> bool:
        if not self.config.get("submit_within_risk_budget", True):
            return True
        total_risk = sum(float(item.get("risk_points", 0.0)) for item in self.assignment_risks)
        risk_budget = float(self.config.get("risk_budget_points", 5.0))
        if self.assignment_risks:
            risk_summary = "; ".join(
                (
                    f"#{item.get('index') or '?'}:{item.get('question_type')} "
                    f"risk={float(item.get('risk_points', 0.0)):.2f} "
                    f"conf={item.get('confidence')} consensus={float(item.get('consensus_ratio', 0.0)):.2f} "
                    f"answer={'/'.join(item.get('answers') or [])}"
                )
                for item in self.assignment_risks
            )
            LOGGER.warning(
                "Pre-submit risk summary: total_risk=%.2f budget=%.2f items=%s",
                total_risk,
                risk_budget,
                risk_summary,
            )
        else:
            LOGGER.info("Pre-submit risk summary: no accepted low-confidence risk items.")

        if total_risk > risk_budget:
            self.request_manual_halt(
                f"提交前风险预算超限：estimated_risk={total_risk:.2f} > budget={risk_budget:.2f}。"
            )
            return False
        return True

    def reviewed_answer_file(self) -> str:
        return str(self.config.get("reviewed_answer_file") or "").strip()

    def load_reviewed_answer_map(self) -> Dict[int, List[str]]:
        if self._reviewed_answer_map is not None:
            return self._reviewed_answer_map

        path = self.reviewed_answer_file()
        if not path:
            self._reviewed_answer_map = {}
            return self._reviewed_answer_map

        with open(path, "r", encoding="utf-8") as handle:
            raw_data = json.load(handle)

        expected_assignment = ""
        if isinstance(raw_data, dict):
            expected_assignment = str(raw_data.get("assignment") or raw_data.get("title") or "").strip()
            candidates = raw_data.get("candidates")
            if isinstance(candidates, list):
                for candidate in candidates:
                    if not isinstance(candidate, dict):
                        continue
                    if candidate.get("outcome") == "pre_submit_review" or candidate.get("rows") or candidate.get("answers"):
                        raw_data = candidate
                        expected_assignment = str(
                            raw_data.get("assignment") or raw_data.get("title") or expected_assignment
                        ).strip()
                        break
            entries = raw_data.get("answers") or raw_data.get("rows") or raw_data
        else:
            entries = raw_data

        if expected_assignment and self.current_candidate_title and not self.assignment_title_matches(
            expected_assignment,
            self.current_candidate_title,
        ):
            self.request_manual_halt(
                "Reviewed answer file does not match current assignment candidate; stopping before submit. "
                f"reviewed={expected_assignment} current={self.current_candidate_title}"
            )
            self._reviewed_answer_map = {}
            return self._reviewed_answer_map

        answer_map: Dict[int, List[str]] = {}
        if isinstance(entries, dict):
            for key, value in entries.items():
                index = self.parse_reviewed_answer_index(key)
                if index is None:
                    continue
                answer_map[index] = self.normalize_reviewed_answer_entry(value)
        elif isinstance(entries, list):
            for row in entries:
                if not isinstance(row, dict):
                    continue
                index = self.parse_reviewed_answer_index(row.get("i", row.get("index")))
                if index is None:
                    continue
                value = row.get("answers", row.get("selected", row.get("answer")))
                answer_map[index] = self.normalize_reviewed_answer_entry(value)

        self._reviewed_answer_map = answer_map
        LOGGER.info("Loaded reviewed answer file %s with %s question(s).", path, len(answer_map))
        return self._reviewed_answer_map

    def assignment_title_matches(self, reviewed_title: str, current_title: str) -> bool:
        reviewed = compact_page_text(reviewed_title)
        current = compact_page_text(current_title)
        return bool(reviewed and current and (reviewed in current or current in reviewed))

    def parse_reviewed_answer_index(self, value: Any) -> Optional[int]:
        match = re.search(r"\d+", str(value or ""))
        if not match:
            return None
        try:
            return int(match.group(0))
        except ValueError:
            return None

    def normalize_reviewed_answer_entry(self, value: Any) -> List[str]:
        if isinstance(value, dict):
            value = value.get("answers", value.get("selected", value.get("answer")))
        if isinstance(value, str):
            raw_items = [item for item in re.split(r"[/,，;；\n]+", value) if item.strip()]
        elif isinstance(value, list):
            raw_items = [str(item) for item in value if str(item).strip()]
        else:
            raw_items = [str(value)] if value is not None and str(value).strip() else []

        normalized: List[str] = []
        for item in raw_items:
            text = item.strip()
            indexed_match = re.fullmatch(r"\d+\s*:\s*(.+)", text)
            if indexed_match:
                text = indexed_match.group(1).strip()
            if text:
                normalized.append(text)
        return normalized

    def reviewed_answers_for_question(
        self,
        index: int,
        question_type: str,
        options: Dict[str, str],
    ) -> Optional[List[str]]:
        if not self.reviewed_answer_file():
            return None
        answer_map = self.load_reviewed_answer_map()
        raw_answers = answer_map.get(index)
        if not raw_answers:
            self.request_manual_halt(f"Reviewed answer file is missing question #{index}; stopping before submit.")
            return []
        answers = normalize_ai_answers(raw_answers, question_type, options)
        if not answers:
            self.request_manual_halt(
                f"Reviewed answer file has no usable answer for question #{index}: {raw_answers}"
            )
            return []
        return answers

    def manual_review_required_before_submit(self) -> bool:
        return bool(self.config.get("require_manual_review_before_submit")) and not self.reviewed_answer_file()

    def write_pre_submit_review_report(
        self,
        answer_summary: List[Dict[str, Any]],
        processed: int,
        selected: int,
    ) -> str:
        output_dir = str(self.config.get("review_output_dir") or "logs/reviews")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(output_dir, f"assignment_pre_submit_review_{timestamp}.json")
        report = {
            "outcome": "pre_submit_review_required",
            "url": self.page.url if self.page else "",
            "processed": processed,
            "selected_or_mapped": selected,
            "risks": self.assignment_risks,
            "answers": {
                str(row["index"]): row["answers"]
                for row in answer_summary
                if row.get("applied")
            },
            "rows": answer_summary,
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        return path

    def submit_current_page(self) -> bool:
        if not self.page:
            raise RuntimeError("Cannot submit without an initialized page.")
        if not self.actions_allowed() or not self.config["allow_submission"]:
            LOGGER.info("Dry-run: would click submit")
            return True
        if not self.guard_risk_budget_before_submit():
            self.pause_for_low_confidence_halt()
            return False

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
            if not self.wait_for_submission_completion():
                raise RuntimeError(f"Submit completion was not verified after click. url={self.page.url}")
            self.completed_assignments += 1
            self.inspect_score_after_submit()
            return True
        except (PlaywrightTimeoutError, PlaywrightError) as exc:
            raise RuntimeError(f"Submit action failed: {exc}") from exc

    def wait_for_submission_completion(self) -> bool:
        if not self.page:
            return False
        deadline = time.monotonic() + max(1_000, int(self.config.get("submit_completion_timeout_ms", 12_000))) / 1000
        while time.monotonic() < deadline:
            if self.is_completed_or_closed_page():
                LOGGER.info("[Action] 提交完成已通过页面完成态验证。")
                return True
            if self.extract_score_info():
                LOGGER.info("[Action] 提交完成已通过分数信息验证。")
                return True
            if self.is_submitted_result_page():
                LOGGER.info("[Action] 提交完成已通过答案结果态验证。")
                return True
            try:
                submit_button = self.find_locator(
                    self.selectors["submit_button"],
                    state="visible",
                    timeout_ms=300,
                    log_missing=False,
                )
                if not submit_button and "dowork" not in (self.page.url or "").lower():
                    LOGGER.info("[Action] 提交完成已通过提交按钮消失/URL 变化验证。")
                    return True
            except PlaywrightError:
                if "dowork" not in (self.page.url or "").lower():
                    LOGGER.info("[Action] 提交完成已通过 URL 变化验证。")
                    return True
            self.page.wait_for_timeout(500)
        LOGGER.warning("[Action] 提交完成验证失败，当前 url=%s", self.page.url)
        return False

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
        extracted: Optional[QuestionData] = None,
    ) -> bool:
        extracted = extracted or self.extract_question()
        if not extracted:
            return False

        question_text = extracted.text
        options = extracted.options
        question_type = extracted.question_type
        controls = extracted.controls
        expected_answer_count = self.expected_answer_count(extracted)
        LOGGER.info("Question type=%s text=%s", question_type, question_text[:80])
        answers = self.decide_answers(
            question_text,
            options,
            question_type,
            extracted.media,
            question_index=None,
            sub_question_count=expected_answer_count,
        )
        if not answers:
            LOGGER.warning("No usable AI answer; skipping question")
            if self.halt_requested:
                return self.pause_for_low_confidence_halt()
            return self.click_next_or_submit()

        if question_type == "text":
            self.apply_text_answers(answers, controls)
        elif question_type == "shared_options":
            self.apply_shared_option_answers(answers, controls, len(extracted.sub_questions or []))
        else:
            self.apply_answers(answers, controls)
        LOGGER.info("Question final answer type=%s answer=%s", question_type, answers)
        return self.click_next_or_submit()

    def process_all_questions(
        self,
        first_extracted: Optional[QuestionData] = None,
    ) -> bool:
        containers = self.all_question_containers()
        if not containers:
            if not first_extracted:
                return False
            containers = []

        processed = 0
        selected = 0
        answer_summary: List[Dict[str, Any]] = []
        capped_by_max_questions = False
        if first_extracted and not containers:
            containers_to_process: List[Optional[Locator]] = [None]
        else:
            containers_to_process = containers

        for index, container in enumerate(containers_to_process, start=1):
            if index > self.config["max_questions"]:
                LOGGER.info("Reached max_questions=%s; stopping question loop.", self.config["max_questions"])
                capped_by_max_questions = True
                break

            extracted = first_extracted if container is None else self.extract_question_from_container(container)
            first_extracted = None
            if not extracted:
                LOGGER.warning("Question #%s extraction failed; skipping.", index)
                if self.config.get("stop_on_unanswerable"):
                    self.request_manual_halt(f"第 {index} 题题目提取失败，已停止以避免漏答提交。")
                    self.pause_for_low_confidence_halt()
                    return False
                continue

            question_text = extracted.text
            options = extracted.options
            question_type = extracted.question_type
            controls = extracted.controls
            expected_answer_count = self.expected_answer_count(extracted)
            processed += 1
            LOGGER.info("Question #%s type=%s text=%s", index, question_type, question_text[:80])
            reviewed_answers = self.reviewed_answers_for_question(index, question_type, options)
            if reviewed_answers is not None:
                answers = reviewed_answers
                LOGGER.info("Question #%s using reviewed answer(s): %s", index, answers)
            else:
                answers = self.decide_answers(
                    question_text,
                    options,
                    question_type,
                    extracted.media,
                    question_index=index,
                    sub_question_count=expected_answer_count,
                )
            if not answers:
                LOGGER.warning("Question #%s has no usable answer; skipping.", index)
                if self.halt_requested:
                    self.pause_for_low_confidence_halt()
                    return False
                if self.config.get("stop_on_unanswerable"):
                    self.request_manual_halt(f"第 {index} 题没有可用答案，已停止以避免漏答提交。")
                    self.pause_for_low_confidence_halt()
                    return False
                continue
            if question_type == "text":
                applied = self.apply_text_answers(answers, controls)
            elif question_type == "shared_options":
                applied = self.apply_shared_option_answers(answers, controls, len(extracted.sub_questions or []))
            else:
                applied = self.apply_answers(answers, controls)
            answer_summary.append(
                {
                    "index": index,
                    "question_type": question_type,
                    "answers": answers,
                    "applied": applied,
                    "question": re.sub(r"\s+", " ", question_text).strip(),
                    "options": options,
                }
            )
            if applied:
                selected += 1

        LOGGER.info("Processed %s question(s); selected/mapped %s question(s).", processed, selected)
        if answer_summary:
            summary_text = "; ".join(
                (
                    f"#{row['index']}:{row['question_type']}:{'/'.join(row['answers'])}:"
                    f"{'applied' if row['applied'] else 'not-applied'}"
                )
                for row in answer_summary
            )
            LOGGER.info("Answer summary before next/submit: %s", summary_text)
        if selected < processed:
            LOGGER.warning("Question loop incomplete: processed=%s selected_or_mapped=%s", processed, selected)
            if self.config.get("stop_on_unanswerable"):
                self.request_manual_halt(
                    f"检测到漏答或未成功映射：processed={processed} selected_or_mapped={selected}，已停止提交。"
                )
                self.pause_for_low_confidence_halt()
                return False
            if self.config.get("block_on_incomplete"):
                print("\n" + "=" * 60)
                print("检测到漏答，已按 ASSIGNMENT_BLOCK_ON_INCOMPLETE=true 暂停。")
                print("请在浏览器中手动检查后再继续。")
                print("=" * 60 + "\n")
                time.sleep(max(0, int(self.config.get("incomplete_block_seconds", 7200))))
                return False
        if capped_by_max_questions:
            self.request_manual_halt(
                f"题目数量超过 ASSIGNMENT_MAX_QUESTIONS={self.config['max_questions']}，已停止提交以避免漏答。"
            )
            self.pause_for_low_confidence_halt()
            return False
        if processed == 0:
            return False
        if self.manual_review_required_before_submit():
            report_path = self.write_pre_submit_review_report(answer_summary, processed, selected)
            self.request_manual_halt(
                "提交前人工复核报告已生成，未提交。"
                f"review_file={report_path}；复核后用 ASSIGNMENT_REVIEWED_ANSWER_FILE 指向修正后的文件再提交。"
            )
            self.pause_for_low_confidence_halt()
            return False
        return self.click_next_or_submit()

    def parse_visible_correct_answer_letters(self, text: str) -> List[str]:
        normalized = unicodedata.normalize("NFKC", text or "")
        match = re.search(
            r"正确答案\s*[:：]\s*([A-Z](?:\s*[,，、/\s]*[A-Z])*)",
            normalized,
            flags=re.IGNORECASE,
        )
        if not match:
            return []
        return re.findall(r"[A-Z]", match.group(1).upper())

    def retry_submitted_result_page_with_visible_correct_answers(self) -> bool:
        containers = self.all_question_containers()
        if not containers:
            self.request_manual_halt("低分重做页没有可解析的题目容器，无法按可见正确答案重提。")
            return False

        processed = 0
        applied_count = 0
        answer_summary: List[Tuple[int, str, List[str], bool]] = []
        for index, container in enumerate(containers, start=1):
            if index > self.config["max_questions"]:
                self.request_manual_halt(
                    f"重做页题目数量超过 ASSIGNMENT_MAX_QUESTIONS={self.config['max_questions']}，已停止提交。"
                )
                return False

            extracted = self.extract_question_from_container(container)
            if not extracted:
                self.request_manual_halt(f"重做页第 {index} 题题目提取失败，无法安全重提。")
                return False
            if extracted.question_type not in {"single", "multiple"}:
                self.request_manual_halt(
                    f"重做页第 {index} 题类型 {extracted.question_type} 暂不支持按可见正确答案自动重提。"
                )
                return False

            try:
                container_text = container.inner_text(timeout=1_000)
            except (PlaywrightTimeoutError, PlaywrightError) as exc:
                self.request_manual_halt(f"重做页第 {index} 题读取正确答案失败：{exc}")
                return False

            correct_letters = self.parse_visible_correct_answer_letters(container_text)
            answers = normalize_ai_answers(correct_letters, extracted.question_type, extracted.options)
            if not answers:
                self.request_manual_halt(f"重做页第 {index} 题没有可解析的可见正确答案，已停止重提。")
                return False

            processed += 1
            LOGGER.info("Retry question #%s with visible correct answer(s): %s", index, answers)
            applied = self.apply_choice_answers_exact(answers, extracted.controls, extracted.question_type)
            answer_summary.append((index, extracted.question_type, answers, applied))
            if applied:
                applied_count += 1

        LOGGER.info(
            "Visible-correct retry processed %s question(s); selected/mapped %s question(s).",
            processed,
            applied_count,
        )
        if answer_summary:
            summary_text = "; ".join(
                f"#{index}:{question_type}:{'/'.join(answers)}:{'applied' if applied else 'not-applied'}"
                for index, question_type, answers, applied in answer_summary
            )
            LOGGER.info("Visible-correct retry answer summary before submit: %s", summary_text)
        if not processed or applied_count < processed:
            self.request_manual_halt(
                f"重做页答案映射不完整：processed={processed} selected_or_mapped={applied_count}，已停止提交。"
            )
            return False
        return self.submit_current_page()

    def decide_answers(
        self,
        question_text: str,
        options: Dict[str, str],
        question_type: str,
        media: Optional[List[QuestionMedia]] = None,
        question_index: Optional[int] = None,
        sub_question_count: int = 0,
    ) -> Optional[List[str]]:
        if self.live_ai_allowed():
            decision = ask_ai_brain_decision(question_text, options, question_type, self.config, media)
            if not decision:
                return None
            self.record_ai_decision_risk(question_index, question_text, question_type, decision)
            if decision.low_confidence and self.config.get("stop_on_low_confidence"):
                self.request_low_confidence_halt(decision, question_text)
                return None
            answers = decision.answers
            if question_type == "text" and sub_question_count > 1 and len(answers) == 1:
                split_answers = [
                    item.strip()
                    for item in re.split(r"[,，;；\n]+", answers[0])
                    if item.strip()
                ]
                if len(split_answers) == sub_question_count:
                    answers = split_answers
            return answers

        first_option = next(iter(options), None)
        if question_type == "text":
            count = max(1, sub_question_count)
            LOGGER.info(
                "Dry-run real-site mode: live AI disabled; would send text question to AI in authorized staging. "
                "Using deterministic placeholder text for %s fill path(s).",
                count,
            )
            return ["dry-run text answer placeholder"] * count
        if first_option:
            if question_type == "shared_options":
                count = max(1, sub_question_count)
                LOGGER.info(
                    "Dry-run real-site mode: live AI disabled; would send shared-option question to AI in authorized staging. "
                    "Using deterministic mock answer %s repeated %s time(s) for mapping test.",
                    first_option,
                    count,
                )
                return [first_option] * count
            LOGGER.info(
                "Dry-run real-site mode: live AI disabled; would send question to AI in authorized staging. "
                "Using deterministic mock answer %s for mapping test.",
                first_option,
            )
            return [first_option]
        return None

    def expected_answer_count(self, extracted: QuestionData) -> int:
        if extracted.question_type == "shared_options":
            return len(extracted.sub_questions or [])
        if extracted.question_type == "text":
            return sum(1 for key in extracted.controls if key.startswith("__text_")) or (
                1 if "__text__" in extracted.controls else 0
            )
        return 0

    def record_ai_decision_risk(
        self,
        question_index: Optional[int],
        question_text: str,
        question_type: str,
        decision: AIAnswerResult,
    ) -> None:
        if not decision.review_required and not decision.accepted_with_risk:
            return
        if decision.low_confidence:
            return
        if not decision.accepted_with_risk:
            return

        points = self.estimate_question_points(question_text)
        decision.risk_points = points
        risk_item = {
            "index": question_index,
            "question_type": question_type,
            "answers": decision.answers,
            "confidence": decision.confidence,
            "consensus_ratio": decision.consensus_ratio,
            "risk_points": points,
            "reason": decision.reason,
            "question": re.sub(r"\s+", " ", question_text).strip()[:120],
        }
        self.assignment_risks.append(risk_item)
        LOGGER.warning(
            "Risk accepted for question #%s: points=%.2f confidence=%s consensus=%.2f answer=%s reason=%s",
            question_index if question_index is not None else "?",
            points,
            decision.confidence,
            decision.consensus_ratio,
            decision.answers,
            decision.reason,
        )

    def estimate_question_points(self, question_text: str) -> float:
        match = re.search(r"(\d+(?:\.\d+)?)\s*分", question_text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return 1.0

    def apply_shared_option_answers(
        self,
        answers: List[str],
        controls: Dict[str, Locator],
        sub_question_count: int,
    ) -> bool:
        if sub_question_count <= 0:
            LOGGER.warning("Shared-option question has no sub-question count; skipping.")
            return False
        if len(answers) != sub_question_count:
            LOGGER.warning(
                "Shared-option answer count mismatch: answers=%s expected=%s",
                answers,
                sub_question_count,
            )
            return False

        applied = 0
        for index, answer in enumerate(answers, start=1):
            letter = str(answer).strip().upper()
            control = controls.get(f"{index}:{letter}")
            if not control:
                LOGGER.warning("No shared-option control for sub-question %s answer %s", index, letter)
                continue
            if not self.actions_allowed():
                LOGGER.info("Dry-run: would click shared-option #%s answer %s", index, letter)
                applied += 1
                continue
            description = f"shared-option #{index} answer {letter}"
            if self.safe_click(control, description) and self.verify_answer_control_selected(control, description):
                applied += 1
            else:
                LOGGER.warning("Shared-option #%s answer %s did not produce a verifiable selected state.", index, letter)
        return applied == sub_question_count

    def request_low_confidence_halt(self, decision: AIAnswerResult, question_text: str) -> None:
        self.halt_requested = True
        question_preview = re.sub(r"\s+", " ", question_text).strip()[:120]
        self.halt_reason = (
            f"低置信度答案，已停止自动提交。answer={decision.answers} "
            f"confidence={decision.confidence} consensus={decision.consensus_ratio:.2f} "
            f"attempts={decision.attempts} reason={decision.reason or '<none>'} question={question_preview}"
        )
        LOGGER.warning(self.halt_reason)

    def request_manual_halt(self, reason: str) -> None:
        self.halt_requested = True
        self.halt_reason = reason
        LOGGER.warning(reason)

    def request_low_score_halt(self, score: float, total: float, text_snippet: str) -> None:
        threshold = float(self.config.get("min_acceptable_score", 80.0))
        self.halt_requested = True
        self.halt_reason = (
            f"提交后检测到成绩偏低，已停止继续扫描。score={score:g}/{total:g} "
            f"threshold={threshold:g} page_text={text_snippet}"
        )
        LOGGER.warning(self.halt_reason)

    def request_low_score_marker_halt(self, text_snippet: str) -> None:
        threshold = float(self.config.get("min_acceptable_score", 80.0))
        self.halt_requested = True
        self.halt_reason = (
            "提交后检测到未达到及格线/重做提示，已停止继续扫描。"
            f"threshold={threshold:g} page_text={text_snippet}"
        )
        LOGGER.warning(self.halt_reason)

    def inspect_score_after_submit(self) -> None:
        if not self.page or not self.config.get("stop_on_low_score"):
            return
        score_info = self.extract_score_info()
        if not score_info:
            retry_marker = self.extract_low_score_retry_marker()
            if retry_marker:
                self.request_low_score_marker_halt(retry_marker)
                return
            LOGGER.info("No score detected after submit; continuing.")
            return
        score, total, snippet = score_info
        percent_score = score / total * 100 if total > 0 else score
        LOGGER.info("Detected assignment score: %s/%s (%.1f%%)", score, total, percent_score)
        if percent_score < float(self.config.get("min_acceptable_score", 80.0)):
            self.request_low_score_halt(score, total, snippet)

    def extract_score_info(self) -> Optional[Tuple[float, float, str]]:
        if not self.page:
            return None
        for body_text in self.iter_body_texts():
            normalized = re.sub(r"\s+", " ", body_text).strip()
            score = self.parse_score_text(normalized)
            if score:
                snippet = normalized[:200]
                return score[0], score[1], snippet
        return None

    def parse_score_text(self, text: str) -> Optional[Tuple[float, float]]:
        patterns = [
            r"(?:成绩|得分|分数|score)[:：]?\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)",
            r"(?:成绩|得分|分数|score)[:：]?\s*(\d+(?:\.\d+)?)\s*分",
            r"(?:^|\s)(\d+(?:\.\d+)?)\s*分\s*提交时间",
            r"(?:总分|满分)[:：]?\s*(\d+(?:\.\d+)?).*?(?:得分|成绩|分数)[:：]?\s*(\d+(?:\.\d+)?)",
            r"(?:得分|成绩|分数)[:：]?\s*(\d+(?:\.\d+)?).*?(?:总分|满分)[:：]?\s*(\d+(?:\.\d+)?)",
        ]
        for index, pattern in enumerate(patterns):
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            first = float(match.group(1))
            second = float(match.group(2)) if len(match.groups()) >= 2 else 100.0
            if index == 3:
                return second, first
            return first, second
        return None

    def pause_for_low_confidence_halt(self) -> bool:
        if self._halt_pause_handled:
            return False
        self._halt_pause_handled = True
        print("\n" + "=" * 72)
        print("检测到需要人工检查的情况，已停止继续答题或提交。")
        print(self.halt_reason or "请手动检查当前页面答案。")
        print("=" * 72 + "\n")
        if self.config.get("hold_browser_on_low_confidence") and not self.config.get("headless"):
            input("浏览器已暂停在当前页面。检查完后按回车结束程序...")
        return False

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
                    if self.config.get("exit_when_no_unsubmitted"):
                        LOGGER.info("ASSIGNMENT_EXIT_WHEN_NO_UNSUBMITTED=true; exiting because no assignment candidates were found.")
                        return
                max_candidates = self.config.get("max_candidates_per_round", 0)
                candidates_to_process = candidates[:max_candidates] if max_candidates else candidates
                if max_candidates and len(candidates) > max_candidates:
                    LOGGER.info(
                        "Limiting this scan to %s candidate(s); %s remaining candidate(s) left untouched.",
                        max_candidates,
                        len(candidates) - max_candidates,
                    )
                outcomes: List[str] = []
                for candidate in candidates_to_process:
                    outcome = self.process_inbox_candidate(candidate)
                    outcomes.append(outcome)
                    LOGGER.info("Candidate outcome: %s", outcome)
                    if self.halt_requested:
                        LOGGER.warning("Monitor stopped because a guard halt was requested: %s", self.halt_reason)
                        return
                LOGGER.info("Monitor scan round %s completed at %s", rounds_completed, time.strftime("%Y-%m-%d %H:%M:%S"))

                if (
                    self.config.get("exit_when_no_unsubmitted")
                    and candidates_to_process
                    and all(outcome in {"completed_or_closed", "notice_only", "processed_completed"} for outcome in outcomes)
                    and (not max_candidates or len(candidates) <= max_candidates)
                ):
                    LOGGER.info(
                        "ASSIGNMENT_EXIT_WHEN_NO_UNSUBMITTED=true; all scanned assignment candidates are completed/closed."
                    )
                    return

                max_rounds = self.config.get("max_scan_rounds", 0)
                if max_rounds and rounds_completed >= max_rounds:
                    LOGGER.info("Reached max_scan_rounds=%s; exiting monitor.", max_rounds)

                    if self.config.get("hold_browser_on_exit") and not self.config.get("allow_submission"):
                        print("\n" + "="*50)
                        print("答题已完成，浏览器已悬停。")
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
            self.close()

if __name__ == "__main__":
    AssignmentAutoTester(CONFIG).run_monitor()
