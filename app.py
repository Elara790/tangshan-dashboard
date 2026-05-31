"""
唐山打人案 · 三路径舆论对比 — Streamlit 交互式仪表盘
======================================================
功能:
  - 流光人物关系图 (streamlit-agraph) — 节点可点击查看详情
  - 象限散点图 — 动态展示各路径 Agent 分布
  - 文字报告 — 每条路径独立分析
  - 路径对比 — 三路径并排对比
  - 时间轴滑块 — 观察舆论演变过程

用法:
  source /home/elara/streamlit-env/bin/activate
  streamlit run /home/elara/Agent-Kernel/examples/tangshan_opinion/streamlit_dashboard.py
"""

import streamlit as st
import json
import random
import math
import os
import sys
import base64
import io
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# ---------- 页面配置 ----------
st.set_page_config(
    page_title="唐山打人案 · 三路径舆论对比",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- 常量和配置 ----------
PROJECT_DIR = Path(__file__).parent
DATA_FILE = PROJECT_DIR / "comparison_data.json"
CONFIGS_DIR = PROJECT_DIR / "configs"

QUADRANT_LABELS = {
    "tl": "愤怒/共情",
    "tr": "理性/法律",
    "bl": "官方/秩序",
    "br": "质疑/批判",
}
QUADRANT_COLORS = {
    "tl": "#ef4444",  # 红 - 愤怒
    "tr": "#3b82f6",  # 蓝 - 理性
    "bl": "#10b981",  # 绿 - 官方
    "br": "#f59e0b",  # 黄 - 质疑
}
QUADRANT_ICONS = {"tl": "🔥", "tr": "⚖️", "bl": "🏛️", "br": "❓"}

PATH_COLORS = {"A": "#3b82f6", "B": "#f59e0b", "C": "#ef4444"}
PATH_LABELS = {
    "A": "公开表态·有效传播",
    "B": "私下和解·保持沉默",
    "C": "表态传播失败·信息黑洞",
}
PATH_DESCRIPTIONS = {
    "A": "被害人通过央媒公开表态'不和解'，信息全国有效传播，法治框架得到巩固",
    "B": "被害人私下接受100万赔偿并沉默，和解信息通过非正式渠道泄露，阶层撕裂严重",
    "C": "被害人发声被限流压制，公众处于信息黑洞，阴谋论泛滥，信任全面崩塌",
}

# Agent 类型定义
AGENT_TYPES = {
    "citizen": {"label": "普通市民", "icon": "👤", "base_size": 15, "color": "#64748b"},
    "media": {"label": "媒体/自媒体", "icon": "📰", "base_size": 22, "color": "#8b5cf6"},
    "official": {"label": "官方/机构", "icon": "🏛️", "base_size": 25, "color": "#10b981"},
    "opinion_leader": {"label": "意见领袖", "icon": "📢", "base_size": 20, "color": "#f59e0b"},
    "victim_family": {"label": "受害方", "icon": "💔", "base_size": 18, "color": "#ef4444"},
    "legal_expert": {"label": "法律专家", "icon": "⚖️", "base_size": 18, "color": "#3b82f6"},
    "perpetrator_side": {"label": "施暴方关联", "icon": "⚠️", "base_size": 16, "color": "#dc2626"},
}

# ---------- 数据加载 ----------
@st.cache_data
def load_simulation_data() -> List[Dict]:
    """加载仿真对比数据"""
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@st.cache_data
def generate_agents(seed: int = 42) -> Dict[str, List[Dict]]:
    """
    为每条路径生成 100 个 Agent 的模拟数据。
    基于 comparison_data.json 中的象限分布来分配 Agent 位置。
    每个 Agent 有: id, name, type, quadrant, position(x,y), influence, connections, bio
    """
    data = load_simulation_data()
    rng = random.Random(seed)

    # 姓名字库
    surnames = ["李", "王", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴",
                "徐", "孙", "胡", "朱", "高", "林", "何", "郭", "马", "罗"]
    given_names = ["明", "华", "强", "伟", "芳", "敏", "静", "丽", "军", "磊",
                   "洋", "涛", "辉", "宁", "文", "博", "浩", "峰", "宇", "鹏"]

    all_agents = {}

    for path_data in data:
        path_id = path_data["id"]
        history = path_data["history"]
        final_tick = history[-1]  # 使用最后一个 tick 的分布

        agents = []
        agent_idx = 0
        total = sum(final_tick.values())  # 应该是 ~100

        # 意见领袖 (每路径 ~5个)
        opinion_leader_names = [
            {"name": "央视新闻", "type": "media", "influence": 95},
            {"name": "人民日报", "type": "media", "influence": 92},
            {"name": "微博大V-张某某", "type": "opinion_leader", "influence": 85},
            {"name": "法学教授-王教授", "type": "legal_expert", "influence": 78},
            {"name": "知名博主-李某", "type": "opinion_leader", "influence": 72},
        ]

        # 官方机构
        official_names = [
            {"name": "唐山公安局", "type": "official", "influence": 88},
            {"name": "河北省高院", "type": "official", "influence": 85},
            {"name": "中央政法委", "type": "official", "influence": 90},
            {"name": "全国妇联", "type": "official", "influence": 75},
            {"name": "唐山市宣传部", "type": "official", "influence": 70},
        ]

        # 受害方
        victim_names = [
            {"name": "被害人王某某", "type": "victim_family", "influence": 80},
            {"name": "被害人李某", "type": "victim_family", "influence": 65},
            {"name": "被害人家属-王父", "type": "victim_family", "influence": 55},
            {"name": "被害人家属-李母", "type": "victim_family", "influence": 50},
        ]

        # 施暴方关联
        perpetrator_names = [
            {"name": "施暴者陈某志", "type": "perpetrator_side", "influence": 30},
            {"name": "施暴者同伙-刘某", "type": "perpetrator_side", "influence": 20},
            {"name": "辩护律师-赵某", "type": "legal_expert", "influence": 45},
        ]

        # 法律专家
        legal_names = [
            {"name": "刑法学者-陈教授", "type": "legal_expert", "influence": 70},
            {"name": "律师-周某", "type": "legal_expert", "influence": 60},
            {"name": "法学评论员-吴某", "type": "legal_expert", "influence": 55},
        ]

        specials = (opinion_leader_names + official_names + victim_names +
                    perpetrator_names + legal_names)

        for s in specials:
            # 根据类型分配到不同象限
            t = s["type"]
            if t in ["media", "official"]:
                quad = rng.choice(["bl", "tr"])  # 官方/秩序 或 理性/法律
            elif t in ["victim_family"]:
                quad = rng.choice(["tl", "tr"])  # 愤怒/共情 或 理性/法律
            elif t in ["perpetrator_side"]:
                quad = rng.choice(["br", "bl"])  # 质疑区 或 官方区
            elif t in ["opinion_leader"]:
                quad = rng.choice(["tl", "tr", "br"])  # 可能在多个象限
            else:
                quad = rng.choice(["tl", "tr", "bl", "br"])

            pos = _random_position_in_quadrant(quad, rng)
            agent = {
                "id": f"agent_{path_id}_{agent_idx:03d}",
                "name": s["name"],
                "type": t,
                "type_label": AGENT_TYPES[t]["label"],
                "type_icon": AGENT_TYPES[t]["icon"],
                "quadrant": quad,
                "quadrant_label": QUADRANT_LABELS[quad],
                "x": pos[0],
                "y": pos[1],
                "influence": s["influence"],
                "connections": [],
                "bio": _generate_bio(t, quad, path_id),
                "stance": _generate_stance(quad, path_id),
                "evolution": [quad],  # 演变轨迹
            }
            agents.append(agent)
            agent_idx += 1
            # 减少对应象限的配额
            final_tick[quad] = max(0, final_tick[quad] - 1)

        # 生成剩余的普通市民 Agent
        for quad, count in final_tick.items():
            for _ in range(count):
                pos = _random_position_in_quadrant(quad, rng)
                name = f"{rng.choice(surnames)}{rng.choice(given_names)}"
                agent = {
                    "id": f"agent_{path_id}_{agent_idx:03d}",
                    "name": name,
                    "type": "citizen",
                    "type_label": AGENT_TYPES["citizen"]["label"],
                    "type_icon": AGENT_TYPES["citizen"]["icon"],
                    "quadrant": quad,
                    "quadrant_label": QUADRANT_LABELS[quad],
                    "x": pos[0],
                    "y": pos[1],
                    "influence": rng.randint(5, 40),
                    "connections": [],
                    "bio": _generate_bio("citizen", quad, path_id),
                    "stance": _generate_stance(quad, path_id),
                    "evolution": [quad],
                }
                agents.append(agent)
                agent_idx += 1

        # 生成连接关系 (基于位置距离和影响力)
        for i, a in enumerate(agents):
            others = [o for j, o in enumerate(agents) if j != i]
            # 按距离排序，最近的优先
            others.sort(key=lambda o: math.dist((a["x"], a["y"]), (o["x"], o["y"])))
            # 取最近的 2~5 个建立连接
            num_conn = rng.randint(2, min(5, len(others)))
            for o in others[:num_conn]:
                a["connections"].append({
                    "target": o["id"],
                    "weight": round(rng.uniform(0.3, 1.0), 2),
                    "type": rng.choice(["信息传播", "观点影响", "社交关联", "情绪感染"]),
                })

        all_agents[path_id] = agents

    return all_agents


def _random_position_in_quadrant(quad: str, rng: random.Random) -> Tuple[float, float]:
    """在指定象限内生成随机位置 (0-300 坐标系)"""
    if quad == "tl":
        return (rng.uniform(10, 140), rng.uniform(10, 140))
    elif quad == "tr":
        return (rng.uniform(160, 290), rng.uniform(10, 140))
    elif quad == "bl":
        return (rng.uniform(10, 140), rng.uniform(160, 290))
    else:  # br
        return (rng.uniform(160, 290), rng.uniform(160, 290))


def _generate_bio(agent_type: str, quadrant: str, path_id: str) -> str:
    """为 Agent 生成人物简介"""
    bios = {
        "citizen": {
            "tl": "普通市民，对暴力事件感到极度愤怒，在社交媒体上积极发声，呼吁严惩施暴者。",
            "tr": "关注事件的市民，倾向于从法律角度分析问题，相信司法程序能带来公正。",
            "bl": "市民，倾向于信任官方通报，支持政府依法处理事件，维护社会秩序。",
            "br": "市民，对事件处理持怀疑态度，质疑信息透明度，担忧权力干预司法。",
        },
        "media": {
            "tl": "媒体从业者，以情感化叙事报道事件，引发公众对女性安全的广泛讨论。",
            "tr": "深度报道记者，聚焦法律程序和制度层面的问题，推动理性公共讨论。",
            "bl": "官方媒体，按照口径报道事件进展，强调法治和秩序维护。",
            "br": "独立媒体人，调查报道事件背后的权力关系，揭露可能的信息封锁。",
        },
        "official": {
            "tl": "基层执法人员，对暴力行为表示强烈谴责，承诺依法办案。",
            "tr": "司法系统官员，强调依法独立办案，推动案件进入司法程序。",
            "bl": "政府机构代表，发布权威信息，维护社会稳定和公众信心。",
            "br": "体制内反思者，意识到信息不透明带来的信任危机，内部呼吁改革。",
        },
        "opinion_leader": {
            "tl": "有影响力的网络意见人士，以情感动员方式凝聚公众愤怒，推动舆论发酵。",
            "tr": "公共知识分子，从法学和社会学角度分析事件，引导理性讨论。",
            "bl": "具有一定影响力的评论者，倾向于维护主流叙事框架。",
            "br": "体制批判型意见领袖，质疑官方叙事，推动深层制度反思。",
        },
        "victim_family": {
            "tl": "受害者或其家属，身心受到严重伤害，对公正有着迫切而强烈的要求。",
            "tr": "受害方代表，希望通过法律途径获得公正，同时保持理性和克制。",
        },
        "legal_expert": {
            "tl": "法律从业者，对暴力犯罪的恶劣性质感到愤慨，呼吁从严惩处。",
            "tr": "法学专家，从专业角度分析案件的法律定性和量刑标准。",
            "bl": "体制内法律工作者，在法治框架内参与案件处理。",
            "br": "律师或法学研究者，对司法过程中可能的程序瑕疵保持警惕。",
        },
        "perpetrator_side": {
            "bl": "施暴者方相关人员，试图通过法律手段减轻责任。",
            "br": "施暴者关联人，处于舆论漩涡中，面临巨大社会压力。",
        },
    }
    default_bio = f"事件相关方，处于{QUADRANT_LABELS.get(quadrant, '未知')}象限。"
    return bios.get(agent_type, {}).get(quadrant, default_bio)


def _generate_stance(quadrant: str, path_id: str) -> str:
    """根据象限和路径生成 Agent 的核心立场"""
    stances = {
        "tl": [
            "严惩施暴者，给受害者一个公道",
            "暴力零容忍，社会安全不容践踏",
            "女性的安全感是社会文明的底线",
        ],
        "tr": [
            "相信法律，依法裁判是唯一正解",
            "程序正义和实体正义同样重要",
            "完善公共安全法律体系刻不容缓",
        ],
        "bl": [
            "依法办事，维护社会大局稳定",
            "官方信息是最可靠的权威来源",
            "支持政府雷霆行动，相信法治力量",
        ],
        "br": [
            "信息必须透明，公众有权知道真相",
            "质疑权力运作，警惕司法不公",
            "资本和权力不应凌驾于法律之上",
        ],
    }
    return random.Random(hash(f"{quadrant}_{path_id}")).choice(stances.get(quadrant, ["关注事件进展"]))


# ---------- 图表函数 ----------

def render_relationship_graph(agents: List[Dict], path_id: str, key_suffix: str = ""):
    """
    使用 streamlit-agraph 渲染人物关系图。
    返回被点击的节点信息。
    """
    from streamlit_agraph import agraph, Node, Edge, Config

    nodes = []
    edges = []
    seen_edges = set()

    for a in agents:
        quad_color = QUADRANT_COLORS.get(a["quadrant"], "#64748b")
        node_size = AGENT_TYPES[a["type"]]["base_size"] + a["influence"] * 0.15
        label = f"{a['type_icon']} {a['name']}"
        nodes.append(Node(
            id=a["id"],
            label=label,
            size=node_size,
            color=quad_color,
            shape="dot" if a["type"] == "citizen" else "star",
            title=f"<b>{a['name']}</b><br>"
                  f"类型: {a['type_label']}<br>"
                  f"象限: {a['quadrant_label']}<br>"
                  f"影响力: {a['influence']}<br>"
                  f"立场: {a['stance']}",
            borderWidth=2,
            borderWidthSelected=4,
        ))

        for conn in a.get("connections", []):
            edge_key = tuple(sorted([a["id"], conn["target"]]))
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                edges.append(Edge(
                    source=a["id"],
                    target=conn["target"],
                    label=conn["type"],
                    width=conn["weight"] * 2,
                    color={"color": "#475569", "opacity": 0.3},
                ))

    config = Config(
        width="100%",
        height=600,
        directed=False,
        physics={
            "barnesHut": {
                "gravitationalConstant": -3000,
                "centralGravity": 0.3,
                "springLength": 120,
                "springConstant": 0.04,
                "damping": 0.09,
            },
            "minVelocity": 0.75,
            "maxVelocity": 30,
        },
        interaction={
            "hover": True,
            "tooltipDelay": 200,
            "zoomView": True,
            "dragView": True,
            "navigationButtons": True,
        },
        node={
            "font": {"size": 10, "color": "#cbd5e1", "face": "Microsoft YaHei"},
        },
        edge={
            "font": {"size": 8, "color": "#64748b", "strokeWidth": 0},
            "smooth": {"type": "continuous", "roundness": 0.5},
        },
    )

    return agraph(nodes=nodes, edges=edges, config=config)


def render_scatter_chart(agents: List[Dict], height: int = 400):
    """使用 Altair 渲染象限散点图"""
    import altair as alt
    import pandas as pd

    df = pd.DataFrame([
        {
            "x": a["x"],
            "y": a["y"],
            "象限": a["quadrant_label"],
            "类型": a["type_label"],
            "影响力": a["influence"],
            "名称": a["name"],
        }
        for a in agents
    ])

    # 颜色映射
    color_scale = alt.Scale(
        domain=list(QUADRANT_LABELS.values()),
        range=[QUADRANT_COLORS["tl"], QUADRANT_COLORS["tr"],
               QUADRANT_COLORS["bl"], QUADRANT_COLORS["br"]],
    )

    # 分割线
    vline = alt.Chart(pd.DataFrame({"x": [150]})).mark_rule(
        strokeDash=[5, 5], color="#475569"
    ).encode(x="x:Q")
    hline = alt.Chart(pd.DataFrame({"y": [150]})).mark_rule(
        strokeDash=[5, 5], color="#475569"
    ).encode(y="y:Q")

    scatter = alt.Chart(df).mark_circle(opacity=0.7).encode(
        x=alt.X("x:Q", scale=alt.Scale(domain=[-10, 310]), title=""),
        y=alt.Y("y:Q", scale=alt.Scale(domain=[-10, 310]), title=""),
        size=alt.Size("影响力:Q", scale=alt.Scale(range=[40, 250]), legend=None),
        color=alt.Color("象限:N", scale=color_scale, legend=alt.Legend(orient="bottom")),
        tooltip=["名称", "类型", "象限", "影响力"],
    ).properties(height=height)

    # 象限标签
    quad_texts = pd.DataFrame([
        {"x": 75, "y": 20, "text": "愤怒/共情"},
        {"x": 225, "y": 20, "text": "理性/法律"},
        {"x": 75, "y": 295, "text": "官方/秩序"},
        {"x": 225, "y": 295, "text": "质疑/批判"},
    ])
    text_layer = alt.Chart(quad_texts).mark_text(
        fontSize=11, color="#94a3b8", opacity=0.7
    ).encode(x="x:Q", y="y:Q", text="text:N")

    chart = (vline + hline + scatter + text_layer).configure(
        background="#0f172a",
        view={"stroke": "#1e293b"},
    ).configure_axis(
        gridColor="#1e293b",
        tickColor="#475569",
        labelColor="#64748b",
        domainColor="#475569",
    )

    return chart


def render_quadrant_timeline(simulation_data: List[Dict], height: int = 300):
    """使用 Altair 渲染象限分布随时间变化"""
    import altair as alt
    import pandas as pd

    rows = []
    for path_data in simulation_data:
        path_id = path_data["id"]
        for tick_idx, tick in enumerate(path_data["history"]):
            for quad_key, quad_label in QUADRANT_LABELS.items():
                rows.append({
                    "Tick": tick_idx,
                    "路径": f"Path {path_id}: {PATH_LABELS[path_id]}",
                    "象限": quad_label,
                    "人数": tick[quad_key],
                })
    df = pd.DataFrame(rows)

    color_scale = alt.Scale(
        domain=list(QUADRANT_LABELS.values()),
        range=[QUADRANT_COLORS["tl"], QUADRANT_COLORS["tr"],
               QUADRANT_COLORS["bl"], QUADRANT_COLORS["br"]],
    )

    chart = alt.Chart(df).mark_line(point=True, strokeWidth=2.5).encode(
        x=alt.X("Tick:O", title="Tick"),
        y=alt.Y("人数:Q", title="Agent 数量"),
        color=alt.Color("象限:N", scale=color_scale, legend=alt.Legend(orient="bottom")),
        strokeDash=alt.StrokeDash("路径:N", scale=alt.Scale(
            domain=sorted(df["路径"].unique()),
            range=[[1, 0], [5, 3], [1, 1]],
        )),
    ).properties(height=height).facet(
        column=alt.Column("路径:N", title=None, header=alt.Header(
            labelFontSize=13, labelColor="#e2e8f0"
        )),
    ).configure(
        background="#0f172a",
        view={"stroke": "#1e293b"},
    ).configure_axis(
        gridColor="#1e293b",
        tickColor="#475569",
        labelColor="#64748b",
        domainColor="#475569",
        titleColor="#94a3b8",
    ).configure_legend(
        labelColor="#94a3b8",
        titleColor="#94a3b8",
    )

    return chart


# ---------- CSS 样式 ----------
def inject_css():
    st.markdown("""
    <style>
    /* ---- 全局 ---- */
    .stApp {
        background: #0b1120;
    }
    section[data-testid="stSidebar"] {
        background: #111b2a;
        border-right: 1px solid #2d3a4a;
    }
    section[data-testid="stSidebar"] * {
        color: #e2e8f0;
    }

    /* ---- 卡片 ---- */
    .detail-card {
        background: linear-gradient(135deg, #1a2332 0%, #1e293b 100%);
        border: 1px solid #2d3a4a;
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
    }
    .detail-card h3 {
        margin: 0 0 8px 0;
        font-size: 20px;
    }
    .detail-card .type-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
        margin-right: 8px;
    }
    .path-card-a { border-left: 4px solid #3b82f6; }
    .path-card-b { border-left: 4px solid #f59e0b; }
    .path-card-c { border-left: 4px solid #ef4444; }

    /* ---- 指标 ---- */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin: 16px 0;
    }
    .metric-item {
        background: #111b2a;
        border: 1px solid #2d3a4a;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }
    .metric-item .value {
        font-size: 28px;
        font-weight: bold;
    }
    .metric-item .label {
        font-size: 12px;
        color: #94a3b8;
        margin-top: 4px;
    }

    /* ---- 报告文本 ---- */
    .report-text {
        background: #111b2a;
        border: 1px solid #2d3a4a;
        border-radius: 8px;
        padding: 20px;
        line-height: 1.9;
        font-size: 14px;
        color: #cbd5e1;
    }
    .report-text h4 {
        color: #e2e8f0;
        margin-top: 16px;
        margin-bottom: 8px;
    }
    .report-text .highlight {
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: bold;
    }
    .highlight-red { background: rgba(239,68,68,0.2); color: #fca5a5; }
    .highlight-blue { background: rgba(59,130,246,0.2); color: #93c5fd; }
    .highlight-green { background: rgba(16,185,129,0.2); color: #6ee7b7; }
    .highlight-yellow { background: rgba(245,158,11,0.2); color: #fcd34d; }
    </style>
    """, unsafe_allow_html=True)


# ---------- 报告导出 ----------

def _build_single_report_html(path_id: str, agents: List[Dict],
                              path_data: Dict, all_paths: List[Dict]) -> str:
    """构建单条路径的完整 HTML 报告"""
    quad_counts = {"tl": 0, "tr": 0, "bl": 0, "br": 0}
    type_counts = {}
    total_influence = 0
    for a in agents:
        quad_counts[a["quadrant"]] += 1
        type_counts[a["type_label"]] = type_counts.get(a["type_label"], 0) + 1
        total_influence += a["influence"]
    avg_influence = total_influence / len(agents) if agents else 0

    first_tick = path_data["history"][0]
    final_tick = path_data["history"][-1]
    path_label = PATH_LABELS[path_id]
    color = PATH_COLORS[path_id]

    if path_id == "A":
        assessment, assess_class = "正面", "green"
    elif path_id == "B":
        assessment, assess_class = "负面", "yellow"
    else:
        assessment, assess_class = "严重", "red"

    # 构建 Agent 表格行
    agent_rows = ""
    for a in sorted(agents, key=lambda a: a["influence"], reverse=True):
        qc = QUADRANT_COLORS.get(a["quadrant"], "#64748b")
        agent_rows += f"""
        <tr>
            <td>{a['type_icon']} {a['name']}</td>
            <td>{a['type_label']}</td>
            <td><span style="color:{qc}">●</span> {a['quadrant_label']}</td>
            <td>{a['influence']}</td>
            <td style="font-size:12px;max-width:260px;">{a['stance']}</td>
        </tr>"""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Path {path_id}: {path_label} — 分析报告</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Microsoft YaHei','PingFang SC',sans-serif;background:#0b1120;color:#e2e8f0;line-height:1.8;padding:40px;max-width:1100px;margin:0 auto}}
h1{{font-size:26px;margin-bottom:4px}}
h2{{font-size:20px;margin:28px 0 12px;padding-bottom:8px;border-bottom:1px solid #2d3a4a}}
h3{{font-size:16px;color:#94a3b8;margin-bottom:20px}}
.meta{{color:#64748b;font-size:12px;margin-bottom:24px}}
.card{{background:#1a2332;border:1px solid #2d3a4a;border-radius:10px;padding:20px;margin:16px 0}}
.card.a{{border-left:4px solid #3b82f6}}
.card.b{{border-left:4px solid #f59e0b}}
.card.c{{border-left:4px solid #ef4444}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0}}
.metric{{background:#111b2a;border:1px solid #2d3a4a;border-radius:8px;padding:16px;text-align:center}}
.metric .val{{font-size:28px;font-weight:bold}}
.metric .lbl{{font-size:12px;color:#94a3b8;margin-top:4px}}
table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:13px}}
th{{background:#111b2a;color:#94a3b8;padding:10px 12px;text-align:left;border-bottom:2px solid #2d3a4a}}
td{{padding:8px 12px;border-bottom:1px solid #1e293b}}
.hl-green{{background:rgba(16,185,129,0.15);color:#6ee7b7;padding:1px 6px;border-radius:4px}}
.hl-yellow{{background:rgba(245,158,11,0.15);color:#fcd34d;padding:1px 6px;border-radius:4px}}
.hl-red{{background:rgba(239,68,68,0.15);color:#fca5a5;padding:1px 6px;border-radius:4px}}
.hl-blue{{background:rgba(59,130,246,0.15);color:#93c5fd;padding:1px 6px;border-radius:4px}}
.finding{{display:flex;gap:10px;align-items:flex-start;padding:8px 0}}
.finding .icon{{font-size:18px;flex-shrink:0}}
.footer{{margin-top:40px;padding-top:16px;border-top:1px solid #2d3a4a;color:#64748b;font-size:11px;text-align:center}}
@media print{{body{{background:#fff;color:#000}} .card{{background:#f8f9fa;border-color:#ddd}}}}
</style>
</head>
<body>

<h1>📋 Path {path_id}: {path_label}</h1>
<h3>综合评估: <span class="hl-{assess_class}">{assessment}</span></h3>
<p class="meta">生成时间: {timestamp} | 仿真框架: ZJU Agent-Kernel | Agent 数量: {len(agents)}</p>

<div class="card {path_id.lower()}">
<h2>📊 数据总览</h2>
<div class="metrics">
<div class="metric"><div class="val" style="color:{QUADRANT_COLORS['bl']}">{final_tick['bl']}</div><div class="lbl">🏛️ 官方/秩序</div></div>
<div class="metric"><div class="val" style="color:{QUADRANT_COLORS['br']}">{final_tick['br']}</div><div class="lbl">❓ 质疑/批判</div></div>
<div class="metric"><div class="val" style="color:{QUADRANT_COLORS['tl']}">{final_tick['tl']}</div><div class="lbl">🔥 愤怒/共情</div></div>
<div class="metric"><div class="val" style="color:{QUADRANT_COLORS['tr']}">{final_tick['tr']}</div><div class="lbl">⚖️ 理性/法律</div></div>
</div>
<p>平均影响力指数: <strong>{avg_influence:.1f}</strong> | 总连接数: {sum(len(a.get('connections',[])) for a in agents)}</p>
<p>官区变化: {first_tick['bl']}→{final_tick['bl']} | 疑区变化: {first_tick['br']}→{final_tick['br']}</p>
</div>

<div class="card {path_id.lower()}">
<h2>🗺️ 象限分布分析</h2>
<p>官方/秩序象限（🏛️）: <strong>{quad_counts['bl']}</strong> 个 Agent ({quad_counts['bl']/len(agents)*100:.0f}%)</p>
<p>质疑/批判象限（❓）: <strong>{quad_counts['br']}</strong> 个 Agent ({quad_counts['br']/len(agents)*100:.0f}%)</p>
<p>愤怒/共情象限（🔥）: <strong>{quad_counts['tl']}</strong> 个 Agent ({quad_counts['tl']/len(agents)*100:.0f}%)</p>
<p>理性/法律象限（⚖️）: <strong>{quad_counts['tr']}</strong> 个 Agent ({quad_counts['tr']/len(agents)*100:.0f}%)</p>
</div>

<div class="card {path_id.lower()}">
<h2>🔑 关键发现</h2>
{_key_findings_html(path_id)}
</div>

<div class="card {path_id.lower()}">
<h2>👥 Agent 详情列表</h2>
<table>
<thead><tr><th>名称</th><th>类型</th><th>象限</th><th>影响力</th><th>核心立场</th></tr></thead>
<tbody>{agent_rows}</tbody>
</table>
</div>

<div class="card {path_id.lower()}">
<h2>📈 象限演变数据</h2>
<table>
<thead><tr><th>Tick</th><th>🔥 愤怒/共情</th><th>⚖️ 理性/法律</th><th>🏛️ 官方/秩序</th><th>❓ 质疑/批判</th></tr></thead>
<tbody>
{_build_tick_table(path_data["history"])}
</tbody>
</table>
</div>

<div class="footer">
<p>唐山打人案 · 三路径舆论对比仿真 | Path {path_id}: {path_label} | {timestamp}</p>
</div>
</body>
</html>"""


def _key_findings_html(path_id: str) -> str:
    findings = {
        "A": [
            ("✅", "公开表态有效传递，信息触达率 > 90%"),
            ("✅", "谣言被有效遏制，舆论高度统一"),
            ("✅", "司法信任维持在较高水平"),
            ("⚠️", "需持续关注受害人权益保障的长期性"),
        ],
        "B": [
            ("❌", "私下和解严重损害司法公信力"),
            ("❌", "沉默制造信息真空，谣言泛滥"),
            ("❌", "阶层撕裂加剧，'有钱vs没钱'主导舆论"),
            ("⚠️", "即使判决相同，公众信任度显著低于Path A"),
        ],
        "C": [
            ("❌", "信息压制导致全面信任崩塌——最危险的路径"),
            ("❌", "阴谋论填补信息真空，辟谣完全失效"),
            ("❌", "公众对信息生态和司法系统双重不信任"),
            ("❌", "信任损伤几乎不可逆，国际舆论负面报道激增"),
        ],
    }
    return "".join(
        f'<div class="finding"><span class="icon">{icon}</span><span>{text}</span></div>'
        for icon, text in findings.get(path_id, [])
    )


def _build_tick_table(history: List[Dict]) -> str:
    rows = ""
    for i, tick in enumerate(history):
        rows += f"<tr><td>{i}</td><td>{tick['tl']}</td><td>{tick['tr']}</td><td>{tick['bl']}</td><td>{tick['br']}</td></tr>"
    return rows


def _build_comparison_html(simulation_data: List[Dict], all_agents: Dict[str, List[Dict]]) -> str:
    """构建三路径对比 HTML 报告"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 对比表格
    comp_rows = ""
    comp_data = [
        ("被害人表态", "公开'不和解'", "私下接受100万", "发声被限流压制"),
        ("信息渠道", "央媒全国传播", "微信群朋友圈泄露", "平台限流+删帖"),
        ("主导叙事框架", "正义 vs 邪恶", "有钱 vs 没钱", "真相被掩盖"),
        ("信息触达率", "> 90%", "~40%（碎片化）", "< 5%"),
        ("舆论极化度", "低", "高", "极度碎片化"),
        ("谣言控制", "有效遏制", "广泛传播", "完全失控"),
        ("司法信任度", "高 ✅", "极低 ❌", "崩溃 ❌"),
    ]
    for dim, a, b, c in comp_data:
        comp_rows += f"<tr><td>{dim}</td><td>{a}</td><td>{b}</td><td>{c}</td></tr>"

    # 路径卡片
    path_cards = ""
    for i, path_data in enumerate(simulation_data):
        pid = path_data["id"]
        final = path_data["history"][-1]
        first = path_data["history"][0]
        agents = all_agents.get(pid, [])
        quad_counts = {"tl": 0, "tr": 0, "bl": 0, "br": 0}
        for a in agents:
            quad_counts[a["quadrant"]] += 1
        path_cards += f"""
        <div class="card {pid.lower()}">
            <h3 style="color:{PATH_COLORS[pid]}">Path {pid}: {PATH_LABELS[pid]}</h3>
            <p style="color:#94a3b8">{PATH_DESCRIPTIONS[pid]}</p>
            <div class="metrics" style="grid-template-columns:repeat(2,1fr)">
                <div class="metric"><div class="val" style="color:{QUADRANT_COLORS['bl']}">{final['bl']}</div><div class="lbl">🏛️ 官方/秩序</div></div>
                <div class="metric"><div class="val" style="color:{QUADRANT_COLORS['br']}">{final['br']}</div><div class="lbl">❓ 质疑/批判</div></div>
            </div>
            <p style="font-size:12px;color:#64748b">官区: {first['bl']}→{final['bl']} | 疑区: {first['br']}→{final['br']}</p>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>唐山打人案 · 三路径对比综合报告</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Microsoft YaHei','PingFang SC',sans-serif;background:#0b1120;color:#e2e8f0;line-height:1.8;padding:40px;max-width:1100px;margin:0 auto}}
h1{{font-size:28px;margin-bottom:4px}}
h2{{font-size:20px;margin:28px 0 12px;padding-bottom:8px;border-bottom:1px solid #2d3a4a}}
h3{{font-size:16px;color:#94a3b8;margin-bottom:16px}}
.meta{{color:#64748b;font-size:12px;margin-bottom:24px}}
.card{{background:#1a2332;border:1px solid #2d3a4a;border-radius:10px;padding:20px;margin:16px 0}}
.card.a{{border-left:4px solid #3b82f6}}
.card.b{{border-left:4px solid #f59e0b}}
.card.c{{border-left:4px solid #ef4444}}
.metrics{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin:16px 0}}
.metric{{background:#111b2a;border:1px solid #2d3a4a;border-radius:8px;padding:16px;text-align:center}}
.metric .val{{font-size:28px;font-weight:bold}}
.metric .lbl{{font-size:12px;color:#94a3b8;margin-top:4px}}
table{{width:100%;border-collapse:collapse;margin:12px 0;font-size:13px}}
th{{background:#111b2a;color:#94a3b8;padding:10px 12px;text-align:left;border-bottom:2px solid #2d3a4a}}
td{{padding:8px 12px;border-bottom:1px solid #1e293b}}
.hl-green{{background:rgba(16,185,129,0.15);color:#6ee7b7;padding:1px 6px;border-radius:4px}}
.hl-red{{background:rgba(239,68,68,0.15);color:#fca5a5;padding:1px 6px;border-radius:4px}}
.conclusion{{background:linear-gradient(135deg,#1a2332,#1e293b);border:2px solid #3b82f6;border-radius:12px;padding:24px;margin:24px 0;text-align:center}}
.footer{{margin-top:40px;padding-top:16px;border-top:1px solid #2d3a4a;color:#64748b;font-size:11px;text-align:center}}
@media print{{body{{background:#fff;color:#000}} .card{{background:#f8f9fa;border-color:#ddd}}}}
</style>
</head>
<body>

<h1>📊 唐山打人案 · 三路径舆论对比</h1>
<h3>综合仿真分析报告</h3>
<p class="meta">生成时间: {timestamp} | 仿真框架: ZJU Agent-Kernel | 100 Agent × 5 Ticks × 3 Paths | LLM: DeepSeek-Chat</p>

<h2>📋 三路径概览</h2>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px">{path_cards}</div>

<h2>📊 核心维度对比</h2>
<div class="card">
<table>
<thead><tr><th>维度</th><th>Path A: 有效传播</th><th>Path B: 私下和解</th><th>Path C: 信息黑洞</th></tr></thead>
<tbody>{comp_rows}</tbody>
</table>
</div>

<h2>🔢 仿真数据详情</h2>
<div class="card">
<h3>Path A: {PATH_LABELS['A']}</h3>
<table><thead><tr><th>Tick</th><th>🔥 愤怒</th><th>⚖️ 理性</th><th>🏛️ 官方</th><th>❓ 质疑</th></tr></thead>
<tbody>{_build_tick_table(simulation_data[0]['history'])}</tbody></table>
<br>
<h3>Path B: {PATH_LABELS['B']}</h3>
<table><thead><tr><th>Tick</th><th>🔥 愤怒</th><th>⚖️ 理性</th><th>🏛️ 官方</th><th>❓ 质疑</th></tr></thead>
<tbody>{_build_tick_table(simulation_data[1]['history'])}</tbody></table>
<br>
<h3>Path C: {PATH_LABELS['C']}</h3>
<table><thead><tr><th>Tick</th><th>🔥 愤怒</th><th>⚖️ 理性</th><th>🏛️ 官方</th><th>❓ 质疑</th></tr></thead>
<tbody>{_build_tick_table(simulation_data[2]['history'])}</tbody></table>
</div>

<h2>🎯 综合结论</h2>
<div class="conclusion">
    <p style="font-size:18px;font-weight:bold;margin-bottom:12px;">信息透明度与舆论稳定性呈<span class="hl-green">正相关</span></p>
    <p style="color:#94a3b8">公开传播 → 舆论理性化 → 司法信任巩固<br>信息压制 → 谣言泛滥 → 信任全面崩塌</p>
</div>
<div class="card">
    <p><strong>Path A:</strong> <span class="hl-green">公开透明不会削弱政府权威，反而通过疏导公众情绪来巩固法治信任。</span></p>
    <p><strong>Path B:</strong> <span class="hl-green" style="background:rgba(245,158,11,0.15);color:#fcd34d">私下和解虽能暂时平息个案，但信息泄露后造成的信任损害远大于短期收益。</span></p>
    <p><strong>Path C:</strong> <span class="hl-red">信息压制是最危险的策略——制造的信息黑洞会被阴谋论完全填充，造成几乎不可逆的系统性信任崩塌。</span></p>
</div>

<div class="footer"><p>唐山打人案 · 三路径舆论对比仿真综合报告 | {timestamp}</p></div>
</body>
</html>"""


def _build_csv_data(simulation_data: List[Dict]) -> str:
    """构建仿真数据 CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Path", "Path_Label", "Tick", "愤怒共情(tl)", "理性法律(tr)", "官方秩序(bl)", "质疑批判(br)"])
    for path_data in simulation_data:
        pid = path_data["id"]
        label = PATH_LABELS[pid]
        for tick_idx, tick in enumerate(path_data["history"]):
            writer.writerow([pid, label, tick_idx, tick["tl"], tick["tr"], tick["bl"], tick["br"]])
    return output.getvalue()


def _build_agents_csv(all_agents: Dict[str, List[Dict]]) -> str:
    """构建 Agent 数据 CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Path", "Agent_ID", "名称", "类型", "象限", "影响力", "x坐标", "y坐标", "核心立场", "简介"])
    for path_id, agents in all_agents.items():
        for a in agents:
            writer.writerow([
                path_id, a["id"], a["name"], a["type_label"], a["quadrant_label"],
                a["influence"], f"{a['x']:.1f}", f"{a['y']:.1f}", a["stance"], a["bio"],
            ])
    return output.getvalue()


def render_export_page(simulation_data: List[Dict], all_agents: Dict[str, List[Dict]]):
    """渲染报告导出页面"""
    st.markdown("## 📥 报告导出中心")
    st.markdown("*将分析结果导出为 HTML 报告或 CSV 数据文件*")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ---- HTML 报告导出 ----
    st.markdown("---")
    st.markdown("### 📄 HTML 分析报告")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        html_a = _build_single_report_html("A", all_agents["A"], simulation_data[0], simulation_data)
        st.download_button(
            label="📥 导出 Path A 报告",
            data=html_a,
            file_name=f"Tangshan_PathA_Report_{timestamp}.html",
            mime="text/html",
            use_container_width=True,
        )

    with col2:
        html_b = _build_single_report_html("B", all_agents["B"], simulation_data[1], simulation_data)
        st.download_button(
            label="📥 导出 Path B 报告",
            data=html_b,
            file_name=f"Tangshan_PathB_Report_{timestamp}.html",
            mime="text/html",
            use_container_width=True,
        )

    with col3:
        html_c = _build_single_report_html("C", all_agents["C"], simulation_data[2], simulation_data)
        st.download_button(
            label="📥 导出 Path C 报告",
            data=html_c,
            file_name=f"Tangshan_PathC_Report_{timestamp}.html",
            mime="text/html",
            use_container_width=True,
        )

    with col4:
        html_comp = _build_comparison_html(simulation_data, all_agents)
        st.download_button(
            label="📥 导出综合对比报告",
            data=html_comp,
            file_name=f"Tangshan_Comparison_Report_{timestamp}.html",
            mime="text/html",
            use_container_width=True,
        )

    # ---- CSV 数据导出 ----
    st.markdown("---")
    st.markdown("### 📊 CSV 数据导出")

    col1, col2 = st.columns(2)

    with col1:
        csv_data = _build_csv_data(simulation_data)
        st.download_button(
            label="📥 导出仿真数据 (CSV)",
            data=csv_data,
            file_name=f"Tangshan_Simulation_Data_{timestamp}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col2:
        agents_csv = _build_agents_csv(all_agents)
        st.download_button(
            label="📥 导出 Agent 详情 (CSV)",
            data=agents_csv,
            file_name=f"Tangshan_Agent_Details_{timestamp}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # ---- 预览 ----
    st.markdown("---")
    st.markdown("### 👁️ 报告内容预览")

    preview_tab1, preview_tab2, preview_tab3 = st.tabs([
        "📋 综合对比报告", "📊 仿真数据表格", "👥 Agent 数据表格"
    ])

    with preview_tab1:
        st.markdown("综合对比报告包含：三路径概览卡片、核心维度对比表、仿真数据详情、综合结论")
        st.markdown("*点击上方「导出综合对比报告」按钮下载完整 HTML 文件*")

        # 显示对比表预览
        import pandas as pd
        comp_preview = pd.DataFrame([
            {"维度": "被害人表态", "Path A": "公开'不和解'", "Path B": "私下接受100万", "Path C": "发声被限流压制"},
            {"维度": "信息渠道", "Path A": "央媒全国传播", "Path B": "微信群朋友圈泄露", "Path C": "平台限流+删帖"},
            {"维度": "主导叙事框架", "Path A": "正义 vs 邪恶", "Path B": "有钱 vs 没钱", "Path C": "真相被掩盖"},
            {"维度": "信息触达率", "Path A": "> 90%", "Path B": "~40%（碎片化）", "Path C": "< 5%"},
            {"维度": "舆论极化度", "Path A": "低", "Path B": "高", "Path C": "极度碎片化"},
            {"维度": "谣言控制", "Path A": "有效遏制", "Path B": "广泛传播", "Path C": "完全失控"},
            {"维度": "司法信任度", "Path A": "高 ✅", "Path B": "极低 ❌", "Path C": "崩溃 ❌"},
        ])
        st.dataframe(comp_preview, use_container_width=True, hide_index=True)

    with preview_tab2:
        # 显示仿真数据预览
        rows = []
        for path_data in simulation_data:
            pid = path_data["id"]
            for tick_idx, tick in enumerate(path_data["history"]):
                rows.append({
                    "Path": f"Path {pid}",
                    "Path Label": PATH_LABELS[pid],
                    "Tick": tick_idx,
                    "🔥 愤怒/共情": tick["tl"],
                    "⚖️ 理性/法律": tick["tr"],
                    "🏛️ 官方/秩序": tick["bl"],
                    "❓ 质疑/批判": tick["br"],
                })
        st.dataframe(rows, use_container_width=True, hide_index=True)

    with preview_tab3:
        # 显示 Agent 数据预览
        agent_rows = []
        for path_id, agents in all_agents.items():
            for a in agents[:10]:  # 每路径只显示前 10 个
                agent_rows.append({
                    "Path": path_id,
                    "名称": a["name"],
                    "类型": a["type_label"],
                    "象限": a["quadrant_label"],
                    "影响力": a["influence"],
                    "立场": a["stance"],
                })
        st.dataframe(agent_rows, use_container_width=True, hide_index=True)
        st.caption("预览仅显示每路径前 10 个 Agent，完整数据请下载 CSV")

    st.markdown("---")
    st.caption("💡 提示：HTML 报告可在浏览器中打开并直接打印为 PDF；CSV 数据可在 Excel / Python / R 中进一步分析")
    st.caption(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


# ---------- Agent 详情面板 ----------
def show_agent_detail(agent: Dict, path_id: str):
    """显示 Agent 详细信息卡片"""
    quad_color = QUADRANT_COLORS.get(agent["quadrant"], "#64748b")

    st.markdown(f"""
    <div class="detail-card" style="border-top: 3px solid {quad_color};">
        <h3>{agent['type_icon']} {agent['name']}</h3>
        <span class="type-badge" style="background:{quad_color}22;color:{quad_color};border:1px solid {quad_color}44;">
            {agent['quadrant_label']}
        </span>
        <span class="type-badge" style="background:#64748b22;color:#94a3b8;border:1px solid #64748b44;">
            {agent['type_label']}
        </span>
        <br><br>
        <p><strong>📌 核心立场：</strong>{agent['stance']}</p>
        <p><strong>📝 简介：</strong>{agent['bio']}</p>
        <p><strong>📡 影响力指数：</strong>{agent['influence']}/100</p>
        <p><strong>📍 象限位置：</strong>({agent['x']:.1f}, {agent['y']:.1f})</p>
        <p><strong>🔗 关联数：</strong>{len(agent.get('connections', []))} 条</p>
    </div>
    """, unsafe_allow_html=True)

    # 显示关联列表
    if agent.get("connections"):
        with st.expander("🔗 查看关联详情", expanded=False):
            for conn in agent["connections"]:
                st.write(f"- {conn['type']} → `{conn['target']}` (强度: {conn['weight']})")


# ---------- 文字报告 ----------
def render_path_report(path_id: str, agents: List[Dict]):
    """渲染单条路径的文字分析报告"""
    # 统计象限分布
    quad_counts = {"tl": 0, "tr": 0, "bl": 0, "br": 0}
    type_counts = {}
    total_influence = 0
    for a in agents:
        quad_counts[a["quadrant"]] += 1
        type_counts[a["type_label"]] = type_counts.get(a["type_label"], 0) + 1
        total_influence += a["influence"]

    dominant_quad = max(quad_counts, key=quad_counts.get)
    avg_influence = total_influence / len(agents) if agents else 0

    # 根据路径生成不同的分析文本
    if path_id == "A":
        assessment = "正面"
        assessment_color = "highlight-green"
        narrative = f"""
        <h4>📊 数据总览</h4>
        <p>在 <span class="highlight highlight-blue">Path A（公开表态·有效传播）</span> 路径中，
        被害人的公开表态通过央媒渠道实现全国性有效传播。仿真结果显示，共有 <strong>{len(agents)}</strong> 个
        舆论 Agent 参与互动，平均影响力指数为 <strong>{avg_influence:.1f}</strong>。</p>

        <h4>🗺️ 象限分布分析</h4>
        <p>官方/秩序象限（{QUADRANT_ICONS['bl']}）有 <strong>{quad_counts['bl']}</strong> 个 Agent，
        占据相对优势。理性/法律象限（{QUADRANT_ICONS['tr']}）有 <strong>{quad_counts['tr']}</strong> 个 Agent，
        表明信息有效传播促进了理性讨论。</p>
        <p>质疑/批判象限（{QUADRANT_ICONS['br']}）仅 <strong>{quad_counts['br']}</strong> 个 Agent，
        远低于其他路径——<span class="highlight highlight-green">说明公开透明有效遏制了谣言传播</span>。</p>

        <h4>🔗 网络结构特征</h4>
        <p>Agent 关系网络呈现 <strong>中心化结构</strong>：央媒和官方机构处于网络核心位置，
        信息从中心向外围高效扩散。连接密度较高，信息孤岛较少。</p>

        <h4>📈 舆论演变趋势</h4>
        <p>随着时间推移，Agent 从愤怒/共情象限逐步向理性/法律象限迁移，体现了
        <span class="highlight highlight-green">有效传播对情绪疏导的正面作用</span>。
        官方框架（正义vs邪恶）成功主导了舆论叙事。</p>

        <h4>⚖️ 司法信任评估</h4>
        <p>公众对司法系统的信任度维持在 <span class="highlight highlight-green">高水平</span>。
        被害人"不和解"的坚定表态树立了榜样效应，强化了公众对法治的信心。</p>
        """

        key_findings = [
            ("✅", "公开表态有效传递，信息触达率 > 90%"),
            ("✅", "谣言被有效遏制，舆论高度统一"),
            ("✅", "司法信任维持在较高水平"),
            ("⚠️", "需持续关注受害人权益保障的长期性"),
        ]

    elif path_id == "B":
        assessment = "负面"
        assessment_color = "highlight-yellow"
        narrative = f"""
        <h4>📊 数据总览</h4>
        <p>在 <span class="highlight highlight-yellow">Path B（私下和解·保持沉默）</span> 路径中，
        被害人私下接受赔偿并保持沉默，但和解信息通过非正式渠道泄露。共有 <strong>{len(agents)}</strong> 个
        Agent 参与舆论场，平均影响力指数为 <strong>{avg_influence:.1f}</strong>。</p>

        <h4>🗺️ 象限分布分析</h4>
        <p>质疑/批判象限（{QUADRANT_ICONS['br']}）急剧膨胀至 <strong>{quad_counts['br']}</strong> 个 Agent，
        而官方/秩序象限（{QUADRANT_ICONS['bl']}）萎缩至仅 <strong>{quad_counts['bl']}</strong> 个。
        <span class="highlight highlight-yellow">信息碎片化导致舆论场严重撕裂</span>。</p>
        <p>愤怒象限（{QUADRANT_ICONS['tl']}）仍有 <strong>{quad_counts['tl']}</strong> 个 Agent，
        但愤怒不再统一指向施暴者——相当一部分转向了制度和被害人本身。</p>

        <h4>🔗 网络结构特征</h4>
        <p>关系网络呈现 <strong>部落化/碎片化</strong> 特征：多个信息孤岛各自形成封闭小圈子，
        跨圈信息流通严重受阻。'有钱就能摆平'的叙事在非正式渠道中被反复强化。</p>

        <h4>📈 舆论演变趋势</h4>
        <p>沉默制造的信息真空被谣言填充。阶层对抗框架（有钱vs没钱）成为主导叙事，
        <span class="highlight highlight-yellow">司法信任度出现断崖式下跌</span>。</p>

        <h4>⚖️ 司法信任评估</h4>
        <p>公众对司法系统的信任度降至 <span class="highlight highlight-yellow">极低水平</span>。
        即使最终判决结果与 Path A 相同，公众普遍认为'判24年只是表面文章'。</p>
        """

        key_findings = [
            ("❌", "私下和解严重损害司法公信力"),
            ("❌", "沉默制造信息真空，谣言泛滥"),
            ("❌", "阶层撕裂加剧，'有钱vs没钱'主导舆论"),
            ("⚠️", "即使判决相同，公众信任度显著低于Path A"),
        ]

    else:  # path C
        assessment = "严重"
        assessment_color = "highlight-red"
        narrative = f"""
        <h4>📊 数据总览</h4>
        <p>在 <span class="highlight highlight-red">Path C（表态传播失败·信息黑洞）</span> 路径中，
        被害人的发声被平台限流和删帖压制，信息无法有效传播。共有 <strong>{len(agents)}</strong> 个
        Agent，但信息获取极度碎片化，平均影响力指数为 <strong>{avg_influence:.1f}</strong>。</p>

        <h4>🗺️ 象限分布分析</h4>
        <p>质疑/批判象限（{QUADRANT_ICONS['br']}）以 <strong>{quad_counts['br']}</strong> 个 Agent
        占据 <span class="highlight highlight-red">绝对多数</span>。
        官方/秩序象限（{QUADRANT_ICONS['bl']}）仅剩 <strong>{quad_counts['bl']}</strong> 个 Agent，
        几乎完全失势。</p>
        <p>信息黑洞导致阴谋论泛滥——'被害人被灭口''更大保护伞'等极端猜测占据主流。</p>

        <h4>🔗 网络结构特征</h4>
        <p>关系网络呈现 <span class="highlight highlight-red">极度碎片化</span> 状态：
        多种互相矛盾的叙事在各自封闭的小圈子内循环强化。官方信息渠道完全丧失公信力。</p>

        <h4>📈 舆论演变趋势</h4>
        <p>这是 <span class="highlight highlight-red">三条路径中最危险的演变轨迹</span>：
        公众对整个信息生态和司法系统的信任同时崩塌。即使事后恢复信息流通，
        已造成的信任损伤几乎不可逆。</p>

        <h4>⚖️ 司法信任评估</h4>
        <p>公众对司法系统的信任度已 <span class="highlight highlight-red">全面崩溃</span>。
        信息压制不但未能'维稳'，反而制造了更深层的合法性危机。</p>
        """

        key_findings = [
            ("❌", "信息压制导致全面信任崩塌——最危险的路径"),
            ("❌", "阴谋论填补信息真空，辟谣完全失效"),
            ("❌", "公众对信息生态和司法系统双重不信任"),
            ("❌", "信任损伤几乎不可逆，国际舆论负面报道激增"),
        ]

    # 渲染报告
    st.markdown(f"""
    <div class="report-text">
        <h3 style="margin-top:0;">📋 Path {path_id}: {PATH_LABELS[path_id]} — 分析报告</h3>
        <p style="color:#94a3b8;">综合评估: <span class="highlight {assessment_color}">{assessment}</span></p>
        {narrative}
    </div>
    """, unsafe_allow_html=True)

    # 关键发现
    st.markdown("#### 🔑 关键发现")
    cols = st.columns(2)
    for i, (icon, finding) in enumerate(key_findings):
        with cols[i % 2]:
            st.markdown(f"{icon} {finding}")

    # 导出按钮
    st.markdown("---")
    st.markdown("#### 📥 导出本路径报告")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path_data_for_export = None
    sim_data = load_simulation_data()
    for d in sim_data:
        if d["id"] == path_id:
            path_data_for_export = d
            break
    if path_data_for_export:
        html_report = _build_single_report_html(path_id, agents, path_data_for_export, sim_data)
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                label=f"📄 导出 Path {path_id} 完整报告 (HTML)",
                data=html_report,
                file_name=f"Tangshan_Path{path_id}_Report_{timestamp}.html",
                mime="text/html",
                use_container_width=True,
            )
        with c2:
            csv_data = _build_csv_data(sim_data)
            st.download_button(
                label="📊 导出仿真数据 (CSV)",
                data=csv_data,
                file_name=f"Tangshan_Simulation_Data_{timestamp}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    return quad_counts, avg_influence


# ---------- 对比页面 ----------
def render_comparison(simulation_data: List[Dict], all_agents: Dict[str, List[Dict]]):
    """渲染三路径对比页面"""
    st.markdown("### 📊 三路径全景对比")

    # 关键指标对比卡片
    cols = st.columns(3)
    for i, (path_id, color) in enumerate(PATH_COLORS.items()):
        agents = all_agents.get(path_id, [])
        path_data = simulation_data[i]
        final_tick = path_data["history"][-1]
        first_tick = path_data["history"][0]

        quad_counts = {"tl": 0, "tr": 0, "bl": 0, "br": 0}
        for a in agents:
            quad_counts[a["quadrant"]] += 1

        with cols[i]:
            st.markdown(f"""
            <div class="detail-card path-card-{path_id.lower()}">
                <h4 style="color:{color};">Path {path_id}</h4>
                <p style="font-size:12px;color:#94a3b8;">{PATH_LABELS[path_id]}</p>
                <hr style="border-color:#2d3a4a;">
                <div class="metric-grid" style="grid-template-columns:repeat(2,1fr);">
                    <div class="metric-item">
                        <div class="value" style="color:{QUADRANT_COLORS['bl']};">{final_tick['bl']}</div>
                        <div class="label">官方/秩序</div>
                    </div>
                    <div class="metric-item">
                        <div class="value" style="color:{QUADRANT_COLORS['br']};">{final_tick['br']}</div>
                        <div class="label">质疑/批判</div>
                    </div>
                    <div class="metric-item">
                        <div class="value" style="color:{QUADRANT_COLORS['tl']};">{final_tick['tl']}</div>
                        <div class="label">愤怒/共情</div>
                    </div>
                    <div class="metric-item">
                        <div class="value" style="color:{QUADRANT_COLORS['tr']};">{final_tick['tr']}</div>
                        <div class="label">理性/法律</div>
                    </div>
                </div>
                <p style="font-size:11px;color:#64748b;">
                    官区变化: {first_tick['bl']}→{final_tick['bl']} ({'+' if final_tick['bl']>=first_tick['bl'] else ''}{final_tick['bl']-first_tick['bl']})<br>
                    疑区变化: {first_tick['br']}→{final_tick['br']} ({'+' if final_tick['br']>=first_tick['br'] else ''}{final_tick['br']-first_tick['br']})
                </p>
            </div>
            """, unsafe_allow_html=True)

    # 象限演变对比图
    st.markdown("---")
    st.markdown("### 📈 象限分布演变（三路径对比）")
    timeline_chart = render_quadrant_timeline(simulation_data)
    st.altair_chart(timeline_chart, use_container_width=True)

    # 核心维度对比表
    st.markdown("---")
    st.markdown("### 📋 核心维度对比表")

    comp_data = [
        {"维度": "被害人表态", "Path A": "公开'不和解'", "Path B": "私下接受100万", "Path C": "发声被限流压制"},
        {"维度": "信息渠道", "Path A": "央媒全国传播", "Path B": "微信群朋友圈泄露", "Path C": "平台限流+删帖"},
        {"维度": "主导叙事框架", "Path A": "正义 vs 邪恶", "Path B": "有钱 vs 没钱", "Path C": "真相被掩盖"},
        {"维度": "信息触达率", "Path A": "> 90%", "Path B": "~40%（碎片化）", "Path C": "< 5%"},
        {"维度": "舆论极化度", "Path A": "低", "Path B": "高", "Path C": "极度碎片化"},
        {"维度": "谣言控制", "Path A": "有效遏制", "Path B": "广泛传播", "Path C": "完全失控"},
        {"维度": "司法信任度", "Path A": "高 ✅", "Path B": "极低 ❌", "Path C": "崩溃 ❌"},
        {"维度": "国际舆论影响", "Path A": "正面", "Path B": "负面", "Path C": "严重负面"},
        {"维度": "社会稳定影响", "Path A": "巩固", "Path B": "撕裂", "Path C": "深层危机"},
    ]

    st.dataframe(
        comp_data,
        use_container_width=True,
        column_config={
            "维度": st.column_config.TextColumn("维度", width="medium"),
            "Path A": st.column_config.TextColumn("Path A: 有效传播", width="large"),
            "Path B": st.column_config.TextColumn("Path B: 私下和解", width="large"),
            "Path C": st.column_config.TextColumn("Path C: 信息黑洞", width="large"),
        },
        hide_index=True,
    )

    # 结论
    st.markdown("---")
    st.markdown("### 🎯 综合结论")
    st.markdown("""
    <div class="report-text">
        <p>三条路径的仿真对比清晰地揭示了一个核心规律：</p>
        <p style="font-size:16px;text-align:center;padding:16px;background:#1a2332;border-radius:8px;">
            <strong>信息透明度与舆论稳定性呈<span class="highlight highlight-green">正相关</span></strong><br>
            <span style="font-size:13px;color:#94a3b8;">
            公开传播 → 舆论理性化 → 司法信任巩固<br>
            信息压制 → 谣言泛滥 → 信任全面崩塌
            </span>
        </p>
        <p><strong>Path A</strong> 表明：<span class="highlight highlight-green">公开透明不会削弱政府权威，反而通过疏导公众情绪来巩固法治信任。</span></p>
        <p><strong>Path B</strong> 表明：<span class="highlight highlight-yellow">私下和解虽然能暂时平息个案，但信息泄露后造成的信任损害远大于短期收益。</span></p>
        <p><strong>Path C</strong> 表明：<span class="highlight highlight-red">信息压制是最危险的策略——制造的信息黑洞会被阴谋论完全填充，造成几乎不可逆的系统性信任崩塌。</span></p>
    </div>
    """, unsafe_allow_html=True)

    # 导出按钮
    st.markdown("---")
    st.markdown("### 📥 导出报告")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    c1, c2 = st.columns(2)
    with c1:
        html_comp = _build_comparison_html(simulation_data, all_agents)
        st.download_button(
            label="📄 导出综合对比报告 (HTML)",
            data=html_comp,
            file_name=f"Tangshan_Comparison_Report_{timestamp}.html",
            mime="text/html",
            use_container_width=True,
        )
    with c2:
        csv_data = _build_csv_data(simulation_data)
        st.download_button(
            label="📊 导出仿真数据 (CSV)",
            data=csv_data,
            file_name=f"Tangshan_Simulation_Data_{timestamp}.csv",
            mime="text/csv",
            use_container_width=True,
        )


# ============================================================
# 主应用
# ============================================================
def main():
    inject_css()

    # 加载数据
    simulation_data = load_simulation_data()
    if not simulation_data:
        st.error("❌ 未找到 comparison_data.json，请先运行 run_three_paths.py 生成数据。")
        st.stop()

    all_agents = generate_agents()

    # ---- 侧边栏 ----
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center;padding:10px 0;">
            <h2>📊 唐山打人案</h2>
            <p style="color:#94a3b8;font-size:13px;">三路径舆论对比 · 交互式仪表盘</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

        # 页面选择
        page = st.radio(
            "📍 导航",
            ["🏠 总览仪表盘", "🔵 Path A · 有效传播", "🟡 Path B · 私下和解",
             "🔴 Path C · 信息黑洞", "📊 三路径对比", "📥 报告导出"],
            label_visibility="collapsed",
        )

        st.markdown("---")
        st.markdown("### 🔍 图例")
        for quad_key, label in QUADRANT_LABELS.items():
            color = QUADRANT_COLORS[quad_key]
            st.markdown(
                f'<span style="display:inline-block;width:12px;height:12px;'
                f'background:{color};border-radius:50%;margin-right:8px;"></span>'
                f'{QUADRANT_ICONS[quad_key]} {label}',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("### 📐 Agent 类型")
        for tkey, tinfo in AGENT_TYPES.items():
            st.markdown(
                f'<span style="color:{tinfo["color"]};">{tinfo["icon"]}</span> '
                f'{tinfo["label"]} <span style="color:#64748b;font-size:11px;">(size:{tinfo["base_size"]})</span>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.caption("仿真框架: ZJU Agent-Kernel | 可视化: Streamlit + agraph")
        st.caption(f"Agent 总数: 每路径 ~100 | Tick 数: 5 | LLM: DeepSeek-Chat")

    # ---- 主内容区 ----
    if page == "🏠 总览仪表盘":
        render_overview(simulation_data, all_agents)
    elif page.startswith("🔵"):
        render_single_path("A", all_agents, simulation_data)
    elif page.startswith("🟡"):
        render_single_path("B", all_agents, simulation_data)
    elif page.startswith("🔴"):
        render_single_path("C", all_agents, simulation_data)
    elif page == "📊 三路径对比":
        render_comparison(simulation_data, all_agents)
    elif page == "📥 报告导出":
        render_export_page(simulation_data, all_agents)


def render_overview(simulation_data: List[Dict], all_agents: Dict[str, List[Dict]]):
    """总览仪表盘"""
    st.markdown("## 🏠 总览仪表盘")

    # 顶部关键指标
    cols = st.columns(4)
    for i, (path_id, color) in enumerate(PATH_COLORS.items()):
        path_data = simulation_data[i]
        final = path_data["history"][-1]
        first = path_data["history"][0]
        br_change = final["br"] - first["br"]

        with cols[i]:
            direction = "↑" if br_change > 0 else "↓"
            st.metric(
                label=f"Path {path_id}: 质疑区变化",
                value=f"{final['br']} 人",
                delta=f"{direction}{abs(br_change)}",
                delta_color="inverse",
            )

    # 象限演变总览
    st.markdown("---")
    st.markdown("### 📈 三路径象限演变")
    timeline_chart = render_quadrant_timeline(simulation_data)
    st.altair_chart(timeline_chart, use_container_width=True)

    # 三条路径的关系图概览 (只显示 Path A 作为示例)
    st.markdown("---")
    st.markdown("### 🕸️ 人物关系网络 (Path A 示例)")

    col_graph, col_detail = st.columns([3, 2])

    with col_graph:
        agents_a = all_agents.get("A", [])
        # 只显示影响力前 40 的 agent 以免太密集
        top_agents = sorted(agents_a, key=lambda a: a["influence"], reverse=True)[:40]
        selected = render_relationship_graph(top_agents, "A", "overview")

    with col_detail:
        st.markdown("#### 🔍 节点详情")
        if selected:
            # agraph 返回选中的节点 ID (如果是单选) 或列表
            selected_id = selected if isinstance(selected, str) else (
                selected[0] if isinstance(selected, list) and len(selected) > 0 else None
            )
            if selected_id:
                # 查找 agent
                found = next((a for a in agents_a if a["id"] == selected_id), None)
                if found:
                    show_agent_detail(found, "A")
                else:
                    st.info(f"选中节点: {selected_id}")
            else:
                st.info("点击图中节点查看详细信息")
        else:
            st.info("👆 点击左侧关系图中的节点查看详细信息")

    # 快速对比摘要
    st.markdown("---")
    st.markdown("### ⚡ 快速对比摘要")
    cols = st.columns(3)
    for i, (path_id, color) in enumerate(PATH_COLORS.items()):
        path_data = simulation_data[i]
        final = path_data["history"][-1]
        with cols[i]:
            st.markdown(f"""
            <div class="detail-card path-card-{path_id.lower()}">
                <h4 style="color:{color};">Path {path_id}</h4>
                <p style="font-size:12px;color:#94a3b8;">{PATH_LABELS[path_id]}</p>
                <p style="font-size:11px;">{PATH_DESCRIPTIONS[path_id]}</p>
                <hr style="border-color:#2d3a4a;">
                <p>🔥 愤怒: {final['tl']} | ⚖️ 理性: {final['tr']}</p>
                <p>🏛️ 官方: {final['bl']} | ❓ 质疑: {final['br']}</p>
            </div>
            """, unsafe_allow_html=True)


def render_single_path(path_id: str, all_agents: Dict[str, List[Dict]],
                       simulation_data: List[Dict]):
    """渲染单条路径的完整分析页面"""
    color = PATH_COLORS[path_id]
    path_label = PATH_LABELS[path_id]
    agents = all_agents.get(path_id, [])
    path_data = next((d for d in simulation_data if d["id"] == path_id), None)

    st.markdown(f"## Path {path_id}: {path_label}")
    st.markdown(f'<p style="color:{color};">{PATH_DESCRIPTIONS[path_id]}</p>',
                unsafe_allow_html=True)

    # ---- Tab 切换 ----
    tab1, tab2, tab3, tab4 = st.tabs([
        "🕸️ 人物关系图", "📊 象限散点图", "📋 文字报告", "📈 演变趋势"
    ])

    # ---- Tab 1: 人物关系图 ----
    with tab1:
        st.markdown("### 🕸️ 流光人物关系图")
        st.markdown("*拖拽、缩放、点击节点查看详情*")

        # 过滤选项
        col1, col2, col3 = st.columns(3)
        with col1:
            show_types = st.multiselect(
                "显示类型",
                options=[t["label"] for t in AGENT_TYPES.values()],
                default=[t["label"] for t in AGENT_TYPES.values()],
                key=f"types_{path_id}",
            )
        with col2:
            min_influence = st.slider("最低影响力", 0, 100, 0, 5, key=f"inf_{path_id}")
        with col3:
            highlight_quad = st.selectbox(
                "高亮象限",
                options=["全部"] + list(QUADRANT_LABELS.values()),
                key=f"hl_{path_id}",
            )

        # 筛选 agents
        filtered = [
            a for a in agents
            if a["type_label"] in show_types and a["influence"] >= min_influence
        ]
        if highlight_quad != "全部":
            filtered = [a for a in filtered if a["quadrant_label"] == highlight_quad]

        st.caption(f"显示 {len(filtered)}/{len(agents)} 个 Agent")

        col_graph, col_detail = st.columns([3, 2])

        with col_graph:
            # 如果太多，只取 top 50
            display_agents = sorted(filtered, key=lambda a: a["influence"], reverse=True)[:50]
            selected = render_relationship_graph(display_agents, path_id, f"single_{path_id}")

        with col_detail:
            st.markdown("#### 🔍 节点详情")
            if selected:
                selected_id = selected if isinstance(selected, str) else (
                    selected[0] if isinstance(selected, list) and len(selected) > 0 else None
                )
                if selected_id:
                    found = next((a for a in agents if a["id"] == selected_id), None)
                    if found:
                        show_agent_detail(found, path_id)
                    else:
                        st.info(f"选中节点: {selected_id}")
                else:
                    st.info("点击图中节点查看详细信息")
            else:
                st.info("👆 点击左侧关系图中的节点查看详细信息")

    # ---- Tab 2: 象限散点图 ----
    with tab2:
        st.markdown("### 📊 Agent 象限分布图")
        st.markdown("*每个点代表一个 Agent，位置反映其舆论立场*")

        # 象限统计
        quad_counts = {"tl": 0, "tr": 0, "bl": 0, "br": 0}
        for a in agents:
            quad_counts[a["quadrant"]] += 1

        cols = st.columns(4)
        for i, (quad_key, label) in enumerate(QUADRANT_LABELS.items()):
            with cols[i]:
                st.metric(
                    label=f"{QUADRANT_ICONS[quad_key]} {label}",
                    value=f"{quad_counts[quad_key]} 人",
                    delta=f"{quad_counts[quad_key]/len(agents)*100:.0f}%",
                )

        scatter_chart = render_scatter_chart(agents)
        st.altair_chart(scatter_chart, use_container_width=True)

        # Agent 列表
        with st.expander("📋 查看所有 Agent 列表", expanded=False):
            agent_df_data = [
                {
                    "名称": a["name"],
                    "类型": a["type_label"],
                    "象限": a["quadrant_label"],
                    "影响力": a["influence"],
                    "立场": a["stance"],
                }
                for a in sorted(agents, key=lambda a: a["influence"], reverse=True)
            ]
            st.dataframe(agent_df_data, use_container_width=True, hide_index=True)

    # ---- Tab 3: 文字报告 ----
    with tab3:
        st.markdown("### 📋 路径分析报告")
        render_path_report(path_id, agents)

        # 网络统计
        st.markdown("---")
        st.markdown("#### 🌐 网络统计")
        total_connections = sum(len(a.get("connections", [])) for a in agents)
        avg_connections = total_connections / len(agents) if agents else 0
        max_influence_agent = max(agents, key=lambda a: a["influence"])

        cols = st.columns(4)
        with cols[0]:
            st.metric("总 Agent 数", len(agents))
        with cols[1]:
            st.metric("总连接数", total_connections)
        with cols[2]:
            st.metric("平均连接数", f"{avg_connections:.1f}")
        with cols[3]:
            st.metric("最大影响力", f"{max_influence_agent['influence']}",
                      delta=max_influence_agent["name"])

    # ---- Tab 4: 演变趋势 ----
    with tab4:
        st.markdown("### 📈 象限分布演变")

        if path_data:
            # 单路径时间线
            import altair as alt
            import pandas as pd

            rows = []
            for tick_idx, tick in enumerate(path_data["history"]):
                for quad_key, quad_label in QUADRANT_LABELS.items():
                    rows.append({
                        "Tick": tick_idx,
                        "象限": quad_label,
                        "人数": tick[quad_key],
                    })
            df = pd.DataFrame(rows)

            color_scale = alt.Scale(
                domain=list(QUADRANT_LABELS.values()),
                range=[QUADRANT_COLORS["tl"], QUADRANT_COLORS["tr"],
                       QUADRANT_COLORS["bl"], QUADRANT_COLORS["br"]],
            )

            line_chart = alt.Chart(df).mark_line(point=True, strokeWidth=3).encode(
                x=alt.X("Tick:O", title="Tick"),
                y=alt.Y("人数:Q", title="Agent 数量"),
                color=alt.Color("象限:N", scale=color_scale,
                                legend=alt.Legend(orient="bottom")),
            ).properties(height=350).configure(
                background="#0f172a",
                view={"stroke": "#1e293b"},
            ).configure_axis(
                gridColor="#1e293b",
                tickColor="#475569",
                labelColor="#64748b",
                domainColor="#475569",
                titleColor="#94a3b8",
            ).configure_legend(
                labelColor="#94a3b8",
                titleColor="#94a3b8",
            )

            st.altair_chart(line_chart, use_container_width=True)

            # 堆叠面积图
            area_chart = alt.Chart(df).mark_area(opacity=0.6).encode(
                x=alt.X("Tick:O", title="Tick"),
                y=alt.Y("人数:Q", title="Agent 数量"),
                color=alt.Color("象限:N", scale=color_scale,
                                legend=alt.Legend(orient="bottom")),
            ).properties(height=300).configure(
                background="#0f172a",
                view={"stroke": "#1e293b"},
            ).configure_axis(
                gridColor="#1e293b",
                tickColor="#475569",
                labelColor="#64748b",
                domainColor="#475569",
                titleColor="#94a3b8",
            ).configure_legend(
                labelColor="#94a3b8",
                titleColor="#94a3b8",
            )

            st.markdown("#### 堆叠面积图")
            st.altair_chart(area_chart, use_container_width=True)

        # Agent 类型分布
        st.markdown("---")
        st.markdown("#### 📐 Agent 类型分布")

        type_counts = {}
        for a in agents:
            type_counts[a["type_label"]] = type_counts.get(a["type_label"], 0) + 1

        type_df = pd.DataFrame([
            {"类型": k, "数量": v} for k, v in type_counts.items()
        ])

        bar_chart = alt.Chart(type_df).mark_bar(cornerRadius=4).encode(
            x=alt.X("数量:Q", title="数量"),
            y=alt.Y("类型:N", title=None, sort="-x"),
            color=alt.Color("类型:N", legend=None),
        ).properties(height=200).configure(
            background="#0f172a",
            view={"stroke": "#1e293b"},
        ).configure_axis(
            gridColor="#1e293b",
            labelColor="#94a3b8",
            titleColor="#94a3b8",
        )

        st.altair_chart(bar_chart, use_container_width=True)


# ============================================================
if __name__ == "__main__":
    main()
