"""Review sentiment analysis — jieba tokenization + SnowNLP scoring."""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)


def analyze_sentiment(storage: Any) -> list[dict]:
    """Score reviews per product and extract top keywords."""
    from snownlp import SnowNLP

    apps = storage.get_all_apps()
    results = []

    for p in apps:
        reviews = storage.get_reviews(p["app_id"], limit=100)
        if not reviews:
            continue

        scores = []
        all_words: list[str] = []
        positive_words: list[str] = []
        negative_words: list[str] = []

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
            r["sentiment"] = "positive" if score > 0.6 else "negative" if score < 0.4 else "neutral"

            # Collect words for keyword extraction
            words = _tokenize(text)
            all_words.extend(words)
            if score > 0.6:
                positive_words.extend(words)
            elif score < 0.4:
                negative_words.extend(words)

        avg_score = sum(scores) / len(scores) if scores else 0
        pos_count = sum(1 for s in scores if s > 0.6)
        neg_count = sum(1 for s in scores if s < 0.4)
        neu_count = len(scores) - pos_count - neg_count

        # Update sentiment in DB
        for r in reviews:
            if r.get("sentiment"):
                storage.conn.execute(
                    "UPDATE reviews SET sentiment=? WHERE review_id=?",
                    (r["sentiment"], r["review_id"]),
                )
        storage.conn.commit()

        results.append({
            "app_id": p["app_id"],
            "name": p["name"],
            "review_count": len(scores),
            "avg_sentiment": round(avg_score, 3),
            "positive_pct": round(pos_count / len(scores) * 100, 1) if scores else 0,
            "negative_pct": round(neg_count / len(scores) * 100, 1) if scores else 0,
            "neutral_pct": round(neu_count / len(scores) * 100, 1) if scores else 0,
            "top_positive_words": _top_words(positive_words, 5),
            "top_negative_words": _top_words(negative_words, 5),
        })

    return results


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
