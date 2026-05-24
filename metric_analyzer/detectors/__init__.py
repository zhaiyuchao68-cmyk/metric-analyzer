"""检测器模块"""

from metric_analyzer.detectors.registry import MetricRegistry
from metric_analyzer.detectors.rule_based import MetricDetector

__all__ = ["MetricDetector", "MetricRegistry"]
