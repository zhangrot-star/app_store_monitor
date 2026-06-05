# App Store 竞品监控系统

基于 Apple App Store 真实公开数据的竞品监控工具，自动追踪竞品 App 的评分变化、用户评论情感和版本迭代，输出运营分析报告。

## 监控目标

中国区 App Store 热门 App（电商 / 外卖 / 短视频 / 社交品类）：

| App | 当前评分 | 评分人数 |
|-----|---------|---------|
| 快手 | 4.84 ★ | 1,648 万 |
| Soul | 4.81 ★ | 320 万 |
| 美团外卖 | 4.80 ★ | 958 万 |
| 得物 | 4.72 ★ | 528 万 |
| 拼多多 | 4.21 ★ | 4 万 |
| 淘宝 | 4.14 ★ | 172 万 |

## 功能模块

| 模块 | 功能 | 数据来源 |
|------|------|---------|
| 数据采集 | App 元数据、评分、评论定时抓取 | iTunes Search / Lookup API |
| 评分追踪 | 评分变化趋势记录，异动预警（下滑超 0.3 分自动标记） | iTunes Lookup API |
| 情感分析 | jieba 分词 + SnowNLP 评论情感打分 + 好评/差评关键词提取 | RSS 评论 Feed |
| 竞品矩阵 | 多维度排名（评分 / 评论量 / 品类），竞品定位分析 | 聚合计算 |
| 可视化报告 | Jinja2 + ECharts HTML 看板（含评分柱状图、情感分布、评论饼图） | 自动生成 |
| 自动通知 | 飞书 / 钉钉 / 企业微信 Webhook 推送评分异动和口碑预警 | Webhook |

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 一键执行：采集 → 分析 → 报告
python main.py run

# 或分步执行
python main.py crawl      # 采集 App Store 实时数据
python main.py analyze    # 分析评分变化和评论情感
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
  - app_id: "387682726"       # App Store 中的 App ID
    name: "淘宝"
    category: "电商"
  # 添加更多监控目标...
```

## 技术栈

Python 3.10+ · requests · BeautifulSoup4 · SnowNLP · jieba · Jinja2 · ECharts · SQLite

## 仓库地址

https://github.com/zhangrot-star/app_store_monitor
