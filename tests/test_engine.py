"""分析引擎测试"""

import pandas as pd
import pytest

from metric_analyzer.engine import AnalysisEngine
from metric_analyzer.models import DecompositionMethod, MetricType


class TestAnalysisEngine:
    def setup_method(self):
        self.engine = AnalysisEngine()

    def test_detect_addition(self):
        data = pd.DataFrame({
            "技能组": ["A组", "B组", "C组"],
            "通话量": [1000, 600, 400],
        })
        detections = self.engine.detect_method(data, "通话量")
        assert len(detections) > 0
        assert detections[0]["method"] == DecompositionMethod.ADDITION

    def test_detect_ratio(self):
        data = pd.DataFrame({
            "季度": ["2024Q1", "2024Q1", "2024Q2", "2024Q2"],
            "语言线": ["中文", "英语", "中文", "英语"],
            "好评量": [8500, 3200, 9200, 2800],
            "参评量": [10000, 5000, 10500, 5200],
        })
        detections = self.engine.detect_method(data, "客户满意度")
        assert detections[0]["method"] == DecompositionMethod.DUAL_FACTOR

    def test_preset_override(self):
        data = pd.DataFrame()
        detections = self.engine.detect_method(data, "客户满意度")
        assert detections[0]["confidence"] >= 0.9
