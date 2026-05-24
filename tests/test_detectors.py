"""指标类型检测器测试"""

import pandas as pd

from metric_analyzer.detectors.rule_based import MetricDetector
from metric_analyzer.models import DecompositionMethod, MetricType


class TestMetricDetector:
    def setup_method(self):
        self.detector = MetricDetector()

    def test_ratio_keyword_detection(self):
        results = self.detector.detect(pd.DataFrame(), "客户满意度")
        types = [r["metric_type"] for r in results]
        assert MetricType.RATIO in types

    def test_efficiency_keyword_detection(self):
        results = self.detector.detect(pd.DataFrame(), "单位人员效率")
        types = [r["metric_type"] for r in results]
        assert MetricType.EFFICIENCY in types

    def test_absolute_keyword_detection(self):
        results = self.detector.detect(pd.DataFrame(), "通话量")
        types = [r["metric_type"] for r in results]
        assert MetricType.ABSOLUTE in types

    def test_unknown_returns_all(self):
        results = self.detector.detect(pd.DataFrame(), "未知指标XYZ")
        assert len(results) > 0

    def test_structure_ratio_detection(self):
        df = pd.DataFrame({"好评量": [100], "参评量": [200]})
        results = self.detector.detect(df, "满意度")
        methods = [r["method"] for r in results]
        assert DecompositionMethod.DUAL_FACTOR in methods
