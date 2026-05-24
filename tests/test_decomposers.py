"""拆解器测试"""

import pandas as pd
import pytest

from metric_analyzer.models import (
    AnalysisMode,
    DecompositionMethod,
    MetricConfig,
    MetricType,
)
from metric_analyzer.decomposers.addition import AdditionDecomposer


class TestAdditionDecomposer:
    def setup_method(self):
        self.decomposer = AdditionDecomposer()

    def test_can_handle_addition(self):
        config = MetricConfig(
            name="通话量",
            metric_type=MetricType.ABSOLUTE,
            method=DecompositionMethod.ADDITION,
            data=pd.DataFrame(),
            dimensions=["技能组"],
        )
        assert self.decomposer.can_handle(config) is True

    def test_cannot_handle_other(self):
        config = MetricConfig(
            name="满意度",
            metric_type=MetricType.RATIO,
            method=DecompositionMethod.DUAL_FACTOR,
            data=pd.DataFrame(),
            dimensions=["语言线"],
        )
        assert self.decomposer.can_handle(config) is False

    def test_static_decompose(self):
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
        result = self.decomposer.decompose(config)
        assert result.method == DecompositionMethod.ADDITION
        assert result.mode == AnalysisMode.STATIC
        assert result.is_mece is True
        assert len(result.contributions) == 3
        a_contribution = next(c for c in result.contributions if c.name == "A组")
        assert a_contribution.contribution_rate == pytest.approx(50.0, abs=0.1)

    def test_dynamic_decompose(self):
        data = pd.DataFrame({
            "季度": ["2024Q1", "2024Q1", "2024Q1", "2024Q2", "2024Q2", "2024Q2"],
            "技能组": ["A组", "B组", "C组", "A组", "B组", "C组"],
            "通话量": [1000, 600, 400, 1200, 500, 300],
        })
        config = MetricConfig(
            name="通话量",
            metric_type=MetricType.ABSOLUTE,
            method=DecompositionMethod.ADDITION,
            data=data,
            dimensions=["技能组"],
            value_col="通话量",
            time_col="季度",
            base_period="2024Q1",
            compare_period="2024Q2",
        )
        result = self.decomposer.decompose(config)
        assert result.mode == AnalysisMode.DYNAMIC
        assert result.overall_change == pytest.approx(0.0, abs=0.01)
