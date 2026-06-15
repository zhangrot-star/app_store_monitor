"""Review sentiment analysis — jieba tokenization + SnowNLP scoring.

Credit card edition: includes per-dimension risk sentiment analysis
(发卡问题, 权益缩水, 客服体验, 积分贬值, 活动套路).
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from typing import Any

from config.settings import AppConfig

logger = logging.getLogger(__name__)


def analyze_sentiment(storage: Any, config: AppConfig | None = None) -> list[dict]:
    """Score reviews per product and extract top keywords.

    If config is provided, also runs credit card risk dimension analysis.
    """
    from snownlp import SnowNLP

    apps = storage.get_all_apps()
    results = []

    # Risk keywords for credit card dimension breakdown
    risk_keywords = {}
    if config:
        risk_keywords = config.credit_card.risk_keywords

    for p in apps:
        reviews = storage.get_reviews(p["app_id"], limit=100)
        if not reviews:
            continue

        scores = []
        all_words: list[str] = []
        positive_words: list[str] = []
        negative_words: list[str] = []

        # Per-dimension risk tracking
        risk_dimension_hits: dict[str, int] = defaultdict(int)
        risk_dimension_sentiment: dict[str, list[float]] = defaultdict(list)

        for r in reviews:
            text = r.get("content", "")
            if not text:
                continue
            try:
                s = SnowNLP(text)
                score = s.sentiments
            except Exception:
                score = 0.5

            scores.append(score)
            sent_label = "positive" if score > 0.6 else "negative" if score < 0.4 else "neutral"
            r["sentiment"] = sent_label

            # Update review sentiment in DB
            storage.conn.execute(
                "UPDATE reviews SET sentiment=? WHERE review_id=?",
                (sent_label, r["review_id"]),
            )

            words = _tokenize(text)
            all_words.extend(words)
            if score > 0.6:
                positive_words.extend(words)
            elif score < 0.4:
                negative_words.extend(words)

            # Credit card risk dimension hits
            for dim_name, keywords in risk_keywords.items():
                for kw in keywords:
                    if kw in text:
                        risk_dimension_hits[dim_name] += 1
                        risk_dimension_sentiment[dim_name].append(score)
                        break

        storage.conn.commit()

        avg_score = sum(scores) / len(scores) if scores else 0
        pos_count = sum(1 for s in scores if s > 0.6)
        neg_count = sum(1 for s in scores if s < 0.4)
        neu_count = len(scores) - pos_count - neg_count

        # Build risk dimension insights
        risk_dimensions = [
            {
                "dimension": dim,
                "mention_count": count,
                "avg_sentiment": round(sum(risk_dimension_sentiment[dim]) / len(risk_dimension_sentiment[dim]), 3)
                    if risk_dimension_sentiment[dim] else 0,
                "alert": count >= (config.credit_card.risk_alert_threshold if config else 3),
            }
            for dim, count in sorted(risk_dimension_hits.items(), key=lambda x: -x[1])
        ]

        result = {
            "app_id": p["app_id"],
            "name": p["name"],
            "bank": p.get("bank", ""),
            "review_count": len(scores),
            "avg_sentiment": round(avg_score, 3),
            "positive_pct": round(pos_count / len(scores) * 100, 1) if scores else 0,
            "negative_pct": round(neg_count / len(scores) * 100, 1) if scores else 0,
            "neutral_pct": round(neu_count / len(scores) * 100, 1) if scores else 0,
            "top_positive_words": _top_words(positive_words, 5),
            "top_negative_words": _top_words(negative_words, 5),
            "risk_dimensions": risk_dimensions,
        }
        results.append(result)

    return results


def analyze_risk_sentiment_for_app(
    storage: Any,
    app_id: str,
    risk_keywords: dict[str, list[str]],
    threshold: int = 3,
) -> dict:
    """Deep sentiment analysis per risk dimension for a single bank app."""
    from snownlp import SnowNLP

    app = storage.get_app_by_id(app_id)
    if not app:
        return {"error": "App not found"}

    reviews = storage.get_reviews(app_id, limit=200)
    dimensions: dict[str, dict] = {}

    for r in reviews:
        text = r.get("content", "")
        if not text:
            continue

        try:
            s = SnowNLP(text)
            score = s.sentiments
        except Exception:
            score = 0.5

        for dim_name, keywords in risk_keywords.items():
            for kw in keywords:
                if kw in text:
                    if dim_name not in dimensions:
                        dimensions[dim_name] = {
                            "dimension": dim_name,
                            "mentions": [],
                            "keywords_hit": set(),
                            "scores": [],
                        }
                    dimensions[dim_name]["mentions"].append(r["review_id"])
                    dimensions[dim_name]["keywords_hit"].add(kw)
                    dimensions[dim_name]["scores"].append(score)
                    break

    return {
        "app_id": app_id,
        "name": app.get("name", ""),
        "bank": app.get("bank", ""),
        "dimensions": [
            {
                "dimension": d["dimension"],
                "mention_count": len(d["mentions"]),
                "keywords": sorted(list(d["keywords_hit"])),
                "avg_sentiment": round(sum(d["scores"]) / len(d["scores"]), 3) if d["scores"] else 0,
                "alert": len(d["mentions"]) >= threshold,
            }
            for d in sorted(dimensions.values(), key=lambda x: -len(x["mentions"]))
        ],
    }


def _tokenize(text: str) -> list[str]:
    """Tokenize with jieba, filter stop words."""
    import jieba

    stop_words = {
        "的", "了", "是", "我", "很", "也", "都", "就", "还", "这",
        "那", "有", "不", "在", "和", "一个", "一", "个", "好", "买",
        "用", "说", "上", "下", "来", "去", "会", "可以", "没有",
        "这个", "那个", "觉得", "而且", "但是", "不过", "所以",
        "因为", "如果", "或者", "然后", "就是", "吧", "吗", "呢",
        "哦", "嗯", "啊", "呀", "哈", "嘛", "啦",
    }
    words = jieba.cut(text)
    return [w for w in words if len(w) > 1 and w not in stop_words]


def _top_words(words: list[str], n: int = 5) -> list[str]:
    return [w for w, _ in Counter(words).most_common(n)]
