"""页面4：预设指标管理"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import yaml

from metric_analyzer.detectors.registry import MetricRegistry


YAML_PATH = Path(__file__).parent.parent.parent / "custom_metrics.yaml"

METHOD_OPTIONS = {
    "加法拆解": "addition",
    "减法拆解": "subtraction",
    "乘法拆解": "multiplication",
    "双因素拆解": "dual_factor",
}


def render():
    st.header("预设指标管理")

    registry = MetricRegistry()
    registry.load_yaml(str(YAML_PATH)) if YAML_PATH.exists() else None

    # 查看现有预设
    st.subheader("现有预设指标")
    presets = registry.list_presets()
    col1, col2 = st.columns([2, 1])
    with col1:
        selected = st.selectbox("选择查看", presets)
    with col2:
        st.caption("")
        st.caption("")
        if selected and registry.get_preset(selected):
            preset = registry.get_preset(selected)
            st.json({
                "方法": preset.get("method", "").value if hasattr(preset.get("method"), "value") else str(preset.get("method")),
                "维度": preset.get("dimensions", []),
                "分子": preset.get("numerator", ""),
                "分母": preset.get("denominator", ""),
                "组成列": preset.get("components", []),
            })

    st.divider()

    # 添加新指标
    st.subheader("添加新指标")
    with st.form("add_metric"):
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("指标名称", placeholder="例如：退货率")
        with col2:
            new_method = st.selectbox("拆解方法", list(METHOD_OPTIONS.keys()), index=3)

        new_dims = st.text_input("拆解维度（逗号分隔）", placeholder="例如：品类,渠道")

        if new_method in ["双因素拆解"]:
            col1, col2 = st.columns(2)
            with col1:
                new_num = st.text_input("分子列名", placeholder="例如：退货量")
            with col2:
                new_den = st.text_input("分母列名", placeholder="例如：订单量")
        elif new_method in ["减法拆解"]:
            new_comps = st.text_input("组成列（逗号分隔，按产出-投入顺序）", placeholder="例如：收入,成本,费用")
        elif new_method in ["乘法拆解"]:
            new_comps = st.text_input("因子列（逗号分隔，按流程顺序）", placeholder="例如：流量,转化率,客单价")
        else:
            new_num, new_den, new_comps = "", "", ""

        if st.form_submit_button("添加指标", type="primary"):
            if not new_name:
                st.error("请输入指标名称")
            else:
                dims = [d.strip() for d in new_dims.split(",") if d.strip()]
                preset = {
                    "method": METHOD_OPTIONS[new_method],
                    "dimensions": dims,
                }
                if new_method in ["双因素拆解"]:
                    preset["numerator"] = new_num
                    preset["denominator"] = new_den
                elif new_method in ["减法拆解", "乘法拆解"]:
                    preset["components"] = [c.strip() for c in new_comps.split(",") if c.strip()]

                _save_preset(new_name, preset)
                st.success(f"已添加指标「{new_name}」")
                st.rerun()

    st.divider()

    # 编辑 YAML
    st.subheader("YAML 编辑")
    st.caption("直接编辑 YAML 文件，适合批量配置")

    if YAML_PATH.exists():
        current_yaml = YAML_PATH.read_text(encoding="utf-8")
    else:
        current_yaml = "# 在这里添加自定义指标\n\n"

    edited_yaml = st.text_area("YAML 内容", current_yaml, height=300)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("保存 YAML", type="primary"):
            YAML_PATH.write_text(edited_yaml, encoding="utf-8")
            st.success("已保存")
    with col2:
        st.download_button(
            "下载示例",
            data=_get_example_yaml(),
            file_name="custom_metrics_example.yaml",
            mime="text/yaml",
        )


def _save_preset(name: str, preset: dict):
    """保存单个预设到 YAML 文件"""
    if YAML_PATH.exists():
        data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8")) or {}
    else:
        data = {}

    data[name] = preset
    with open(YAML_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def _get_example_yaml() -> str:
    example = {
        "退货率": {
            "method": "dual_factor",
            "dimensions": ["品类", "渠道"],
            "numerator": "退货量",
            "denominator": "订单量",
        },
        "净利润": {
            "method": "subtraction",
            "dimensions": ["部门"],
            "components": ["收入", "成本", "费用"],
        },
    }
    return yaml.dump(example, allow_unicode=True, default_flow_style=False)
