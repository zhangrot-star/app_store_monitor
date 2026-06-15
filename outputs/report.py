"""HTML report generation — 银行信用卡业务竞品监控看板."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Template

logger = logging.getLogger(__name__)

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>银行信用卡竞品监控报告 — {{ report_time }}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f6fa; color: #333; }
.header { background: linear-gradient(135deg, #1a237e, #283593); color: #fff; padding: 30px 40px; }
.header h1 { font-size: 24px; margin-bottom: 6px; }
.header .subtitle { font-size: 14px; opacity: 0.85; }
.header .meta { font-size: 12px; opacity: 0.7; margin-top: 8px; }
.container { max-width: 1280px; margin: 0 auto; padding: 24px; }
.section { background: #fff; border-radius: 10px; padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.section h2 { font-size: 18px; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 2px solid #283593; display: flex; align-items: center; gap: 8px; }
.section h2 .badge { font-size: 11px; background: #283593; color: #fff; padding: 2px 8px; border-radius: 10px; }
.section h2 .badge.warn { background: #ff9800; }
.section h2 .badge.danger { background: #e53935; }
.chart { width: 100%; height: 380px; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid #eee; font-size: 13px; }
th { background: #fafafa; font-weight: 600; color: #555; white-space: nowrap; }
tr:hover { background: #f9f9f9; }
.bank-tag { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 11px; background: #e8eaf6; color: #283593; }
.alert { background: #fff3e0; border-left: 4px solid #ff9800; padding: 10px 14px; margin: 8px 0; border-radius: 4px; font-size: 13px; }
.alert.critical { background: #ffebee; border-color: #e53935; }
.stars { color: #f5a623; font-weight: 700; }
.tag { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 11px; }
.tag.up { background: #ffebee; color: #c62828; }
.tag.down { background: #e8f5e9; color: #2e7d32; }
.tag.pos { background: #e8f5e9; color: #2e7d32; }
.tag.neg { background: #ffebee; color: #c62828; }
.tag.warn { background: #fff3e0; color: #e65100; }
.tag.critical { background: #ffebee; color: #b71c1c; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; }
.stat-card { background: #fff; border-radius: 8px; padding: 16px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.stat-card .num { font-size: 28px; font-weight: 700; color: #283593; }
.stat-card .label { font-size: 12px; color: #888; margin-top: 4px; }
@media (max-width: 768px) { .grid-2, .grid-3 { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="header">
  <h1>银行信用卡业务 · 竞品监控报告</h1>
  <div class="subtitle">数据源：Apple App Store | 生成时间：{{ report_time }} | 监控 {{ app_count }} 家银行信用卡 App</div>
  <div class="meta">基于公开评论数据的市场情报分析，仅供内部参考</div>
</div>

<div class="container">

  <!-- Stats Summary -->
  <div class="grid-3">
    <div class="stat-card">
      <div class="num">{{ app_count }}</div>
      <div class="label">监控银行 App</div>
    </div>
    <div class="stat-card">
      <div class="num">{{ total_reviews }}</div>
      <div class="label">评论采集量</div>
    </div>
    <div class="stat-card">
      <div class="num">{{ risk_count }}</div>
      <div class="label">风险预警</div>
    </div>
  </div>

  <!-- App Overview Table -->
  <div class="section">
    <h2>银行 App 概览</h2>
    <table>
      <tr>
        <th>银行</th><th>App 名称</th><th>开发者</th><th>版本</th><th>评分</th><th>评分人数</th><th>评论数</th><th>趋势</th>
      </tr>
      {% for r in matrix %}
      <tr>
        <td><span class="bank-tag">{{ r.get('bank', '-') }}</span></td>
        <td><strong>{{ r.name }}</strong></td>
        <td>{{ r.get('developer', '-') }}</td>
        <td>{{ r.get('current_ver', '-') }}</td>
        <td><span class="stars">{{ "%.2f"|format(r.rating|float) }} ★</span></td>
        <td>{{ "{:,}".format(r.rating_count|int) if r.rating_count else '-' }}</td>
        <td>{{ "{:,}".format(r.review_total|int) if r.review_total else '-' }}</td>
        <td>{% if r.rating_change and r.rating_change > 0 %}<span class="tag down">↑{{ "%.2f"|format(r.rating_change) }}</span>{% elif r.rating_change and r.rating_change < 0 %}<span class="tag up">↓{{ "%.2f"|format(r.rating_change|abs) }}</span>{% else %}-{% endif %}</td>
      </tr>
      {% endfor %}
    </table>
  </div>

  <!-- Rating Comparison Chart -->
  <div class="section">
    <h2>评分对比</h2>
    <div id="ratingChart" class="chart"></div>
  </div>

  <!-- Rating Alerts -->
  {% if alerts %}
  <div class="section">
    <h2>评分异动预警 <span class="badge warn">{{ alerts|length }}</span></h2>
    {% for a in alerts %}
    <div class="alert{% if a.direction == 'down' %} critical{% endif %}">
      <strong>{{ a.name }}</strong>（{{ a.get('bank', '') }}）：
      {{ "%.2f"|format(a.previous_rating) }} ★ → {{ "%.2f"|format(a.current_rating) }} ★
      （{% if a.direction == 'up' %}↑{% else %}↓{% endif %}{{ "%.2f"|format(a.change|abs) }}）
      {% if a.direction == 'down' %}⚠ 评分下滑，建议关注用户反馈{% else %}✅ 评分提升{% endif %}
    </div>
    {% endfor %}
  </div>
  {% endif %}

  <!-- Credit Card Activity Monitoring -->
  <div class="section">
    <h2>信用卡活动监测 <span class="badge">{{ activity_total }}</span></h2>
    <p style="color:#888;font-size:13px;margin-bottom:12px;">从用户评论中识别信用卡营销活动相关关键词提及</p>
    <div id="activityChart" class="chart" style="height:350px;"></div>
    {% if activity_table %}
    <table style="margin-top:12px;">
      <tr>
        <th>银行</th><th>App</th><th>活动类型</th><th>提及次数</th>
      </tr>
      {% for a in activity_table %}
      <tr>
        <td><span class="bank-tag">{{ a.bank }}</span></td>
        <td>{{ a.app_name }}</td>
        <td>{{ a.category }}</td>
        <td><strong>{{ a.count }}</strong></td>
      </tr>
      {% endfor %}
    </table>
    {% endif %}
  </div>

  <!-- Risk Sentiment Analysis -->
  <div class="section">
    <h2>信用卡风险口碑 <span class="badge danger">{{ risk_count }}</span></h2>
    <p style="color:#888;font-size:13px;margin-bottom:12px;">基于负面关键词分类的用户口碑分析</p>
    <div id="riskChart" class="chart" style="height:350px;"></div>
    {% if risk_alerts %}
    <div style="margin-top:12px;">
      {% for r in risk_alerts %}
      <div class="alert{% if r.alert_level == 'critical' %} critical{% endif %}">
        <strong>{{ r.get('app_name', '') }}</strong>（{{ r.get('bank', '') }}）
        — {{ r.category }}：提及 <strong>{{ r.mention_count }}</strong> 次
        <span class="tag {{ r.alert_level }}">{{ r.alert_level }}</span>
      </div>
      {% endfor %}
    </div>
    {% endif %}
  </div>

  <div class="grid-2">
    <!-- Sentiment Distribution -->
    <div class="section">
      <h2>用户评价情感分布</h2>
      <div id="sentimentChart" class="chart" style="height:320px;"></div>
    </div>
    <!-- Review Volume -->
    <div class="section">
      <h2>评论采集量</h2>
      <div id="reviewChart" class="chart" style="height:320px;"></div>
    </div>
  </div>

  <!-- Review Keywords Insights -->
  <div class="section">
    <h2>用户评价关键词</h2>
    <table>
      <tr><th>银行</th><th>App</th><th>好评关键词</th><th>差评关键词</th><th>好评率</th><th>差评率</th></tr>
      {% for s in sentiment %}
      <tr>
        <td><span class="bank-tag">{{ s.get('bank', '') }}</span></td>
        <td>{{ s.name }}</td>
        <td>{{ s.top_positive_words[:3]|join('、') if s.top_positive_words else '-' }}</td>
        <td>{{ s.top_negative_words[:3]|join('、') if s.top_negative_words else '-' }}</td>
        <td><span class="tag pos">{{ s.positive_pct }}%</span></td>
        <td><span class="tag neg">{{ s.negative_pct }}%</span></td>
      </tr>
      {% endfor %}
    </table>
  </div>

  <!-- Risk Dimension Breakdown -->
  {% if risk_dimension_table %}
  <div class="section">
    <h2>信用卡负面维度明细</h2>
    <table>
      <tr><th>银行</th><th>App</th><th>风险维度</th><th>提及</th><th>平均情感</th><th>状态</th></tr>
      {% for rd in risk_dimension_table %}
      <tr>
        <td><span class="bank-tag">{{ rd.bank }}</span></td>
        <td>{{ rd.app_name }}</td>
        <td>{{ rd.dimension }}</td>
        <td>{{ rd.count }}</td>
        <td>{{ "%.3f"|format(rd.avg_sentiment) }}</td>
        <td>{% if rd.alert %}<span class="tag warn">需关注</span>{% else %}<span class="tag pos">正常</span>{% endif %}</td>
      </tr>
      {% endfor %}
    </table>
  </div>
  {% endif %}

  <!-- Recommendations -->
  <div class="section">
    <h2>运营建议</h2>
    <table>
      <tr><th>维度</th><th>建议</th></tr>
      {% for rec in recommendations %}
      <tr><td>{{ rec.dimension }}</td><td>{{ rec.advice }}</td></tr>
      {% endfor %}
    </table>
  </div>

</div>

<script>
// Rating comparison bar chart
(function() {
  var dom = document.getElementById('ratingChart');
  var chart = echarts.init(dom);
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: {{ rating_names|safe }}, axisLabel: { rotate: 20, fontSize: 11 } },
    yAxis: { type: 'value', min: 3.5, max: 5, name: '评分 ★' },
    series: [{
      name: 'App Store 评分', type: 'bar',
      data: {{ rating_values|safe }},
      itemStyle: {
        borderRadius: [4,4,0,0],
        color: new echarts.graphic.LinearGradient(0,0,0,1,[
          {offset:0,color:'#283593'},{offset:1,color:'#5c6bc0'}
        ])
      },
      label: { show: true, position: 'top', formatter: '{c}' }
    }]
  });
})();

// Sentiment bars
(function() {
  var dom = document.getElementById('sentimentChart');
  var chart = echarts.init(dom);
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0 },
    xAxis: { type: 'category', data: {{ sentiment_names|safe }}, axisLabel: { rotate: 20, fontSize: 11 } },
    yAxis: { type: 'value', max: 100, name: '%' },
    series: [
      { name: '好评', type: 'bar', stack: 'pct', data: {{ sentiment_pos|safe }}, itemStyle: { color: '#34C759' } },
      { name: '中评', type: 'bar', stack: 'pct', data: {{ sentiment_neu|safe }}, itemStyle: { color: '#FF9500' } },
      { name: '差评', type: 'bar', stack: 'pct', data: {{ sentiment_neg|safe }}, itemStyle: { color: '#FF3B30' } }
    ]
  });
})();

// Review counts pie
(function() {
  var dom = document.getElementById('reviewChart');
  var chart = echarts.init(dom);
  chart.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      name: '评论数', type: 'pie', radius: ['40%','70%'],
      data: {{ review_pie|safe }},
      label: { formatter: '{b}\n{d}%' }
    }]
  });
})();

// Activity chart (horizontal bar)
{% if activity_chart_data %}
(function() {
  var dom = document.getElementById('activityChart');
  var chart = echarts.init(dom);
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'value', name: '提及次数' },
    yAxis: { type: 'category', data: {{ activity_categories|safe }} },
    series: {{ activity_series|safe }}
  });
})();
{% else %}
(function() {
  var dom = document.getElementById('activityChart');
  dom.innerHTML = '<p style="text-align:center;color:#999;padding:60px 0">暂无活动关键词数据，请先运行 python main.py activity</p>';
})();
{% endif %}

// Risk chart
{% if risk_chart_data %}
(function() {
  var dom = document.getElementById('riskChart');
  var chart = echarts.init(dom);
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: { type: 'value', name: '提及次数' },
    yAxis: { type: 'category', data: {{ risk_categories|safe }} },
    series: {{ risk_series|safe }}
  });
})();
{% else %}
(function() {
  var dom = document.getElementById('riskChart');
  dom.innerHTML = '<p style="text-align:center;color:#999;padding:60px 0">暂无风险关键词数据</p>';
})();
{% endif %}
</script>
</body>
</html>"""


