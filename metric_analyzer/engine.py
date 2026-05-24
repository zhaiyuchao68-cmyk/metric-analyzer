"""分析引擎：调度检测和拆解"""

import pandas as pd

from metric_analyzer.decomposers import (
    AdditionDecomposer,
    DualFactorDecomposer,
    MultiplicationDecomposer,
    SubtractionDecomposer,
)
from metric_analyzer.detectors import MetricDetector, MetricRegistry
from metric_analyzer.models import DecompositionMethod, DecompositionResult, MetricConfig


class AnalysisEngine:
    """核心分析引擎"""

    def __init__(self):
        self._decomposers = [
            AdditionDecomposer(),
            SubtractionDecomposer(),
            MultiplicationDecomposer(),
            DualFactorDecomposer(),
        ]
        self._detector = MetricDetector()
        self._registry = MetricRegistry()

    def detect_method(self, df: pd.DataFrame, name: str) -> list[dict]:
        """检测指标可用的拆解方法"""
        # 预设检查
        preset = self._registry.get_preset(name)
        if preset:
            from metric_analyzer.detectors.rule_based import METHOD_DESCRIPTIONS
            return [{
                "metric_type": preset["metric_type"],
                "method": preset["method"],
                "confidence": 0.95,
                "reason": f"命中呼叫中心预设指标'{name}'",
                "description": METHOD_DESCRIPTIONS.get(preset["method"], ""),
                "preset": preset,
            }]

        # 规则检测
        return self._detector.detect(df, name)

    def analyze(self, config: MetricConfig) -> DecompositionResult:
        """执行拆解分析"""
        for decomposer in self._decomposers:
            if decomposer.can_handle(config):
                return decomposer.decompose(config)
        raise ValueError(f"没有找到能处理 {config.method} 的拆解器")

    def list_presets(self) -> list[str]:
        """列出所有预设指标"""
        return self._registry.list_presets()

    def load_custom_metrics(self, yaml_path: str) -> list[str]:
        """加载自定义指标"""
        return self._registry.load_yaml(yaml_path)
