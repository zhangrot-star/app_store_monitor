"""Configuration loader — Pydantic settings from config.yaml."""

from __future__ import annotations

import yaml
from pydantic import BaseModel


class CrawlerConfig(BaseModel):
    request_delay_sec: float = 3.0
    max_retries: int = 3
    timeout_sec: int = 15
    user_agent: str = ""
    use_proxy: bool = False
    proxy: str = ""


class TargetConfig(BaseModel):
    app_id: str
    name: str
    category: str


class AnalysisConfig(BaseModel):
    rating_alert_threshold: float = 0.3
    review_fetch_count: int = 50
    sentiment_model: str = "snownlp"
    review_alert_pct: float = 25.0


class ReportConfig(BaseModel):
    output_dir: str = "./reports"
    template: str = "dashboard.html"


class NotifyConfig(BaseModel):
    enabled: bool = False
    webhook_url: str = ""
    channels: list[str] = ["feishu"]


class AppConfig(BaseModel):
    data_source: str = "app_store"
    country: str = "cn"
    language: str = "zh-Hans"
    crawler: CrawlerConfig = CrawlerConfig()
    targets: list[TargetConfig] = []
    analysis: AnalysisConfig = AnalysisConfig()
    report: ReportConfig = ReportConfig()
    notify: NotifyConfig = NotifyConfig()

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> "AppConfig":
        with open(path) as f:
            raw = yaml.safe_load(f)
        return cls(**raw)


_config: AppConfig | None = None


def get_config(path: str = "config.yaml") -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig.from_yaml(path)
    return _config
