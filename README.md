# 银行信用卡业务竞品监控系统

基于 Apple App Store 公开数据的银行信用卡竞品监控工具，自动追踪各大银行信用卡 App 的评分变化、用户评论情感、**营销活动关键词**和**风险口碑**，输出竞品分析报告。

## 监控目标

中国区银行信用卡 App（招商银行掌上生活、建设银行、京东金融、交通银行买单吧、中信银行动卡空间等）：

| 银行 | App | App Store ID |
|------|-----|-------------|
| 招商银行 | 掌上生活 | 391119604 |
| 建设银行 | 中国建设银行 | 392005641 |
| 京东 | 京东金融 | 895682747 |
| 交通银行 | 买单吧 | 1022142579 |
| 中信银行 | 动卡空间 | 462493235 |

> 可在 `config.yaml` 的 `targets` 中自由增删银行 App（填入 App Store app_id 即可）。

## 功能模块

| 模块 | 功能 | 数据源 |
|------|------|---------|
| 数据采集 | App 元数据、评分、评论定时抓取 | iTunes Search / Lookup API |
| 评分追踪 | 评分变化趋势记录，异动预警 | iTunes Lookup API |
| 情感分析 | jieba 分词 + SnowNLP 评论情感打分 + 关键词提取 | RSS 评论 Feed |
| 竞品矩阵 | 多维度排名（评分/评论量），银行间定位分析 | 聚合计算 |
| **信用卡活动监测** | 从用户评论中识别新户礼、分期优惠、积分活动等关键词 | 评论 NLP + 关键词规则 |
| **信用卡风险口碑** | 自动检测发卡问题、权益缩水、客服体验等负面维度并预警 | 评论 NLP + 风险关键词 |
| 可视化报告 | Jinja2 + ECharts HTML 看板（评分/活动/风险三大分区） | 自动生成 |
| 自动通知 | 飞书/钉钉 Webhook 推送评分异动、活动洞察和风险预警 | Webhook |

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 一键执行：采集 → 分析 → 活动分析 → 报告
python main.py run

# 或分步执行
python main.py crawl      # 采集 App Store 实时数据
python main.py analyze    # 分析评分变化和评论情感
python main.py activity   # 信用卡活动 + 风险口碑分析
python main.py report     # 生成 HTML 看板报告
python main.py notify     # 推送预警通知
```

## 数据源说明

全部数据来自 Apple 官方公开接口，**无需注册 API Key**：

- 搜索接口：`https://itunes.apple.com/search`
- App 详情：`https://itunes.apple.com/cn/lookup?id={app_id}`
- 用户评论：`https://itunes.apple.com/cn/rss/customerreviews/id={app_id}/json`

## 配置文件

编辑 `config.yaml` 自定义监控目标：

```yaml
targets:
  - app_id: "391119604"       # App Store 中的 App ID
    name: "掌上生活"
    category: "银行信用卡"
    bank: "招商银行"
  # 添加更多银行 App...
```

信用卡活动关键词可在 `credit_card.activity_keywords` 中自定义扩展：

```yaml
credit_card:
  activity_keywords:
    新户礼: ["新户礼", "开卡礼", "首刷礼", ...]
    分期优惠: ["分期", "免息", "手续费", ...]
```

## 项目架构

```
├── main.py              # CLI 入口
├── config.yaml          # 配置文件
├── crawlers/
│   ├── base.py          # 基础爬虫（重试 + 限速 + Session）
│   └── store.py         # App Store API 封装
├── analysis/
│   ├── sentiment.py     # 情感分析（含信用卡风险维度）
│   ├── competitor.py    # 竞品对比矩阵
│   ├── price.py         # 评分变化检测
│   └── activities.py    # 信用卡活动 & 口碑监控（新增）
├── storage/db.py        # SQLite 存储
├── outputs/
│   ├── report.py        # HTML 报告生成（含活动/风险分区）
│   └── notify.py        # 飞书/钉钉 Webhook 推送
└── reports/             # 生成的 HTML 报告
```

## 报告样例

运行 `python main.py run` 后生成的 HTML 报告包含：

- **银行 App 概览** — 各银行 App 评分、评价数、趋势一览
- **评分对比** — 各银行评分柱状图
- **信用卡活动监测** — 银行间活动关键词提及对比（新户礼、分期、积分等）
- **信用卡风险口碑** — 发卡问题、权益缩水、客服体验等负面维度预警
- **情感分布** — 好评/中评/差评占比
- **运营建议** — 基于数据分析的 actionable 策略建议

## 技术栈

Python 3.10+ · requests · SnowNLP · jieba · Jinja2 · ECharts · SQLite

## 仓库地址

https://github.com/zhangrot-star/app_store_monitor
