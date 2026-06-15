"""银行信用卡业务竞品监控系统 — CLI 入口。

Usage:
    python main.py crawl      # 从 App Store 采集银行 App 数据
    python main.py analyze    # 评分 / 情感 / 竞品矩阵分析
    python main.py report     # 生成 HTML 看板报告（含信用卡活动分析）
    python main.py activity   # 信用卡活动关键词 + 风险口碑分析
    python main.py notify     # 飞书/钉钉 Webhook 预警推送
    python main.py run        # 全流程：crawl → analyze → activity → report → notify
"""

from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cc_monitor")


def cmd_crawl(config, storage) -> None:
    from crawlers.store import AppStoreCrawler

    crawler = AppStoreCrawler(
        country=config.country,
        delay=config.crawler.request_delay_sec,
        max_retries=config.crawler.max_retries,
        timeout=config.crawler.timeout_sec,
        user_agent=config.crawler.user_agent,
        use_proxy=config.crawler.use_proxy,
        proxy=config.crawler.proxy,
    )

    for t in config.targets:
        logger.info("采集: %s (%s) — %s", t.name, t.app_id, t.bank)

        info = crawler.get_app_info(t.app_id)
        if info:
            info["bank"] = t.bank  # 注入银行信息
            storage.upsert_app(info)

            if info.get("avg_rating", 0) > 0:
                changed = storage.insert_rating(
                    t.app_id, info["avg_rating"], info["rating_count"],
                    info.get("current_version", ""),
                )
                logger.info(
                    "  评分: %.2f★ (%s 条评分) %s",
                    info["avg_rating"], f"{info['rating_count']:,}",
                    "(更新)" if changed else "",
                )

        reviews = crawler.get_reviews(t.app_id, max_count=config.analysis.review_fetch_count)
        if reviews:
            n = storage.insert_reviews(reviews)
            logger.info("  评论: 新增 %d 条 (共采集 %d)", n, len(reviews))
        else:
            logger.info("  评论: 无新数据")

    storage.close()
    logger.info("采集完成。")


def cmd_analyze(config, storage) -> None:
    from analysis.competitor import build_comparison_matrix
    from analysis.price import analyze_rating_changes, compute_rating_summary
    from analysis.sentiment import analyze_sentiment

    logger.info("评分分析...")
    alerts = analyze_rating_changes(storage, config)
    summary = compute_rating_summary(storage)
    logger.info("  评分汇总: %s", summary)
    if alerts:
        for a in alerts:
            logger.info("  ⚠ %s: %s%+.3f★", a["name"], "↑" if a["direction"] == "up" else "↓", a["change"])

    logger.info("情感分析...")
    sentiment = analyze_sentiment(storage, config)  # 传入 config 以启用信用卡维度分析
    for s in sentiment:
        logger.info(
            "  %s: 平均情感=%.3f, 好评=%.1f%%, 差评=%.1f%%",
            s["name"], s["avg_sentiment"], s["positive_pct"], s["negative_pct"],
        )
        for rd in s.get("risk_dimensions", []):
            logger.info("    [信用卡风险] %s: 提及%d次, 平均情感%.3f", rd["dimension"], rd["mention_count"], rd["avg_sentiment"])

    logger.info("竞品矩阵...")
    comparison = build_comparison_matrix(storage)
    logger.info("  App 数: %d", len(comparison.get("matrix", [])))

    storage.close()
    logger.info("分析完成。")


def cmd_activity(config, storage) -> None:
    """信用卡活动 & 风险口碑识别。"""
    from analysis.activities import analyze_credit_card_activities

    logger.info("信用卡活动监控分析...")
    result = analyze_credit_card_activities(storage, config)

    summary = result.get("activity_summary", [])
    risks = result.get("risk_alerts", [])

    logger.info("活动关键词匹配:")
    for item in summary:
        logger.info("  %s(%s) - %s: 提及%d次", item["app_name"], item.get("bank", ""), item["category"], item["count"])

    if risks:
        logger.info("风险预警:")
        for r in risks:
            logger.info("  ⚠ %s(%s) - %s: 提及%d次 [%s]", r.get("app_name", ""), r.get("bank", ""), r["category"], r["mention_count"], r["alert_level"])

    storage.close()
    logger.info("活动分析完成。")


def cmd_report(config, storage) -> None:
    from analysis.activities import analyze_credit_card_activities
    from analysis.competitor import build_comparison_matrix
    from analysis.price import analyze_rating_changes
    from analysis.sentiment import analyze_sentiment
    from outputs.report import generate_report

    logger.info("生成报告...")
    alerts = analyze_rating_changes(storage, config)
    sentiment = analyze_sentiment(storage, config)
    comparison = build_comparison_matrix(storage)
    activities = analyze_credit_card_activities(storage, config)

    path = generate_report(
        comparison=comparison,
        alerts=alerts,
        sentiment_data=sentiment,
        activity_data=activities,
        output_dir=config.report.output_dir,
    )
    logger.info("报告: %s", path)
    storage.close()


def cmd_notify(config, storage) -> None:
    from analysis.price import analyze_rating_changes
    from analysis.sentiment import analyze_sentiment
    from outputs.notify import send_alert

    alerts = analyze_rating_changes(storage, config)
    sentiment = analyze_sentiment(storage, config)
    send_alert(alerts, sentiment, config)
    storage.close()


def cmd_run(config, storage) -> None:
    cmd_crawl(config, storage)
    logger.info("=" * 50)

    s2 = _init_storage()
    cmd_analyze(config, s2)
    logger.info("=" * 50)

    s3 = _init_storage()
    cmd_activity(config, s3)
    logger.info("=" * 50)

    s4 = _init_storage()
    cmd_report(config, s4)


def _init_storage():
    from storage.db import Storage
    return Storage()


def main() -> None:
    from config.settings import AppConfig
    from storage.db import Storage

    parser = argparse.ArgumentParser(description="银行信用卡业务竞品监控系统")
    parser.add_argument(
        "command",
        choices=["crawl", "analyze", "report", "activity", "notify", "run"],
        help="执行操作",
    )
    parser.add_argument(
        "-c", "--config", default="config.yaml", help="配置文件路径",
    )
    args = parser.parse_args()

    config = AppConfig.from_yaml(args.config)
    storage = Storage()

    cmds = {
        "crawl": cmd_crawl,
        "analyze": cmd_analyze,
        "report": cmd_report,
        "activity": cmd_activity,
        "notify": cmd_notify,
        "run": cmd_run,
    }
    cmds[args.command](config, storage)


if __name__ == "__main__":
    main()
