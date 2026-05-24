"""指标注册表：管理预设和自定义指标"""

from pathlib import Path
from typing import Optional

import yaml

from metric_analyzer.models import DecompositionMethod, MetricType
from metric_analyzer.presets.call_center import CALL_CENTER_PRESETS


class MetricRegistry:
    """指标注册表"""

    def __init__(self):
        self._presets: dict[str, dict] = dict(CALL_CENTER_PRESETS)

    def get_preset(self, name: str) -> Optional[dict]:
        """获取预设指标配置"""
        return self._presets.get(name)

    def list_presets(self) -> list[str]:
        """列出所有预设指标名"""
        return list(self._presets.keys())

    def load_yaml(self, yaml_path: str) -> list[str]:
        """从YAML文件加载自定义指标，返回加载的指标名列表"""
        path = Path(yaml_path)
        if not path.exists():
            return []

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        loaded = []
        if data:
            for name, cfg in data.items():
                method_map = {
                    "addition": DecompositionMethod.ADDITION,
                    "subtraction": DecompositionMethod.SUBTRACTION,
                    "multiplication": DecompositionMethod.MULTIPLICATION,
                    "dual_factor": DecompositionMethod.DUAL_FACTOR,
                }
                type_map = {
                    "absolute": MetricType.ABSOLUTE,
                    "derived_diff": MetricType.DERIVED_DIFF,
                    "flow_chain": MetricType.FLOW_CHAIN,
                    "ratio": MetricType.RATIO,
                    "efficiency": MetricType.EFFICIENCY,
                }

                method_str = cfg.get("method", "addition")
                preset = {
                    "method": method_map.get(method_str, DecompositionMethod.ADDITION),
                    "metric_type": type_map.get(method_str, MetricType.ABSOLUTE),
                    "dimensions": cfg.get("dimensions", []),
                    "numerator": cfg.get("numerator", ""),
                    "denominator": cfg.get("denominator", ""),
                    "components": cfg.get("components", []),
                }
                self._presets[name] = preset
                loaded.append(name)

        return loaded

    def save_example_yaml(self, path: str):
        """生成示例YAML文件"""
        example = {
            "自定义指标名": {
                "method": "dual_factor",
                "dimensions": ["维度A", "维度B"],
                "numerator": "分子列名",
                "denominator": "分母列名",
            }
        }
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(example, f, allow_unicode=True, default_flow_style=False)
