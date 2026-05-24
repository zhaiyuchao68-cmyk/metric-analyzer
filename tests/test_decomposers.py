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
from metric_analyzer.decomposers.subtraction import SubtractionDecomposer


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


class TestSubtractionDecomposer:
    def setup_method(self):
        self.decomposer = SubtractionDecomposer()

    def test_can_handle(self):
        config = MetricConfig(
            name="利润",
            metric_type=MetricType.DERIVED_DIFF,
            method=DecompositionMethod.SUBTRACTION,
            data=pd.DataFrame(),
            dimensions=["产品线"],
            components=["收入", "成本", "费用"],
        )
        assert self.decomposer.can_handle(config) is True

    def test_static_decompose(self):
        data = pd.DataFrame({
            "产品线": ["A", "B"],
            "收入": [1000, 800],
            "成本": [600, 500],
            "费用": [200, 200],
        })
        config = MetricConfig(
            name="利润",
            metric_type=MetricType.DERIVED_DIFF,
            method=DecompositionMethod.SUBTRACTION,
            data=data,
            dimensions=["产品线"],
            components=["收入", "成本", "费用"],
        )
        result = self.decomposer.decompose(config)
        assert result.method == DecompositionMethod.SUBTRACTION
        assert result.is_mece is True
        assert result.overall_change == pytest.approx(300.0, abs=0.01)

    def test_dynamic_decompose(self):
        data = pd.DataFrame({
            "季度": ["2024Q1", "2024Q2"],
            "收入": [1000, 1100],
            "成本": [600, 650],
            "费用": [200, 250],
        })
        config = MetricConfig(
            name="利润",
            metric_type=MetricType.DERIVED_DIFF,
            method=DecompositionMethod.SUBTRACTION,
            data=data,
            dimensions=[],
            components=["收入", "成本", "费用"],
            time_col="季度",
            base_period="2024Q1",
            compare_period="2024Q2",
        )
        result = self.decomposer.decompose(config)
        assert result.overall_change == pytest.approx(0.0, abs=0.01)


from metric_analyzer.decomposers.multiplication import MultiplicationDecomposer


class TestMultiplicationDecomposer:
    def setup_method(self):
        self.decomposer = MultiplicationDecomposer()

    def test_can_handle(self):
        config = MetricConfig(
            name="成交用户",
            metric_type=MetricType.FLOW_CHAIN,
            method=DecompositionMethod.MULTIPLICATION,
            data=pd.DataFrame(),
            dimensions=[],
            components=["新增用户量", "激活率", "留存率", "购买率"],
        )
        assert self.decomposer.can_handle(config) is True

    def test_lmdi_mece(self):
        """验证LMDI拆解结果MECE（各因子贡献求和=整体变化率）"""
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
        result = self.decomposer.decompose(config)
        assert result.method == DecompositionMethod.MULTIPLICATION
        assert result.is_mece is True
        total_rate = sum(c.contribution_rate for c in result.contributions)
        assert total_rate == pytest.approx(100.0, abs=1.0)

    def test_lmdi_equal_factors(self):
        """因子值相同时不报错"""
        data = pd.DataFrame({
            "季度": ["2024Q1", "2024Q2"],
            "A": [100, 100],
            "B": [200, 220],
        })
        config = MetricConfig(
            name="测试",
            metric_type=MetricType.FLOW_CHAIN,
            method=DecompositionMethod.MULTIPLICATION,
            data=data,
            dimensions=[],
            components=["A", "B"],
            time_col="季度",
            base_period="2024Q1",
            compare_period="2024Q2",
        )
        result = self.decomposer.decompose(config)
        a_contrib = next(c for c in result.contributions if c.name == "A")
        assert a_contrib.value_change == pytest.approx(0.0, abs=0.01)


from metric_analyzer.decomposers.division import DivisionDecomposer
from metric_analyzer.decomposers.dual_factor import DualFactorDecomposer


class TestDualFactorDecomposer:
    def setup_method(self):
        self.decomposer = DualFactorDecomposer()

    def test_can_handle(self):
        config = MetricConfig(
            name="客户满意度",
            metric_type=MetricType.RATIO,
            method=DecompositionMethod.DUAL_FACTOR,
            data=pd.DataFrame(),
            dimensions=["语言线"],
            numerator_col="好评量",
            denominator_col="参评量",
        )
        assert self.decomposer.can_handle(config) is True

    def test_mece(self):
        """双因素拆解结果MECE"""
        data = pd.DataFrame({
            "季度": ["2024Q1", "2024Q1", "2024Q1",
                     "2024Q2", "2024Q2", "2024Q2"],
            "语言线": ["中文", "英语", "西班牙语",
                      "中文", "英语", "西班牙语"],
            "好评量": [8500, 3200, 900, 9200, 2800, 750],
            "参评量": [10000, 5000, 1000, 10500, 5200, 1050],
        })
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
        result = self.decomposer.decompose(config)
        assert result.method == DecompositionMethod.DUAL_FACTOR
        assert result.is_mece is True
        total_contrib = sum(c.value_change for c in result.contributions)
        assert total_contrib == pytest.approx(result.overall_change, abs=0.01)

    def test_new_dimension(self):
        """新增维度处理"""
        data = pd.DataFrame({
            "季度": ["2024Q1", "2024Q1", "2024Q2", "2024Q2", "2024Q2"],
            "语言线": ["中文", "英语", "中文", "英语", "日语"],
            "好评量": [8500, 3200, 9200, 2800, 400],
            "参评量": [10000, 5000, 10500, 5200, 450],
        })
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
        result = self.decomposer.decompose(config)
        assert any(c.name == "日语" for c in result.contributions)


class TestDivisionDecomposer:
    def setup_method(self):
        self.decomposer = DivisionDecomposer()

    def test_can_handle(self):
        config = MetricConfig(
            name="单位人员效率",
            metric_type=MetricType.EFFICIENCY,
            method=DecompositionMethod.DIVISION,
            data=pd.DataFrame(),
            dimensions=["团队"],
            numerator_col="实际服务量",
            denominator_col="上班时长",
        )
        assert self.decomposer.can_handle(config) is True

    def test_static_decompose(self):
        data = pd.DataFrame({
            "团队": ["A组"],
            "实际服务量": [5000],
            "直服排班时间": [400],
            "排班时间": [450],
            "在线时长": [480],
            "上班时长": [500],
        })
        config = MetricConfig(
            name="单位人员效率",
            metric_type=MetricType.EFFICIENCY,
            method=DecompositionMethod.DIVISION,
            data=data,
            dimensions=["团队"],
            numerator_col="实际服务量",
            denominator_col="上班时长",
        )
        result = self.decomposer.decompose(config)
        assert result.method == DecompositionMethod.DIVISION
        assert result.overall_change == pytest.approx(10.0, abs=0.01)
