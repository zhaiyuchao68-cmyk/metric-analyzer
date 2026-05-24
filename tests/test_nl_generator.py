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
        result = DecompositionResult(
            method=DecompositionMethod.DUAL_FACTOR,
            mode=AnalysisMode.DYNAMIC,
            overall_change=-0.018,
            overall_change_rate=-2.1,
            contributions=[
                FactorContribution("英语线", -0.012, 67.0, 1),
                FactorContribution("西班牙语线", -0.003, 18.0, 2),
                FactorContribution("中文线", 0.002, -10.0, 3),
            ],
            is_mece=True,
        )
        text = self.generator.generate(result, "客户满意度", top_n=3)
        assert "客户满意度" in text
        assert "英语线" in text
        assert "67" in text or "67.0" in text

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