def generate_report(
    comparison: dict,
    alerts: list[dict],
    sentiment_data: list[dict],
    activity_data: dict | None = None,
    output_dir: str = "./reports",
) -> str:
    """Render HTML report and save to file."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    filename = f"cc_monitor_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = Path(output_dir) / filename

    matrix = comparison.get("matrix", [])
    alert_map = {a["app_id"]: a["change"] for a in alerts}
    for r in matrix:
        r["rating_change"] = alert_map.get(r["app_id"], 0)

    # Chart data
    rating_names = json.dumps([f"{m['name']}({m.get('bank','')[:2]})" for m in matrix])
    rating_values = json.dumps([m["rating"] for m in matrix])
    sentiment_names = json.dumps([s["name"][:6] for s in sentiment_data])
    sentiment_pos = json.dumps([s["positive_pct"] for s in sentiment_data])
    sentiment_neu = json.dumps([s["neutral_pct"] for s in sentiment_data])
    sentiment_neg = json.dumps([s["negative_pct"] for s in sentiment_data])
    review_pie = json.dumps([
        {"value": m.get("review_total", 0), "name": m["name"][:8]}
        for m in matrix
    ])

    total_reviews = sum(m.get("review_total", 0) for m in matrix)

    # Activity data
    activity_summary = (activity_data or {}).get("activity_summary", [])
    activity_total = sum(a.get("count", 0) for a in activity_summary)
    activity_table = sorted(activity_summary, key=lambda x: -x.get("count", 0))[:20]

    activity_chart_data = _build_activity_chart_data(activity_summary)
    activity_categories = json.dumps(activity_chart_data.get("categories", []))
    activity_series = json.dumps(activity_chart_data.get("series", []))

    # Risk data
    risk_alerts = (activity_data or {}).get("risk_alerts", [])
    risk_count = len(risk_alerts)

    risk_chart_data = _build_risk_chart_data(risk_alerts)
    risk_categories = json.dumps(risk_chart_data.get("categories", []))
    risk_series = json.dumps(risk_chart_data.get("series", []))

    # Risk dimension breakdown per app (from sentiment data)
    risk_dimension_table = []
    for s in sentiment_data:
        for rd in s.get("risk_dimensions", []):
            risk_dimension_table.append({
                "app_name": s["name"],
                "bank": s.get("bank", ""),
                "dimension": rd["dimension"],
                "count": rd["mention_count"],
                "avg_sentiment": rd["avg_sentiment"],
                "alert": rd["alert"],
            })

    recommendations = _generate_recommendations(alerts, sentiment_data, activity_data, comparison)

    template = Template(TEMPLATE)
    html = template.render(
        report_time=now,
        app_count=len(matrix),
        total_reviews=total_reviews,
        risk_count=risk_count,
        matrix=matrix,
        alerts=alerts,
        sentiment=sentiment_data,
        rating_names=rating_names,
        rating_values=rating_values,
        sentiment_names=sentiment_names,
        sentiment_pos=sentiment_pos,
        sentiment_neu=sentiment_neu,
        sentiment_neg=sentiment_neg,
        review_pie=review_pie,
        recommendations=recommendations,
        # Activity section
        activity_data=activity_data or {},
        activity_total=activity_total,
        activity_table=activity_table,
        activity_chart_data=activity_chart_data,
        activity_categories=activity_categories,
        activity_series=activity_series,
        # Risk section
        risk_alerts=risk_alerts,
        risk_chart_data=risk_chart_data,
        risk_categories=risk_categories,
        risk_series=risk_series,
        risk_dimension_table=risk_dimension_table,
    )

    filepath.write_text(html, encoding="utf-8")
    logger.info("Report saved: %s", filepath)
    return str(filepath)


def _build_activity_chart_data(activity_summary: list[dict]) -> dict:
    """Build horizontal bar chart data for activity monitoring."""
    from collections import defaultdict

    by_category: dict[str, dict[str, int]] = defaultdict(dict)
    categories_seen: set[str] = set()
    banks_seen: set[str] = set()

    for item in activity_summary:
        cat = item["category"]
        bank = item.get("bank", "其他")
        by_category[bank][cat] = by_category[bank].get(cat, 0) + item["count"]
        categories_seen.add(cat)
        banks_seen.add(bank)

    sorted_cats = sorted(categories_seen)
    sorted_banks = sorted(banks_seen)
    colors = ["#283593", "#5c6bc0", "#9fa8da", # indigo
              "#1565c0", "#42a5f5", "#90caf9", # blue
              "#00838f", "#4db6ac", "#80cbc4"] # teal

    series = []
    for i, bank in enumerate(sorted_banks):
        series.append({
            "name": bank,
            "type": "bar",
            "stack": "total",
            "data": [by_category[bank].get(cat, 0) for cat in sorted_cats],
            "itemStyle": {"color": colors[i % len(colors)]},
        })

    return {"categories": sorted_cats, "series": series}


def _build_risk_chart_data(risk_alerts: list[dict]) -> dict:
    """Build horizontal bar chart data for risk monitoring."""
    from collections import defaultdict

    by_dim: dict[str, dict[str, int]] = defaultdict(dict)
    dims_seen: set[str] = set()
    banks_seen: set[str] = set()

    for r in risk_alerts:
        dim = r["category"]
        bank = r.get("bank", "其他")
        by_dim[bank][dim] = by_dim[bank].get(dim, 0) + r["mention_count"]
        dims_seen.add(dim)
        banks_seen.add(bank)

    sorted_dims = sorted(dims_seen)
    sorted_banks = sorted(banks_seen)
    colors = ["#e53935", "#ef5350", "#ef9a9a",  # red gradient
              "#fb8c00", "#ffa726", "#ffcc80"]  # orange

    series = []
    for i, bank in enumerate(sorted_banks):
        series.append({
            "name": bank,
            "type": "bar",
            "stack": "total",
            "data": [by_dim[bank].get(dim, 0) for dim in sorted_dims],
            "itemStyle": {"color": colors[i % len(colors)]},
        })

    return {"categories": sorted_dims, "series": series}


def _generate_recommendations(
    alerts: list[dict],
    sentiment: list[dict],
    activity_data: dict | None,
    comparison: dict,
) -> list[dict]:
    recs = []

    # Rating alerts
    for a in alerts[:3]:
        if a["direction"] == "down":
            recs.append({
                "dimension": "评分监控",
                "advice": f"{a['name']}({a.get('bank','')}) 评分下滑 {a['change']:.2f}，建议关注版本 {a.get('version','')} 的用户反馈。",
            })

    # Risk dimension insights
    for s in sentiment:
        for rd in s.get("risk_dimensions", []):
            if rd.get("alert"):
                recs.append({
                    "dimension": f"{s['name']} · {rd['dimension']}",
                    "advice": f"提及 {rd['mention_count']} 次，平均情感 {rd['avg_sentiment']:.2f}。建议对比自身产品排查同类问题。",
                })

    # Activity insights
    if activity_data:
        summary = activity_data.get("activity_summary", [])
        if summary:
            top = max(summary, key=lambda x: x.get("count", 0))
            recs.append({
                "dimension": "活动监测",
                "advice": f"监测期间 {top['app_name']}({top.get('bank','')}) 的「{top['category']}」提及最多({top['count']}次)，建议关注策略。",
            })

    # Competitive positioning
    rankings = comparison.get("rankings", {})
    top_rated = rankings.get("rating_high_to_low", [])
    if top_rated:
        recs.append({
            "dimension": "竞品定位",
            "advice": f"评分最高为 {top_rated[0][0] if isinstance(top_rated[0],tuple) else top_rated[0]}，建议分析其用户评价关键词提炼可复用策略。",
        })

    if not recs:
        recs.append({
            "dimension": "整体评估",
            "advice": "各银行 App 评分稳定，未发现异常。建议保持每周监控频率。",
        })

    return recs


def generate_weekly_report(
    comparison: dict,
    sentiment: list[dict],
    activities: dict,
    output_dir: str = "./reports",
) -> str:
    """生成周度竞品分析报告 — 适合周会和商务策略会使用.

    包含:
      - 本周评分变化趋势
      - 用户口碑一览（好评/差评关键词）
      - 信用卡活动热度排行
      - 风险预警汇总
      - 竞品对比雷达图
      - 商务策略建议
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    week_id = now.strftime("%Y-W%W")
    filename = f"weekly_report_{week_id}_{now.strftime('%Y%m%d')}.html"
    filepath = Path(output_dir) / filename

    matrix = comparison.get("matrix", [])
    sentiment_data = sentiment
    risk_alerts = activities.get("risk_alerts", [])
    activity_summary = activities.get("activity_summary", [])

    # 活动热度摘要
    top_activities = sorted(activity_summary, key=lambda x: -x.get("count", 0))[:10]

    # 风险汇总
    critical_risks = [r for r in risk_alerts if r.get("alert_level") == "critical"]
    warning_risks = [r for r in risk_alerts if r.get("alert_level") == "warning"]

    # 图表数据
    app_names = json.dumps([m["name"][:6] for m in matrix], ensure_ascii=False)
    app_ratings = json.dumps([m["rating"] for m in matrix])
    app_banks = [f"{m.get('bank','')[:3]}" for m in matrix]
    review_counts = json.dumps([m.get("review_total", 0) for m in matrix])

    pos_pcts = json.dumps([s["positive_pct"] for s in sentiment_data])
    neg_pcts = json.dumps([s["negative_pct"] for s in sentiment_data])

    radar_data = json.dumps([
        {"name": m["name"][:6], "bank": m.get("bank", ""),
         "rating": m["rating"],
         "review_total": m.get("review_total", 0),
         "positive_pct": next((s["positive_pct"] for s in sentiment_data if s["app_id"] == m["app_id"]), 50)}
        for m in matrix
    ], ensure_ascii=False)

    weekly_template = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>银行信用卡竞品周度监控报告 — {{ week }}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: "PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif; background: #f5f6fa; color: #333; }
