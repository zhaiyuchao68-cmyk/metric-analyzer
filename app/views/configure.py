"""页面2：配置拆解参数"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from metric_analyzer.engine import AnalysisEngine
from metric_analyzer.models import AnalysisMode, DecompositionMethod, MetricConfig, MetricType


METHOD_MAP = {
    "加法拆解": DecompositionMethod.ADDITION,
    "减法拆解": DecompositionMethod.SUBTRACTION,
    "乘法拆解": DecompositionMethod.MULTIPLICATION,
    "双因素拆解": DecompositionMethod.DUAL_FACTOR,
}


def render():
    st.header("配置拆解参数")

    if "data" not in st.session_state:
        st.warning("请先在「上传数据」页面上传数据文件")
        return

    df = st.session_state["data"]
    engine = AnalysisEngine()
    numeric_cols = st.session_state.get("numeric_cols", [])
    dim_cols = st.session_state.get("dim_cols", [])

    # 选择指标
    st.subheader("选择指标")
    metric_name = st.text_input(
        "指标名称",
        value=st.session_state.get("metric_name", ""),
        placeholder="例如：客户满意度、通话量、单位人员效率",
    )
    st.session_state["metric_name"] = metric_name

    if not metric_name:
        st.info("请输入指标名称")
        return

    # 自动检测
    detections = engine.detect_method(df, metric_name)

    st.subheader("系统推荐")
    for i, det in enumerate(detections[:3]):
        conf = det.get("confidence", 0)
        method = det["method"]
        reason = det.get("reason", "")
        desc = det.get("description", "")
        label = f"{'✅' if i == 0 else '○'} {method.value}（置信度 {conf:.0%}）"
        st.markdown(f"**{label}**")
        st.caption(f"原因：{reason}")
        if desc:
            st.caption(desc)

    # 用户选择方法
    st.subheader("确认拆解方法")
    method_options = list(METHOD_MAP.keys())
    default_idx = 0
    if detections:
        for i, m in enumerate(method_options):
            if METHOD_MAP[m] == detections[0]["method"]:
                default_idx = i
                break

    selected_method_name = st.selectbox("拆解方法", method_options, index=default_idx)
    selected_method = METHOD_MAP[selected_method_name]

    # 时间列选择：从维度列中选一个作为时间列，选"无"则静态分析
    st.subheader("拆解维度")
    available_dims = dim_cols + [c for c in numeric_cols if c not in dim_cols]

    time_col = None
    base_period = None
    compare_period = None
    is_dynamic = False

    time_col_sel = st.selectbox('时间列（选"无"则进行静态构成分析）', ["无"] + dim_cols)
    if time_col_sel != "无":
        time_col = time_col_sel
        periods = df[time_col].unique().tolist()
        col1, col2 = st.columns(2)
        with col1:
            base_period = st.selectbox("基期（上期）", periods, index=0)
        with col2:
            compare_period = st.selectbox("对比期（本期）", periods, index=min(1, len(periods) - 1))
        is_dynamic = True

    available_dims = [c for c in available_dims if c != time_col]
    selected_dims = st.multiselect(
        "选择拆解维度（可多选）",
        available_dims,
        default=[available_dims[0]] if available_dims else [],
    )

    # 多维度分析模式选择
    multi_dim_mode = "cross"
    if len(selected_dims) > 1:
        st.caption(f"已选择 {len(selected_dims)} 个维度：{' × '.join(selected_dims)}")
        multi_dim_mode = st.radio(
            "多维度分析模式",
            options=["cross", "hierarchy"],
            format_func=lambda x: "交叉分析（维度组合为分项）" if x == "cross" else "分层分析（按主维度逐层拆解）",
            index=0,
        )

    # 数值列配置
    st.subheader("数值列配置")
    if selected_method == DecompositionMethod.DUAL_FACTOR:
        col1, col2 = st.columns(2)
        with col1:
            numerator = st.selectbox("分子列", numeric_cols, index=0)
        with col2:
            denominator = st.selectbox("分母列", numeric_cols, index=min(1, len(numeric_cols) - 1))
    elif selected_method == DecompositionMethod.ADDITION:
        value_col = st.selectbox("数值列", numeric_cols)
    elif selected_method == DecompositionMethod.SUBTRACTION:
        components = st.multiselect("组成列（按 产出-投入-... 顺序）", numeric_cols)
    elif selected_method == DecompositionMethod.MULTIPLICATION:
        components = st.multiselect("因子列（按流程顺序）", numeric_cols)

    # 开始分析按钮
    if st.button("开始分析", type="primary", use_container_width=True):
        if not selected_dims:
            st.error("请至少选择一个拆解维度")
            return

        config = MetricConfig(
            name=metric_name,
            metric_type=detections[0].get("metric_type", MetricType.ABSOLUTE) if detections else MetricType.ABSOLUTE,
            method=selected_method,
            data=df,
            dimensions=selected_dims,
            time_col=time_col if is_dynamic else None,
            base_period=base_period if is_dynamic else None,
            compare_period=compare_period if is_dynamic else None,
            multi_dim_mode=multi_dim_mode,
        )

        if selected_method == DecompositionMethod.DUAL_FACTOR:
            config.numerator_col = numerator
            config.denominator_col = denominator
        elif selected_method == DecompositionMethod.ADDITION:
            config.value_col = value_col
        elif selected_method in (DecompositionMethod.SUBTRACTION, DecompositionMethod.MULTIPLICATION):
            config.components = components

        st.session_state["config"] = config
        st.session_state["analysis_done"] = False
        st.success("配置完成！请前往「查看结果」页面")
