"""乘法拆解器（含LMDI方法）"""

import math

import numpy as np
import pandas as pd

from metric_analyzer.decomposers.base import BaseDecomposer
from metric_analyzer.models import (
    AnalysisMode,
    DecompositionMethod,
    DecompositionResult,
    FactorContribution,
    MetricConfig,
)


def lmdi_weight(base_val: float, comp_val: float) -> float:
    """计算LMDI对数平均权重

    当两个值相等时返回算术平均，避免除零。
    """
    if base_val == comp_val:
        return base_val
    if base_val <= 0 or comp_val <= 0:
        return (base_val + comp_val) / 2
    return (comp_val - base_val) / (math.log(comp_val) - math.log(base_val))


class MultiplicationDecomposer(BaseDecomposer):
    """流程链路指标的乘法拆解，使用LMDI方法"""

    def can_handle(self, config: MetricConfig) -> bool:
        return config.method == DecompositionMethod.MULTIPLICATION

    def decompose(self, config: MetricConfig) -> DecompositionResult:
        if config.time_col and config.base_period and config.compare_period:
            return self._dynamic_decompose(config)
        return self._static_decompose(config)

    def _static_decompose(self, config: MetricConfig) -> DecompositionResult:
        """静态：展示各因子值及整体值"""
        df = config.data
        components = config.components

        last_row = df.iloc[-1]
        factor_values = {c: float(last_row[c]) for c in components}
        overall = 1.0
        for c in components:
            overall *= factor_values[c]

        contributions = []
        for rank, comp in enumerate(components, 1):
            contributions.append(FactorContribution(
                name=comp,
                value_change=factor_values[comp],
                contribution_rate=factor_values[comp] * 100,
                rank=rank,
            ))

        detail = pd.DataFrame({
            "因子": components,
            "值": [factor_values[c] for c in components],
        })

        return DecompositionResult(
            method=DecompositionMethod.MULTIPLICATION,
            mode=AnalysisMode.STATIC,
            overall_change=overall,
            overall_change_rate=0.0,
            contributions=contributions,
            is_mece=True,
            detail_table=detail,
        )

    def _dynamic_decompose(self, config: MetricConfig) -> DecompositionResult:
        """动态：LMDI拆解"""
        df = config.data
        components = config.components
        time_col = config.time_col

        base_row = df[df[time_col] == config.base_period].iloc[0]
        comp_row = df[df[time_col] == config.compare_period].iloc[0]

        base_factors = {c: float(base_row[c]) for c in components}
        comp_factors = {c: float(comp_row[c]) for c in components}

        base_overall = 1.0
        comp_overall = 1.0
        for c in components:
            base_overall *= base_factors[c]
            comp_overall *= comp_factors[c]

        overall_change = comp_overall - base_overall
        overall_change_rate = ((comp_overall - base_overall) / base_overall * 100) if base_overall != 0 else 0

        # LMDI additive decomposition: each factor's contribution
        # is L(base_overall, comp_overall) * ln(comp_f / base_f)
        # where L is the logarithmic mean of the overall values
        overall_weight = lmdi_weight(base_overall, comp_overall) if base_overall > 0 and comp_overall > 0 else 0

        contributions = []
        for comp in components:
            base_f = base_factors[comp]
            comp_f = comp_factors[comp]
            if base_f > 0 and comp_f > 0 and overall_weight != 0:
                contrib = overall_weight * math.log(comp_f / base_f)
            else:
                contrib = comp_f - base_f
            contributions.append(FactorContribution(
                name=comp,
                value_change=contrib,
                contribution_rate=0,
                rank=0,
            ))

        for c in contributions:
            if overall_change != 0:
                c.contribution_rate = (c.value_change / overall_change * 100)

        contributions.sort(key=lambda c: abs(c.value_change), reverse=True)
        for i, c in enumerate(contributions, 1):
            c.rank = i

        detail = pd.DataFrame({
            "因子": [c.name for c in contributions],
            f"{config.base_period}值": [base_factors[c.name] for c in contributions],
            f"{config.compare_period}值": [comp_factors[c.name] for c in contributions],
            "变化": [comp_factors[c.name] - base_factors[c.name] for c in contributions],
            "LMDI贡献": [c.value_change for c in contributions],
            "贡献率(%)": [c.contribution_rate for c in contributions],
        })

        return DecompositionResult(
            method=DecompositionMethod.MULTIPLICATION,
            mode=AnalysisMode.DYNAMIC,
            overall_change=overall_change,
            overall_change_rate=overall_change_rate,
            contributions=contributions,
            is_mece=True,
            detail_table=detail,
            chart_data={
                "labels": [c.name for c in contributions],
                "changes": [c.value_change for c in contributions],
                "rates": [c.contribution_rate for c in contributions],
            },
        )
