"""数据模型测试"""

import pandas as pd
import pytest

from metric_analyzer.models import (
    AnalysisMode,
    DecompositionMethod,
    DecompositionResult,
    FactorContribution,
    MetricConfig,
    MetricType,
)


class TestMetricConfig:
    def test_top_n_clamp_min(self):
        config = MetricConfig(
            name="测试指标",
            metric_type=MetricType.ABSOLUTE,
            method=DecompositionMethod.ADDITION,
            data=pd.DataFrame(),
            dimensions=["维度A"],
            top_n=1,
        )
        assert config.top_n == 3

    def test_top_n_clamp_max(self):
        config = MetricConfig(
            name="测试指标",
            metric_type=MetricType.ABSOLUTE,
            method=DecompositionMethod.ADDITION,
            data=pd.DataFrame(),
            dimensions=["维度A"],
            top_n=20,
        )
        assert config.top_n == 10

    def test_top_n_default(self):
        config = MetricConfig(
            name="测试指标",
            metric_type=MetricType.ABSOLUTE,
            method=DecompositionMethod.ADDITION,
            data=pd.DataFrame(),
            dimensions=["维度A"],
        )
        assert config.top_n == 5


class TestFactorContribution:
    def test_creation(self):
        fc = FactorContribution(
            name="维度A",
            value_change=-1.2,
            contribution_rate=67.0,
            rank=1,
        )
        assert fc.name == "维度A"
        assert fc.value_change == -1.2


class TestDecompositionResult:
    def test_creation(self):
        result = DecompositionResult(
            method=DecompositionMethod.ADDITION,
            mode=AnalysisMode.DYNAMIC,
            overall_change=-100.0,
            overall_change_rate=-10.0,
            contributions=[],
            is_mece=True,
        )
        assert result.is_mece is True
        assert result.summary == ""
