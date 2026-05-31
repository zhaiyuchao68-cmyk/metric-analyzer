"""指标拆解分析工具 - 主入口"""

import sys
from pathlib import Path

import streamlit as st

# 将项目根目录加入 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.views import upload, configure, results, presets


def main():
    st.set_page_config(
        page_title="指标拆解分析工具",
        page_icon="📊",
        layout="wide",
    )

    st.title("📊 指标拆解分析工具")
    st.caption("上传数据 → 配置拆解 → 查看分析结果")

    page = st.sidebar.radio(
        "导航",
        ["上传数据", "配置拆解", "查看结果", "预设指标"],
        index=0,
    )

    if page == "上传数据":
        upload.render()
    elif page == "配置拆解":
        configure.render()
    elif page == "查看结果":
        results.render()
    elif page == "预设指标":
        presets.render()


if __name__ == "__main__":
    main()
