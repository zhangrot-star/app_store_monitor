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
    bank: str = ""  # 所属银行


class AnalysisConfig(BaseModel):
    rating_alert_threshold: float = 0.3
    review_fetch_count: int = 50
    sentiment_model: str = "snownlp"
    review_alert_pct: float = 25.0


class ReportConfig(BaseModel):
    output_dir: str = "./reports"
    template: str = "cc_monitor.html"


class NotifyConfig(BaseModel):
    enabled: bool = False
    webhook_url: str = ""
    channels: list[str] = ["feishu"]


# ── 信用卡活动监控配置 ──


class CreditCardConfig(BaseModel):
    """信用卡活动关键词 / 风险关键词配置。"""

    activity_keywords: dict[str, list[str]] = {
        "新户礼": ["新户礼", "开卡礼", "首刷礼", "新客礼", "开卡送", "首刷送", "新人礼"],
        "分期优惠": ["分期", "免息", "手续费", "分期优惠", "分期0息", "账单分期"],
        "积分活动": ["积分", "积分翻倍", "多倍积分", "积分兑换", "积分加赠"],
        "权益升级": ["权益", "贵宾厅", "接送机", "龙腾", "cip", "延误险", "里程"],
        "支付优惠": ["满减", "立减", "返现", "刷卡金", "优惠券", "折扣"],
        "联名卡": ["联名卡", "联名", "主题卡", "限量卡"],
    }
    risk_keywords: dict[str, list[str]] = {
        "发卡问题": ["审批慢", "额度低", "拒批", "审核严", "门槛高", "不下卡"],
        "权益缩水": ["权益缩水", "权益取消", "权益降级", "温暖升级", "权益变差"],
        "客服体验": ["客服难接通", "客服差", "处理慢", "踢皮球", "投诉无门"],
        "积分贬值": ["积分过期", "积分贬值", "积分难换", "积分清零", "积分不值钱"],
        "活动套路": ["虚假宣传", "门槛高", "到账慢", "活动套路", "抢不到", "名额少"],
    }
    risk_alert_threshold: int = 3


class AppConfig(BaseModel):
    data_source: str = "app_store"
    country: str = "cn"
    language: str = "zh-Hans"
    crawler: CrawlerConfig = CrawlerConfig()
    targets: list[TargetConfig] = []
    analysis: AnalysisConfig = AnalysisConfig()
    report: ReportConfig = ReportConfig()
    notify: NotifyConfig = NotifyConfig()
    credit_card: CreditCardConfig = CreditCardConfig()

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> AppConfig:
        with open(path) as f:
            raw = yaml.safe_load(f)
        return cls(**raw)


_config: AppConfig | None = None


def get_config(path: str = "config.yaml") -> AppConfig:
    global _config
    if _config is None:
        _config = AppConfig.from_yaml(path)
    return _config
