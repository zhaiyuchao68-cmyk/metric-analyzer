"""页面3：分析结果"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from metric_analyzer.engine import AnalysisEngine
from metric_analyzer.interpreters.nl_generator import NLGenerator
from metric_analyzer.components.charts import waterfall_chart, contribution_bar, composition_pie, dual_factor_grouped_bar
from metric_analyzer.components.tables import result_table
from metric_analyzer.models import AnalysisMode, DecompositionMethod


def render():
    st.header("分析结果")

    if "config" not in st.session_state:
        st.warning("请先在「配置拆解」页面完成配置")
        return

    config = st.session_state["config"]

    # 执行分析
    if not st.session_state.get("analysis_done", False):
        with st.spinner("正在分析..."):
            engine = AnalysisEngine()
            result = engine.analyze(config)
            st.session_state["result"] = result
            st.session_state["analysis_done"] = True

    result = st.session_state["result"]

    # Top N 控制
    top_n = st.slider("展示 Top N 因子", min_value=3, max_value=10, value=config.top_n)

    # 自然语言解读
    st.subheader("自然语言解读")
    generator = NLGenerator()
    summary = generator.generate(result, config.name, top_n=top_n)
    st.markdown(summary)

    # 可视化图表
    st.subheader("可视化图表")
    col1, col2 = st.columns(2)

    with col1:
        if result.mode == AnalysisMode.DYNAMIC:
            if result.method == DecompositionMethod.DUAL_FACTOR:
                fig = dual_factor_grouped_bar(result, top_n=top_n)
            else:
                fig = waterfall_chart(result, top_n=top_n)
        else:
            fig = composition_pie(result)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = contribution_bar(result, top_n=top_n)
        st.plotly_chart(fig, use_container_width=True)

    # 数据表格
    st.subheader("数据表格")
    table = result_table(result, top_n=top_n)
    st.dataframe(table, use_container_width=True)

    # 拆解结果信息
    st.caption(f"拆解方法：{result.method.value} | MECE：{'是' if result.is_mece else '否'}")

    # 重新分析
    if st.button("重新分析", use_container_width=True):
        st.session_state["analysis_done"] = False
        st.rerun()
