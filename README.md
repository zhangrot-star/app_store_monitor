# App Store Competitive Intelligence Monitor

App Store 竞品监控系统 — 基于 Apple App Store 真实公开数据，自动追踪竞品 App 评分、评论情感、版本迭代，输出运营分析报告。

## 监控目标

中国区 App Store 热门 App（电商/外卖/短视频/社交品类）：
淘宝、拼多多、得物、美团外卖、快手、Soul

## 功能模块

| 模块 | 功能 | 数据来源 |
|------|------|---------|
| 数据采集 | App 元数据、评分、评论定时抓取 | iTunes Search API + RSS |
| 评分追踪 | 评分变化趋势、异动预警（下滑 >0.3★ 自动标记） | iTunes Lookup API |
| 情感分析 | jieba 分词 + SnowNLP 评论情感打分 + 关键词提取 | RSS 评论 Feed |
| 竞品矩阵 | 多维度排名（评分 / 评论量 / 品类），竞品定位分析 | 聚合计算 |
| 可视化报告 | Jinja2 + ECharts HTML 看板 | 自动生成 |
| 自动通知 | 飞书/钉钉 Webhook 评分异动 + 口碑预警推送 | Webhook |

## 快速开始

```bash
pip install -r requirements.txt
python main.py run
```

或分步执行：

```bash
python main.py crawl      # 采集 App Store 数据
python main.py analyze    # 执行分析
python main.py report     # 生成 HTML 报告
```

## 数据源

全部来自 Apple 官方公开接口，无需 API Key：

- 搜索：`https://itunes.apple.com/search`
- 详情：`https://itunes.apple.com/cn/lookup?id={app_id}`
- 评论：`https://itunes.apple.com/cn/rss/customerreviews/id={app_id}/json`

## 配置

编辑 `config.yaml`：修改监控目标 App ID、品类、预警阈值等。

## 技术栈

Python 3.10+ · requests · BeautifulSoup4 · SnowNLP · jieba · Jinja2 · ECharts · SQLite
