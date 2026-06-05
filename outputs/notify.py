"""Feishu / DingTalk webhook notification — rating & review alerts."""

from __future__ import annotations

import logging
from datetime import datetime

import requests

from config.settings import AppConfig

logger = logging.getLogger(__name__)


def send_alert(
    alerts: list[dict],
    sentiment_summary: list[dict],
    config: AppConfig,
) -> bool:
    if not config.notify.enabled or not config.notify.webhook_url:
        logger.info("Notification disabled or no webhook URL configured.")
        return False

    if not alerts and not _has_negative_sentiment(sentiment_summary):
        logger.info("No alerts to send.")
        return True

    blocks = _build_feishu_blocks(alerts, sentiment_summary)
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "App Store 竞品监控预警"},
                "template": "red" if alerts else "blue",
            },
            "elements": blocks,
        },
    }

    try:
        resp = requests.post(config.notify.webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Notification sent successfully.")
        return True
    except requests.RequestException as e:
        logger.error("Notification failed: %s", e)
        return False


def _has_negative_sentiment(sentiment: list[dict]) -> bool:
    return any(s.get("negative_pct", 0) > 25 for s in sentiment)


def _build_feishu_blocks(alerts: list[dict], sentiment: list[dict]) -> list[dict]:
    blocks = []

    now = datetime.now().strftime("%m-%d %H:%M")
    blocks.append({"tag": "div", "text": {"tag": "lark_md", "content": f"监控时间：{now}"}})
    blocks.append({"tag": "hr"})

    if alerts:
        alert_lines = "\n".join(
            f"- {a['name']}：{'↑' if a['direction'] == 'up' else '↓'}{abs(a['change']):.2f}（{a['previous_rating']}★→{a['current_rating']}★）"
            for a in alerts[:5]
        )
        blocks.append({"tag": "div", "text": {"tag": "lark_md", "content": f"**评分异动**\n{alert_lines}"}})

    for s in sentiment:
        if s.get("negative_pct", 0) > 25:
            blocks.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**口碑预警**\n{s['name']} 差评率 {s['negative_pct']}%\n负面关键词：{'、'.join(s.get('top_negative_words', [])[:5])}",
                },
            })

    blocks.append({"tag": "hr"})
    blocks.append({"tag": "note", "elements": [{"tag": "plain_text", "content": "App Store 竞品监控系统 · 自动生成"}]})

    return blocks
