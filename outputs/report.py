"""HTML report generation — App Store competitive intelligence dashboard."""

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
<title>App Store 竞品监控报告 — {{ report_time }}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f6fa; color: #333; }
.header { background: linear-gradient(135deg, #007AFF, #5856D6); color: #fff; padding: 30px 40px; }
.header h1 { font-size: 24px; margin-bottom: 6px; }
.header p { opacity: 0.85; font-size: 14px; }
.container { max-width: 1200px; margin: 0 auto; padding: 24px; }
.section { background: #fff; border-radius: 10px; padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.section h2 { font-size: 18px; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 2px solid #007AFF; }
.chart { width: 100%; height: 380px; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid #eee; font-size: 13px; }
th { background: #fafafa; font-weight: 600; color: #555; }
tr:hover { background: #f9f9f9; }
.alert { background: #fff3e0; border-left: 4px solid #ff9800; padding: 10px 14px; margin: 8px 0; border-radius: 4px; font-size: 13px; }
.alert.red { background: #ffebee; border-color: #e53935; }
.stars { color: #f5a623; font-weight: 700; }
.tag { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 11px; }
.tag.up { background: #ffebee; color: #c62828; }
.tag.down { background: #e8f5e9; color: #2e7d32; }
.tag.pos { background: #e8f5e9; color: #2e7d32; }
.tag.neg { background: #ffebee; color: #c62828; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 768px) { .grid-2 { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="header">
  <h1>App Store 竞品监控报告</h1>
  <p>数据源：Apple App Store | 生成时间：{{ report_time }} | 监控 {{ app_count }} 款竞品 App</p>
</div>

<div class="container">

  <!-- App Overview Table -->
  <div class="section">
    <h2>App 概览</h2>
    <table>
      <tr><th>App 名称</th><th>开发者</th><th>品类</th><th>当前版本</th><th>评分</th><th>评论数</th><th>趋势</th></tr>
      {% for r in matrix %}
      <tr>
        <td><strong>{{ r.name }}</strong></td>
        <td>{{ r.get('developer', '-') }}</td>
        <td>{{ r.get('category', '-') }}</td>
        <td>{{ r.get('current_ver', '-') }}</td>
        <td><span class="stars">{{ "%.2f"|format(r.rating|float) }} ★</span></td>
        <td>{{ "{:,}".format(r.rating_count|int) if r.rating_count else '-' }}</td>
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
    <h2>评分异动预警</h2>
    {% for a in alerts %}
    <div class="alert{% if a.direction == 'down' %} red{% endif %}">
      <strong>{{ a.name }}</strong>：
      {{ "%.2f"|format(a.previous_rating) }} ★ → {{ "%.2f"|format(a.current_rating) }} ★
      （{% if a.direction == 'up' %}↑{% else %}↓{% endif %}{{ "%.2f"|format(a.change|abs) }}）
      {% if a.direction == 'down' %}⚠ 评分下滑，建议关注最新版本用户反馈{% else %}评分提升，版本优化有效{% endif %}
    </div>
    {% endfor %}
  </div>
  {% endif %}

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

  <!-- Review Insights -->
  <div class="section">
    <h2>用户评价关键词</h2>
    <table>
      <tr><th>App</th><th>好评关键词</th><th>差评关键词</th><th>好评率</th><th>差评率</th></tr>
      {% for s in sentiment %}
      <tr>
        <td>{{ s.name }}</td>
        <td>{{ s.top_positive_words[:3]|join('、') if s.top_positive_words else '-' }}</td>
        <td>{{ s.top_negative_words[:3]|join('、') if s.top_negative_words else '-' }}</td>
        <td><span class="tag pos">{{ s.positive_pct }}%</span></td>
        <td><span class="tag neg">{{ s.negative_pct }}%</span></td>
      </tr>
      {% endfor %}
    </table>
  </div>

  <!-- Recommendations -->
  <div class="section">
    <h2>运营建议</h2>
    <table>
      <tr><th>维度</th><th>建议</th></tr>
      {% for rec in recommendations %}
      <tr>
        <td>{{ rec.dimension }}</td>
        <td>{{ rec.advice }}</td>
      </tr>
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
          {offset:0,color:'#5856D6'},{offset:1,color:'#007AFF'}
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

// Review counts
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
</script>
</body>
</html>"""


def generate_report(
    comparison: dict,
    alerts: list[dict],
    sentiment_data: list[dict],
    output_dir: str = "./reports",
) -> str:
    """Render HTML report and save to file."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    filename = f"app_monitor_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = Path(output_dir) / filename

    matrix = comparison.get("matrix", [])

    # Add rating change info to matrix
    alert_map = {a["app_id"]: a["change"] for a in alerts}
    for r in matrix:
        r["rating_change"] = alert_map.get(r["app_id"], 0)

    # Chart data
    rating_names = json.dumps([m["name"][:8] for m in matrix])
    rating_values = json.dumps([m["rating"] for m in matrix])
    sentiment_names = json.dumps([s["name"][:6] for s in sentiment_data])
    sentiment_pos = json.dumps([s["positive_pct"] for s in sentiment_data])
    sentiment_neu = json.dumps([s["neutral_pct"] for s in sentiment_data])
    sentiment_neg = json.dumps([s["negative_pct"] for s in sentiment_data])
    review_pie = json.dumps([
        {"value": m.get("review_total", 0), "name": m["name"][:8]}
        for m in matrix
    ])

    recommendations = _generate_recommendations(alerts, sentiment_data, comparison)

    template = Template(TEMPLATE)
    html = template.render(
        report_time=now,
        app_count=len(matrix),
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
    )

    filepath.write_text(html, encoding="utf-8")
    logger.info("Report saved: %s", filepath)
    return str(filepath)


def _generate_recommendations(
    alerts: list[dict],
    sentiment: list[dict],
    comparison: dict,
) -> list[dict]:
    recs = []

    # Rating alerts
    for a in alerts[:3]:
        if a["direction"] == "down":
            recs.append({
                "dimension": "评分监控",
                "advice": f"{a['name']}评分下滑{a['change']:.2f}，建议立即检查最新版本(a['version'])用户差评，重点关注崩溃、卡顿等体验问题。",
            })
        elif a["direction"] == "up":
            recs.append({
                "dimension": "评分监控",
                "advice": f"{a['name']}评分提升{a['change']:.2f}，竞品版本优化获得用户认可，建议分析对方改进点作为自身迭代参考。",
            })

    # Sentiment insights
    for s in sentiment:
        if s.get("negative_pct", 0) > 25:
            keywords = "、".join(s.get("top_negative_words", [])[:3])
            recs.append({
                "dimension": "口碑管理",
                "advice": f"{s['name']}差评率{s['negative_pct']}%，负面关键词：{keywords}。建议在自身产品中优先解决同类问题，形成差异化优势。",
            })

    # Competitive positioning
    rankings = comparison.get("rankings", {})
    top_rated = rankings.get("rating_high_to_low", [])
    if top_rated:
        recs.append({
            "dimension": "竞品定位",
            "advice": f"评分最高为{top_rated[0]}，建议深入分析其用户评价高频关键词，提炼可复用的产品/运营策略。",
        })

    if not recs:
        recs.append({
            "dimension": "整体评估",
            "advice": "当前各竞品 App 评分及用户评价稳定，未发现异常波动。建议保持每周监控频率。",
        })

    return recs
