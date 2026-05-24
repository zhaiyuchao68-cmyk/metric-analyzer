"""自然语言解读测试"""

import pandas as pd
import pytest

from metric_analyzer.interpreters.nl_generator import NLGenerator
from metric_analyzer.models import (
    AnalysisMode,
    DecompositionMethod,
    DecompositionResult,
    FactorContribution,
)


class TestNLGenerator:
    def setup_method(self):
        self.generator = NLGenerator()

    def test_dual_factor_summary(self):
        # 使用自洽数据：好评量/参评量 → 好评率、占比
        # Q1: 中文 8500/10000, 英语 3250/5000, 西语 900/1000
        # Q2: 中文 9240/10500, 英语 2750/5000, 西语 875/1250
        detail = pd.DataFrame({
            "分项": ["英语线", "西班牙语线", "中文线"],
            "2024Q1指标值": [0.65, 0.90, 0.85],
            "2024Q2指标值": [0.55, 0.70, 0.88],
            "2024Q1占比": [0.3125, 0.0625, 0.625],
            "2024Q2占比": [5000/16750, 1250/16750, 10500/16750],
            "指标波动贡献": [-0.03125, -0.0125, 0.01875],
            "结构变化贡献": [0.00337, -0.00110, 0.00017],
            "总贡献": [-0.02788, -0.01360, 0.01892],
            "贡献率(%)": [123.57, 60.27, -83.83],
            "上期整体均值": [0.790625, 0.790625, 0.790625],
        })
        result = DecompositionResult(
            method=DecompositionMethod.DUAL_FACTOR,
            mode=AnalysisMode.DYNAMIC,
            overall_change=-0.0226,
            overall_change_rate=-2.85,
            contributions=[
                FactorContribution("英语线", -0.0279, 123.57, 1, rate_effect=-0.03125, share_effect=0.00337),
                FactorContribution("西班牙语线", -0.0136, 60.27, 2, rate_effect=-0.0125, share_effect=-0.00110),
                FactorContribution("中文线", 0.0189, -83.83, 3, rate_effect=0.01875, share_effect=0.00017),
            ],
            is_mece=True,
            detail_table=detail,
        )
        text = self.generator.generate(result, "客户满意度", top_n=3)
        assert "客户满意度" in text
        assert "英语线" in text
        assert "-3.13%" in text or "-2.79%" in text

    def test_addition_summary(self):
        result = DecompositionResult(
            method=DecompositionMethod.ADDITION,
            mode=AnalysisMode.DYNAMIC,
            overall_change=200,
            overall_change_rate=10.0,
            contributions=[
                FactorContribution("A组", 300, 150.0, 1),
                FactorContribution("B组", -100, -50.0, 2),
            ],
            is_mece=True,
        )
        text = self.generator.generate(result, "通话量", top_n=2)
        assert "通话量" in text
        assert "A组" in text

    def test_empty_contributions(self):
        result = DecompositionResult(
            method=DecompositionMethod.ADDITION,
            mode=AnalysisMode.STATIC,
            overall_change=1000,
            overall_change_rate=0.0,
            contributions=[],
            is_mece=True,
        )
        text = self.generator.generate(result, "通话量", top_n=5)
        assert len(text) > 0