.header { background: linear-gradient(135deg, #1a237e, #283593); color: #fff; padding: 24px 36px; }
.header h1 { font-size: 22px; }
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.section { background: #fff; border-radius: 8px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
.section h2 { font-size: 16px; color: #1a237e; margin-bottom: 14px; padding-bottom: 8px; border-bottom: 2px solid #c9a96e; }
.chart { width: 100%; height: 340px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee; }
th { background: #fafafa; font-weight: 600; color: #555; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 11px; }
.badge.critical { background: #ffebee; color: #c62828; }
.badge.warning { background: #fff3e0; color: #e65100; }
.summary-box { background: #f8f9fb; padding: 16px; border-radius: 8px; margin-bottom: 16px; line-height: 1.8; font-size: 14px; }
.action-item { padding: 4px 0; font-size: 13px; }
.action-item::before { content: '▸ '; color: #283593; font-weight: bold; }
</style>
</head>
<body>
<div class="header">
  <h1>🏦 银行信用卡竞品周度监控报告</h1>
  <p style="opacity:0.85;font-size:13px;">报告周期: {{ week }} | 监控App: {{ app_count }} 家 | 生成时间: {{ report_time }}</p>
</div>
<div class="container">

  <!-- 摘要 -->
  <div class="summary-box">
    <strong>📊 本周摘要：</strong>
    监控 {{ app_count }} 家银行信用卡 App · 平均评分 {{ "%.2f" % avg_rating }}★ ·
    风险预警 {{ critical_count }} 条严重 + {{ warning_count }} 条一般 ·
    {% if activity_total > 0 %}活动关键词命中 {{ activity_total }} 次{% else %}暂无活动数据{% endif %}
  </div>

  <!-- 竞品矩阵 -->
  <div class="section">
    <h2>竞品评分矩阵</h2>
    <table>
      <tr><th>银行</th><th>App</th><th>评分</th><th>评论数</th><th>好评率</th><th>差评率</th><th>状态</th></tr>
      {% for m in matrix %}
      <tr>
        <td>{{ m.get('bank','') }}</td>
        <td><strong>{{ m.name }}</strong></td>
        <td>{{ "%.2f" % m.rating }}★</td>
        <td>{{ m.get('review_total',0) }}</td>
        <td>{{ "%.1f" % m.get('positive_pct',0) }}%</td>
        <td>{{ "%.1f" % m.get('negative_pct',0) }}%</td>
        <td>{% if m.get('rating_change',0) < -0.1 %}<span class="badge critical">↓下滑</span>{% elif m.get('rating_change',0) > 0.1 %}<span class="badge" style="background:#e8f5e9;color:#2e7d32;">↑上升</span>{% else %}<span style="color:#888;">→稳定</span>{% endif %}</td>
      </tr>
      {% endfor %}
    </table>
  </div>

  <!-- 图表 -->
  <div class="grid-2">
    <div class="section"><h2>评分对比</h2><div id="ratingChart" class="chart"></div></div>
    <div class="section"><h2>好评/差评率</h2><div id="sentimentChart" class="chart"></div></div>
  </div>

  <!-- 活动热度 -->
  {% if top_activities %}
  <div class="section">
    <h2>信用卡活动热度 TOP 10</h2>
    <table>
      <tr><th>App</th><th>银行</th><th>活动类型</th><th>提及次数</th></tr>
      {% for a in top_activities %}
      <tr><td>{{ a.get('app_name','') }}</td><td>{{ a.get('bank','') }}</td><td>{{ a.category }}</td><td><strong>{{ a.count }}</strong></td></tr>
      {% endfor %}
    </table>
  </div>
  {% endif %}

  <!-- 风险预警 -->
  <div class="section">
    <h2>风险预警</h2>
    {% if critical_risks %}
    <p style="color:#c62828;font-weight:600;margin-bottom:8px;">🔴 严重预警</p>
    {% for r in critical_risks %}
    <div class="action-item" style="color:#c62828;">{{ r.get('app_name','') }}({{ r.get('bank','') }}) — {{ r.category }}: 提及 {{ r.mention_count }} 次</div>
    {% endfor %}
    {% endif %}
    {% if warning_risks %}
    <p style="color:#e65100;font-weight:600;margin:12px 0 8px;">🟠 一般预警</p>
    {% for r in warning_risks %}
    <div class="action-item" style="color:#e65100;">{{ r.get('app_name','') }}({{ r.get('bank','') }}) — {{ r.category }}: 提及 {{ r.mention_count }} 次</div>
    {% endfor %}
    {% endif %}
    {% if not critical_risks and not warning_risks %}
    <p style="color:#2e7d32;">✅ 本周未检测到信用卡风险预警</p>
    {% endif %}
  </div>

  <!-- 商务策略建议 -->
  <div class="section">
    <h2>💡 商务策略建议</h2>
    {% for rec in weekly_recommendations %}
    <div class="action-item"><strong>{{ rec.title }}</strong> — {{ rec.advice }}</div>
    {% endfor %}
  </div>

</div>
<script>
(function() {
  var c = echarts.init(document.getElementById('ratingChart'));
  c.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: {{ app_names|safe }}, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', min: 3.5, max: 5, name: '★' },
    series: [{ type: 'bar', data: {{ app_ratings|safe }}, itemStyle: { borderRadius: [4,4,0,0], color: new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'#283593'},{offset:1,color:'#7986cb'}]) }, label: { show: true, position: 'top' } }]
  });
})();
(function() {
  var c = echarts.init(document.getElementById('sentimentChart'));
  c.setOption({
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0 },
    xAxis: { type: 'category', data: {{ app_names|safe }}, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', max: 100, name: '%' },
    series: [
      { name: '好评率', type: 'bar', data: {{ pos_pcts|safe }}, itemStyle: { color: '#34C759' } },
      { name: '差评率', type: 'bar', data: {{ neg_pcts|safe }}, itemStyle: { color: '#FF3B30' } }
    ]
  });
})();
</script>
</body>
</html>"""

    # 计算摘要数据
    avg_rating = sum(m["rating"] for m in matrix) / len(matrix) if matrix else 0
    activity_total = sum(a.get("count", 0) for a in activity_summary)

    # 注入好评/差评率到矩阵
    sent_by_app = {s["app_id"]: s for s in sentiment_data}
    for m in matrix:
        s = sent_by_app.get(m["app_id"], {})
        m["positive_pct"] = s.get("positive_pct", 0)
        m["negative_pct"] = s.get("negative_pct", 0)

    # 生成周度商务建议
    weekly_recs = _generate_weekly_recommendations(matrix, risk_alerts, activity_summary)

    template = Template(weekly_template)
    html = template.render(
        week=week_id,
        report_time=now.strftime("%Y-%m-%d %H:%M"),
        app_count=len(matrix),
        avg_rating=avg_rating,
        activity_total=activity_total,
        critical_count=len(critical_risks),
        warning_count=len(warning_risks),
        matrix=matrix,
        top_activities=top_activities,
        critical_risks=critical_risks,
        warning_risks=warning_risks,
        app_names=app_names,
        app_ratings=app_ratings,
        pos_pcts=pos_pcts,
        neg_pcts=neg_pcts,
        weekly_recommendations=weekly_recs,
    )

    filepath.write_text(html, encoding="utf-8")
    logger.info("Weekly report saved: %s", filepath)
    return str(filepath)


def _generate_weekly_recommendations(
    matrix: list[dict],
    risk_alerts: list[dict],
    activity_summary: list[dict],
) -> list[dict]:
    """生成周度商务策略建议."""
    recs = []

    # 评分最低的App — 机会点
    sorted_by_rating = sorted(matrix, key=lambda x: x["rating"])
    if sorted_by_rating:
        lowest = sorted_by_rating[0]
        recs.append({
            "title": "合作机会识别",
            "advice": f"{lowest.get('bank','')}「{lowest['name']}」评分最低({lowest['rating']}★)，用户改善需求明显，可作为商务合作重点切入点。",
        })

    # 活动抓取洞察
    if activity_summary:
        by_cat: dict[str, int] = {}
        for a in activity_summary:
            by_cat[a["category"]] = by_cat.get(a["category"], 0) + a["count"]
        top_cat = max(by_cat, key=by_cat.get)
        recs.append({
            "title": "行业活动趋势",
            "advice": f"本周「{top_cat}」类活动在各银行App提及最多({by_cat[top_cat]}次)，建议评估是否有差异化方案可提供。",
        })

    # 风险热点
    if risk_alerts:
        top_risk = max(risk_alerts, key=lambda x: x.get("mention_count", 0))
        recs.append({
            "title": "风险预警响应",
            "advice": f"{top_risk.get('bank','')}「{top_risk['category']}」被提及{top_risk.get('mention_count',0)}次，建议在商务谈判中提前准备应对方案。",
        })

    recs.append({
        "title": "下周行动建议",
        "advice": f"持续监控 {len(matrix)} 家银行 App 评分和用户口碑，重点关注排名变化。",
    })

    return recs
