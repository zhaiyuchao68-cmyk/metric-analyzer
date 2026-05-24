"""页面1：上传数据"""

import streamlit as st
import pandas as pd


def render():
    st.header("上传数据")

    uploaded_file = st.file_uploader(
        "拖拽或点击上传 Excel/CSV 文件",
        type=["csv", "xlsx", "xls"],
        help="支持 CSV 和 Excel 格式",
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            st.session_state["data"] = df
            st.session_state["filename"] = uploaded_file.name

            st.success(f"文件 '{uploaded_file.name}' 上传成功，共 {len(df)} 行 {len(df.columns)} 列")

            st.subheader("数据预览")
            st.dataframe(df.head(20), use_container_width=True)

            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            st.session_state["numeric_cols"] = numeric_cols

            st.subheader("识别到的数值列")
            st.write("、".join(numeric_cols) if numeric_cols else "未发现数值列")

            dim_cols = [c for c in df.columns if c not in numeric_cols]
            st.session_state["dim_cols"] = dim_cols

            if dim_cols:
                st.subheader("识别到的维度列")
                st.write("、".join(dim_cols))

        except Exception as e:
            st.error(f"文件读取失败：{e}")
    else:
        st.info("请上传数据文件以开始分析")

        st.subheader("数据格式示例")
        example = pd.DataFrame({
            "季度": ["2024Q1", "2024Q1", "2024Q2", "2024Q2"],
            "语言线": ["中文", "英语", "中文", "英语"],
            "好评量": [8500, 3200, 9200, 2800],
            "参评量": [10000, 5000, 10500, 5200],
        })
        st.dataframe(example, use_container_width=True)
