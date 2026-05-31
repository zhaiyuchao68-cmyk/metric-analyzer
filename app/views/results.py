"""页面3：分析结果"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd

from metric_analyzer.engine import AnalysisEngine
from metric_analyzer.interpreters.nl_generator import NLGenerator
from metric_analyzer.components.charts import waterfall_chart, contribution_bar, composition_pie, dual_factor_grouped_bar, trend_line
from metric_analyzer.components.tables import result_table
from metric_analyzer.components.exporters import export_excel, export_pdf
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

    # 趋势分析（多期数据）
    if config.time_col:
        df = config.data
        periods = df[config.time_col].unique()
        if len(periods) > 2:
            st.subheader("趋势分析")

            # 计算各期指标值
            num_col = getattr(config, 'numerator_col', None)
            den_col = getattr(config, 'denominator_col', None)
            val_col = getattr(config, 'value_col', None)

            dim_col = config.dimensions[0] if config.dimensions else None

            if num_col and den_col:
                # 比率指标
                trend_df = df.groupby([config.time_col, dim_col]).agg({
                    num_col: "sum", den_col: "sum"
                }).reset_index()
                trend_df["指标值"] = trend_df[num_col] / trend_df[den_col]
                trend_col = "指标值"
            elif val_col:
                # 绝对量指标
                trend_df = df.groupby([config.time_col, dim_col])[val_col].sum().reset_index()
                trend_col = val_col
            else:
                trend_df = None
                trend_col = None

            if trend_df is not None and trend_col:
                fig = trend_line(trend_df, config.time_col, trend_col, dim_col=dim_col, top_n=5)
                st.plotly_chart(fig, use_container_width=True)

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

    # 导出功能
    st.subheader("导出报告")
    col_export1, col_export2 = st.columns(2)

    with col_export1:
        if st.button("导出 Excel 报告", use_container_width=True):
            original_data = st.session_state.get("data", pd.DataFrame())
            excel_bytes = export_excel(result, config, original_data, summary)
            st.download_button(
                label="下载 Excel 文件",
                data=excel_bytes,
                file_name=f"{config.name}_分析报告.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    with col_export2:
        if st.button("导出 PDF 报告", use_container_width=True):
            pdf_bytes = export_pdf(result, config, summary, top_n)
            st.download_button(
                label="下载 PDF 文件",
                data=pdf_bytes,
                file_name=f"{config.name}_分析报告.pdf",
                mime="application/pdf",
            )

    # 重新分析
    if st.button("重新分析", use_container_width=True):
        st.session_state["analysis_done"] = False
        st.rerun()
