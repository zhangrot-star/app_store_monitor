"""App Store Competitive Intelligence Monitor — CLI entry point.

Usage:
    python main.py crawl      # Fetch app data, ratings, and reviews from App Store
    python main.py analyze    # Run rating/sentiment/competitor analysis
    python main.py report     # Generate HTML dashboard report
    python main.py notify     # Send alerts via webhook
    python main.py run        # Full pipeline: crawl → analyze → report → notify
"""

from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app_monitor")


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
        logger.info("Fetching: %s (%s)", t.name, t.app_id)

        # App metadata + ratings
        info = crawler.get_app_info(t.app_id)
        if info:
            # Override name/category from config if API data is incomplete
            if not info.get("name"):
                info["name"] = t.name
            if not info.get("category"):
                info["category"] = t.category
            storage.upsert_app(info)

            # Record rating snapshot
            if info.get("avg_rating", 0) > 0:
                changed = storage.insert_rating(
                    t.app_id, info["avg_rating"], info["rating_count"],
                    info.get("current_version", ""),
                )
                logger.info(
                    "  Rating: %.2f★ (%s ratings) %s",
                    info["avg_rating"], f"{info['rating_count']:,}",
                    "(changed)" if changed else "",
                )
            else:
                logger.info("  No rating data available")

        # Reviews
        reviews = crawler.get_reviews(t.app_id, max_count=config.analysis.review_fetch_count)
        if reviews:
            n = storage.insert_reviews(reviews)
            logger.info("  Reviews: %d new (fetched %d)", n, len(reviews))
        else:
            logger.info("  Reviews: none fetched")

    storage.close()
    logger.info("Crawl complete.")


def cmd_analyze(config, storage) -> None:
    from analysis.competitor import build_comparison_matrix
    from analysis.price import analyze_rating_changes, compute_rating_summary
    from analysis.sentiment import analyze_sentiment

    logger.info("Running rating analysis...")
    alerts = analyze_rating_changes(storage, config)
    summary = compute_rating_summary(storage)
    logger.info("  Rating summary: %s", summary)
    if alerts:
        for a in alerts:
            logger.info("  Alert: %s %+.3f★", a["name"], a["change"])

    logger.info("Running sentiment analysis...")
    sentiment = analyze_sentiment(storage)
    for s in sentiment:
        logger.info(
            "  %s: avg_sentiment=%.3f, pos=%.1f%%, neg=%.1f%%",
            s["name"], s["avg_sentiment"], s["positive_pct"], s["negative_pct"],
        )

    logger.info("Building comparison matrix...")
    comparison = build_comparison_matrix(storage)
    logger.info("  Apps: %d", len(comparison.get("matrix", [])))
    logger.info("  Rankings: %s", comparison.get("rankings", {}))

    storage.close()
    logger.info("Analysis complete.")


def cmd_report(config, storage) -> None:
    from analysis.competitor import build_comparison_matrix
    from analysis.price import analyze_rating_changes
    from analysis.sentiment import analyze_sentiment
    from outputs.report import generate_report

    logger.info("Generating report...")
    alerts = analyze_rating_changes(storage, config)
    sentiment = analyze_sentiment(storage)
    comparison = build_comparison_matrix(storage)

    path = generate_report(
        comparison=comparison,
        alerts=alerts,
        sentiment_data=sentiment,
        output_dir=config.report.output_dir,
    )
    logger.info("Report: %s", path)
    storage.close()


def cmd_notify(config, storage) -> None:
    from analysis.price import analyze_rating_changes
    from analysis.sentiment import analyze_sentiment
    from outputs.notify import send_alert

    alerts = analyze_rating_changes(storage, config)
    sentiment = analyze_sentiment(storage)
    send_alert(alerts, sentiment, config)
    storage.close()


def cmd_run(config, storage) -> None:
    cmd_crawl(config, storage)
    storage2 = _init_storage()
    cmd_analyze(config, storage2)
    storage3 = _init_storage()
    cmd_report(config, storage3)


def _init_storage():
    from storage.db import Storage

    return Storage()


def main() -> None:
    from config.settings import AppConfig
    from storage.db import Storage

    parser = argparse.ArgumentParser(description="App Store Competitive Intelligence Monitor")
    parser.add_argument(
        "command",
        choices=["crawl", "analyze", "report", "notify", "run"],
        help="Action to execute",
    )
    parser.add_argument(
        "-c", "--config", default="config.yaml", help="Config file path",
    )
    args = parser.parse_args()

    config = AppConfig.from_yaml(args.config)
    storage = Storage()

    cmds = {
        "crawl": cmd_crawl,
        "analyze": cmd_analyze,
        "report": cmd_report,
        "notify": cmd_notify,
        "run": cmd_run,
    }
    cmds[args.command](config, storage)


if __name__ == "__main__":
    main()
