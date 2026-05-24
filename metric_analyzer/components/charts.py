"""Plotly 可视化图表组件"""

import plotly.graph_objects as go

from metric_analyzer.models import AnalysisMode, DecompositionMethod, DecompositionResult

_ABSOLUTE_METHODS = {DecompositionMethod.ADDITION, DecompositionMethod.SUBTRACTION}


def dual_factor_grouped_bar(result: DecompositionResult, top_n: int = 5) -> go.Figure:
    """分组柱状图：指标波动 vs 占比波动（双因素拆解用）"""
    contributions = result.contributions[:top_n]

    names = [c.name for c in contributions]
    rate_effects = [(c.rate_effect or 0) * 100 for c in contributions]
    share_effects = [(c.share_effect or 0) * 100 for c in contributions]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="指标波动",
        x=names,
        y=rate_effects,
        marker_color="#1f77b4",
        text=[f"{v:+.2f}%" for v in rate_effects],
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name="占比波动",
        x=names,
        y=share_effects,
        marker_color="#ff7f0e",
        text=[f"{v:+.2f}%" for v in share_effects],
        textposition="outside",
    ))

    fig.update_layout(
        title="指标波动 vs 占比波动",
        yaxis_title="贡献（%）",
        barmode="group",
        height=400,
    )

    return fig


def waterfall_chart(result: DecompositionResult, top_n: int = 5) -> go.Figure:
    """瀑布图：展示各因子贡献的正负累积"""
    contributions = result.contributions[:top_n]
    is_abs = result.method in _ABSOLUTE_METHODS
    is_mul = result.method == DecompositionMethod.MULTIPLICATION

    labels = ["起始"] + [c.name for c in contributions] + ["合计"]
    values = [0] + [c.value_change for c in contributions] + [0]

    measure = ["absolute"] + ["relative"] * len(contributions) + ["total"]

    # 柱上文字
    if is_abs or is_mul:
        text_labels = [""] + [f"{v:+,.0f}" for v in values[1:-1]] + [f"{sum(c.value_change for c in contributions):+,.0f}"]
    else:
        text_labels = [""] + [f"{v*100:+.2f}%" for v in values[1:-1]] + [""]

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=measure,
        x=labels,
        y=values,
        text=text_labels,
        textposition="outside",
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#2ca02c"}},
        decreasing={"marker": {"color": "#d62728"}},
        totals={"marker": {"color": "#1f77b4"}},
    ))

    if is_abs:
        title, yaxis = "因子贡献瀑布图", "数量"
    elif is_mul:
        title, yaxis = "LMDI贡献值", "通数"
    else:
        title, yaxis = "因子贡献瀑布图", "贡献（%）"

    fig.update_layout(
        title=title,
        showlegend=False,
        yaxis_title=yaxis,
        height=400,
    )

    return fig


def contribution_bar(result: DecompositionResult, top_n: int = 5) -> go.Figure:
    """贡献值排名柱状图"""
    contributions = result.contributions[:top_n]
    is_abs = result.method in _ABSOLUTE_METHODS
    is_mul = result.method == DecompositionMethod.MULTIPLICATION

    names = [c.name for c in contributions]

    if is_abs:
        values = [c.value_change for c in contributions]
        text_labels = [f"{v:+,.0f}" for v in values]
        title, yaxis = "因子贡献排名", "变化量"
    elif is_mul:
        # 乘法：贡献率 = LMDI值 / 上期总量 × 100%
        base_overall = result.overall_change * 100 / result.overall_change_rate if result.overall_change_rate != 0 else 1
        values = [c.value_change / base_overall * 100 for c in contributions]
        text_labels = [f"{v:+.2f}%" for v in values]
        title, yaxis = "各因素幅度变化", "幅度（%）"
    else:
        values = [c.value_change * 100 for c in contributions]
        text_labels = [f"{v:+.2f}%" for v in values]
        title, yaxis = "因子贡献排名", "贡献（%）"

    colors = ["#2ca02c" if v >= 0 else "#d62728" for v in values]

    fig = go.Figure(go.Bar(
        x=names,
        y=values,
        marker_color=colors,
        text=text_labels,
        textposition="outside",
    ))

    fig.update_layout(
        title=title,
        yaxis_title=yaxis,
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
