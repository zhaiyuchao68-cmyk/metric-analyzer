"""集成测试：端到端验证"""

import pandas as pd
import pytest

from metric_analyzer.engine import AnalysisEngine
from metric_analyzer.interpreters.nl_generator import NLGenerator
from metric_analyzer.models import DecompositionMethod, MetricConfig, MetricType, AnalysisMode


class TestIntegration:
    def setup_method(self):
        self.engine = AnalysisEngine()
        self.generator = NLGenerator()

    def test_csat_dual_factor_e2e(self):
        """端到端：客户满意度双因素拆解"""
        data = pd.DataFrame({
            "季度": ["2024Q1"] * 3 + ["2024Q2"] * 3,
            "语言线": ["中文", "英语", "西班牙语"] * 2,
            "好评量": [8500, 3200, 900, 9200, 2800, 750],
            "参评量": [10000, 5000, 1000, 10500, 5200, 1050],
        })

        detections = self.engine.detect_method(data, "客户满意度")
        assert detections[0]["method"] == DecompositionMethod.DUAL_FACTOR

        config = MetricConfig(
            name="客户满意度",
            metric_type=MetricType.RATIO,
            method=DecompositionMethod.DUAL_FACTOR,
            data=data,
            dimensions=["语言线"],
            numerator_col="好评量",
            denominator_col="参评量",
            time_col="季度",
            base_period="2024Q1",
            compare_period="2024Q2",
        )

        result = self.engine.analyze(config)
        assert result.is_mece is True
        assert len(result.contributions) == 3

        text = self.generator.generate(result, "客户满意度")
        assert "客户满意度" in text
        assert len(text) > 50

    def test_funnel_multiplication_e2e(self):
        """端到端：漏斗乘法拆解"""
        data = pd.DataFrame({
            "季度": ["2024Q1", "2024Q2"],
            "新增用户量": [10000, 8500],
            "激活率": [0.60, 0.55],
            "3日留存率": [0.40, 0.40],
            "购买率": [0.15, 0.13],
        })

        config = MetricConfig(
            name="成交用户",
            metric_type=MetricType.FLOW_CHAIN,
            method=DecompositionMethod.MULTIPLICATION,
            data=data,
            dimensions=[],
            components=["新增用户量", "激活率", "3日留存率", "购买率"],
            time_col="季度",
            base_period="2024Q1",
            compare_period="2024Q2",
        )

        result = self.engine.analyze(config)
        assert result.is_mece is True

        total_rate = sum(c.contribution_rate for c in result.contributions)
        assert total_rate == pytest.approx(100.0, abs=1.0)

    def test_addition_e2e(self):
        """端到端：通话量加法拆解"""
        data = pd.DataFrame({
            "技能组": ["A组", "B组", "C组"],
            "通话量": [1000, 600, 400],
        })

        config = MetricConfig(
            name="通话量",
            metric_type=MetricType.ABSOLUTE,
            method=DecompositionMethod.ADDITION,
            data=data,
            dimensions=["技能组"],
            value_col="通话量",
        )

        result = self.engine.analyze(config)
        assert result.mode == AnalysisMode.STATIC
        assert result.overall_change == pytest.approx(2000.0, abs=0.01)

        text = self.generator.generate(result, "通话量")
        assert "通话量" in text
