"""Plotly 可视化图表组件"""

import plotly.graph_objects as go

from metric_analyzer.models import AnalysisMode, DecompositionResult


def waterfall_chart(result: DecompositionResult, top_n: int = 5) -> go.Figure:
    """瀑布图：展示各因子贡献的正负累积"""
    contributions = result.contributions[:top_n]

    labels = ["起始"] + [c.name for c in contributions] + ["合计"]
    values = [0] + [c.value_change for c in contributions] + [0]

    measure = ["absolute"] + ["relative"] * len(contributions) + ["total"]

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=measure,
        x=labels,
        y=values,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#2ca02c"}},
        decreasing={"marker": {"color": "#d62728"}},
        totals={"marker": {"color": "#1f77b4"}},
    ))

    fig.update_layout(
        title="因子贡献瀑布图",
        showlegend=False,
        height=400,
    )

    return fig


def contribution_bar(result: DecompositionResult, top_n: int = 5) -> go.Figure:
    """贡献率排名柱状图"""
    contributions = result.contributions[:top_n]

    names = [c.name for c in contributions]
    values = [c.value_change for c in contributions]
    colors = ["#2ca02c" if v >= 0 else "#d62728" for v in values]

    fig = go.Figure(go.Bar(
        x=names,
        y=values,
        marker_color=colors,
        text=[f"{c.contribution_rate:.1f}%" for c in contributions],
        textposition="outside",
    ))

    fig.update_layout(
        title="因子贡献排名",
        yaxis_title="贡献值",
        height=400,
    )

    return fig


def composition_pie(result: DecompositionResult) -> go.Figure:
    """构成占比饼图（静态拆解用）"""
    names = [c.name for c in result.contributions]
    values = [abs(c.value_change) for c in result.contributions]

    fig = go.Figure(go.Pie(
        labels=names,
        values=values,
        hole=0.3,
    ))

    fig.update_layout(
        title="构成占比",
        height=400,
    )

    return fig
