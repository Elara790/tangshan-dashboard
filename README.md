# 唐山打人案 · 三路径舆论对比仪表盘

基于 Streamlit 的交互式舆论仿真可视化仪表盘。

## 功能

- 🕸️ **人物关系流光图** — 使用 streamlit-agraph 展示 Agent 关系网络，节点可点击查看详情
- 📊 **象限散点图** — 实时展示舆论 Agent 在四象限（愤怒/理性/官方/质疑）的分布
- 📋 **文字分析报告** — 三条路径各自的深度分析报告
- 📈 **演变趋势图** — 时间轴展示舆论动态变化
- 📊 **三路径对比** — Path A/B/C 全方位对比

## 三条路径

| 路径 | 含义 |
|------|------|
| Path A | 公开表态·有效传播 |
| Path B | 私下和解·保持沉默 |
| Path C | 表态传播失败·信息黑洞 |

## 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud 部署

1. Fork 或创建你自己的 GitHub 仓库
2. 将本项目文件推送到 GitHub
3. 在 [share.streamlit.io](https://share.streamlit.io) 中连接你的仓库
4. 设置 Main file path 为 `app.py`
5. 点击 Deploy！
