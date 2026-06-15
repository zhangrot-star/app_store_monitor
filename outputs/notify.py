"""Feishu / DingTalk webhook notification — 银行信用卡竞品监控预警."""

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
    activity_data: dict | None = None,
) -> bool:
    if not config.notify.enabled or not config.notify.webhook_url:
        logger.info("Notification disabled or no webhook URL configured.")
        return False

    has_alerts = bool(alerts)
    has_negative = _has_negative_sentiment(sentiment_summary)
    has_risk = _has_risk_alerts(activity_data)

    if not has_alerts and not has_negative and not has_risk:
        logger.info("No alerts to send.")
        return True

    blocks = _build_feishu_blocks(alerts, sentiment_summary, activity_data)
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "银行信用卡竞品监控预警"},
                "template": "red" if (has_alerts or has_risk) else "blue",
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


def _has_risk_alerts(activity_data: dict | None) -> bool:
    if not activity_data:
        return False
    return len(activity_data.get("risk_alerts", [])) > 0


def _build_feishu_blocks(
    alerts: list[dict],
    sentiment: list[dict],
    activity_data: dict | None,
) -> list[dict]:
    blocks = []

    now = datetime.now().strftime("%m-%d %H:%M")
    blocks.append({"tag": "div", "text": {"tag": "lark_md", "content": f"监控时间：{now}"}})
    blocks.append({"tag": "hr"})

    # Rating alerts
    if alerts:
        alert_lines = "\n".join(
            f"- **{a['name']}**（{a.get('bank','')}）：{'↑' if a['direction'] == 'up' else '↓'}{abs(a['change']):.2f}（{a['previous_rating']}★→{a['current_rating']}★）"
            for a in alerts[:5]
        )
        blocks.append({"tag": "div", "text": {"tag": "lark_md", "content": f"**📊 评分异动**\n{alert_lines}"}})
        blocks.append({"tag": "hr"})

    # Sentiment alerts
    for s in sentiment:
        if s.get("negative_pct", 0) > 25:
            blocks.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**😟 口碑预警**\n{s['name']}（{s.get('bank','')}）差评率 {s['negative_pct']}%\n负面关键词：{'、'.join(s.get('top_negative_words', [])[:5])}",
                },
            })
            blocks.append({"tag": "hr"})

        # Risk dimensions from sentiment
        for rd in s.get("risk_dimensions", []):
            if rd.get("alert"):
                blocks.append({
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**⚠️ 信用卡风险**\n{s['name']}（{s.get('bank','')}）— {rd['dimension']}\n提及 {rd['mention_count']} 次，平均情感 {rd['avg_sentiment']:.2f}",
                    },
                })
                blocks.append({"tag": "hr"})

    # Activity risk alerts
    if activity_data:
        risk_alerts = activity_data.get("risk_alerts", [])
        if risk_alerts:
            risk_lines = "\n".join(
                f"- **{r.get('app_name','')}**（{r.get('bank','')}）：{r['category']} 提及 {r['mention_count']} 次 [{r['alert_level']}]"
                for r in risk_alerts[:5]
            )
            blocks.append({"tag": "div", "text": {"tag": "lark_md", "content": f"**🚨 信用卡风险预警**\n{risk_lines}"}})
            blocks.append({"tag": "hr"})

    blocks.append({"tag": "note", "elements": [{"tag": "plain_text", "content": "银行信用卡竞品监控系统 · 自动生成"}]})

    return blocks
