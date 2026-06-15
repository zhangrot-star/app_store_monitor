"""信用卡活动监控 — 从用户评论中识别营销活动、用户权益、风险关键词。

功能：
  1. 活动关键词匹配：扫描评论中是否提及新户礼、分期优惠、积分活动等
  2. 风险关键词匹配：扫描评论中是否涉及发卡问题、权益缩水、客服体验等
  3. 自动生成活动简报和风险预警
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from config.settings import AppConfig
from snownlp import SnowNLP

logger = logging.getLogger(__name__)


def analyze_credit_card_activities(
    storage: Any,
    config: AppConfig,
) -> dict:
    """主入口：扫描所有银行 App 的评论，识别信用卡活动和风险关键词。

    Returns:
        {
            "activity_summary": [{"app_name", "bank", "category", "count"}, ...],
            "risk_alerts":       [{"app_name", "bank", "category", "count", "alert_level"}, ...],
            "by_app":            {app_id: {"activities": [...], "risks": [...]}},
        }
    """
    cc_cfg = config.credit_card
    apps = storage.get_all_apps()
    by_app: dict[str, dict] = {}
    all_alerts: list[dict] = []

    for app in apps:
        aid = app["app_id"]
        reviews = storage.get_reviews(aid, limit=100)
        if not reviews:
            continue

        app_activities = _scan_activities(aid, reviews, cc_cfg.activity_keywords, storage)
        app_risks = _scan_risks(aid, reviews, cc_cfg.risk_keywords, storage, cc_cfg.risk_alert_threshold)
        all_alerts.extend(app_risks)

        by_app[aid] = {
            "name": app["name"],
            "bank": app.get("bank", ""),
            "activities": app_activities,
            "risks": app_risks,
        }

    # 汇总 activity 统计
    activity_summary = storage.get_activity_summary(days=30)

    # 汇总风险预警
    unread = storage.get_unread_risk_alerts(days=7)
    risk_alerts = unread or all_alerts

    return {
        "activity_summary": activity_summary,
        "risk_alerts": risk_alerts,
        "by_app": by_app,
    }


def analyze_activities_by_app(storage: Any, app_id: str, config: AppConfig, days: int = 30) -> dict:
    """单独分析某个银行 App 的活动/风险情况。"""
    app = storage.get_app_by_id(app_id)
    if not app:
        return {"error": "App not found", "app_id": app_id}

    reviews = storage.get_reviews_since(app_id, since_date="", limit=200)
    if not reviews:
        reviews = storage.get_reviews(app_id, limit=200)

    cc_cfg = config.credit_card
    activities = _scan_activities(app_id, reviews, cc_cfg.activity_keywords, storage)
    risks = _scan_risks(app_id, reviews, cc_cfg.risk_keywords, storage, cc_cfg.risk_alert_threshold)

    return {
        "app_id": app_id,
        "name": app["name"],
        "bank": app.get("bank", ""),
        "activities": activities,
        "risks": risks,
        "review_count": len(reviews),
    }


def _scan_activities(
    app_id: str,
    reviews: list[dict],
    activity_keywords: dict[str, list[str]],
    storage: Any,
) -> list[dict]:
    """扫描评论中匹配活动关键词，存入 activity_mentions 表。

    Returns:
        [{"category": "新户礼", "keyword": "...", "sentiment": "positive", "count": 3}, ...]
    """
    category_counter: dict[str, int] = defaultdict(int)
    category_keywords: dict[str, set[str]] = defaultdict(set)

    for r in reviews:
        text = f"{r.get('title', '')} {r.get('content', '')}"
        if not text.strip():
            continue

        # 情感分类 (给匹配到的条目一个大致情感倾向)
        try:
            s = SnowNLP(text)
            sentiment = "positive" if s.sentiments > 0.6 else "negative" if s.sentiments < 0.4 else "neutral"
        except Exception:
            sentiment = "neutral"

        for cat_name, keywords in activity_keywords.items():
            for kw in keywords:
                if kw in text:
                    category_counter[cat_name] += 1
                    category_keywords[cat_name].add(kw)
                    storage.insert_activity_mention(
                        app_id, r["review_id"], cat_name, kw,
                        sentiment=sentiment, review_date=r.get("review_date", ""),
                    )
                    break  # 同一评论同一类别只记一次

    return [
        {
            "category": cat,
            "keywords": sorted(list(kws)),
            "count": cnt,
        }
        for cat, cnt in sorted(category_counter.items(), key=lambda x: -x[1])
        for kws in [category_keywords[cat]]
    ]


def _scan_risks(
    app_id: str,
    reviews: list[dict],
    risk_keywords: dict[str, list[str]],
    storage: Any,
    threshold: int = 3,
) -> list[dict]:
    """扫描评论中匹配风险关键词，达到阈值则生成预警。

    Returns:
        [{"category": "发卡问题", "count": 5, "alert_level": "warning"}, ...]
    """
    category_counter: dict[str, int] = defaultdict(int)

    for r in reviews:
        text = f"{r.get('title', '')} {r.get('content', '')}"
        if not text.strip():
            continue

        for cat_name, keywords in risk_keywords.items():
            for kw in keywords:
                if kw in text:
                    category_counter[cat_name] += 1
                    break

    alerts = []
    for cat, cnt in sorted(category_counter.items(), key=lambda x: -x[1]):
        if cnt >= threshold:
            level = "critical" if cnt >= threshold * 3 else "warning"
            alerts.append({
                "category": cat,
                "count": cnt,
                "alert_level": level,
            })
            storage.insert_risk_alert(app_id, cat, cnt, alert_level=level)

    return alerts


def _compute_activity_report_data(activity_summary: list[dict]) -> dict:
    """把 activity_summary 整理成更容易在模板中使用的格式。"""
    categories_seen: set[str] = set()
    by_bank: dict[str, dict[str, int]] = {}

    for item in activity_summary:
        cat = item["category"]
        bank = item.get("bank", "")
        categories_seen.add(cat)
        if bank not in by_bank:
            by_bank[bank] = {}
        by_bank[bank][cat] = by_bank[bank].get(cat, 0) + item["count"]

    sorted_cats = sorted(categories_seen)
    bank_names = list(by_bank.keys())

    return {
        "categories": sorted_cats,
        "banks": bank_names,
        "bank_data": by_bank,
    }
