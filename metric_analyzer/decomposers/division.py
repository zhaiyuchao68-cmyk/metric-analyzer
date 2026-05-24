"""除法拆解器（乘一法拆分分母）"""

import math

import pandas as pd

from metric_analyzer.decomposers.base import BaseDecomposer
from metric_analyzer.decomposers.multiplication import lmdi_weight
from metric_analyzer.models import (
    AnalysisMode,
    DecompositionMethod,
    DecompositionResult,
    FactorContribution,
    MetricConfig,
)


class DivisionDecomposer(BaseDecomposer):
    """效率/比例指标的除法拆解"""

    def can_handle(self, config: MetricConfig) -> bool:
        return config.method == DecompositionMethod.DIVISION

    def decompose(self, config: MetricConfig) -> DecompositionResult:
        if config.time_col and config.base_period and config.compare_period:
            return self._dynamic_decompose(config)
        return self._static_decompose(config)

    def _get_factors(self, row, config: MetricConfig) -> dict[str, float]:
        """乘一法：将 服务量/上班时长 拆为多个因子的乘积"""
        numerator = float(row[config.numerator_col])
        denominator = float(row[config.denominator_col])

        if config.components:
            denom_cols = config.components
            factors = {}
            factors[f"{config.numerator_col}/{denom_cols[0]}"] = numerator / float(row[denom_cols[0]]) if float(row[denom_cols[0]]) != 0 else 0
            for i in range(len(denom_cols) - 1):
                v1 = float(row[denom_cols[i]])
                v2 = float(row[denom_cols[i + 1]])
                factors[f"{denom_cols[i]}/{denom_cols[i+1]}"] = v1 / v2 if v2 != 0 else 0
            return factors
        else:
            return {"整体效率": numerator / denominator if denominator != 0 else 0}

    def _static_decompose(self, config: MetricConfig) -> DecompositionResult:
        """静态：乘一法展示各因子"""
        df = config.data
        last_row = df.iloc[-1]
        factors = self._get_factors(last_row, config)

        overall = float(last_row[config.numerator_col]) / float(last_row[config.denominator_col]) \
            if float(last_row[config.denominator_col]) != 0 else 0

        contributions = []
        for rank, (name, val) in enumerate(factors.items(), 1):
            contributions.append(FactorContribution(
                name=name,
                value_change=val,
                contribution_rate=val * 100,
                rank=rank,
            ))

        detail = pd.DataFrame({
            "因子": list(factors.keys()),
            "值": list(factors.values()),
        })

        return DecompositionResult(
            method=DecompositionMethod.DIVISION,
            mode=AnalysisMode.STATIC,
            overall_change=overall,
            overall_change_rate=0.0,
            contributions=contributions,
            is_mece=True,
            detail_table=detail,
        )

    def _dynamic_decompose(self, config: MetricConfig) -> DecompositionResult:
        """动态：转为乘法后用LMDI"""
        df = config.data
        time_col = config.time_col

        base_row = df[df[time_col] == config.base_period].iloc[0]
        comp_row = df[df[time_col] == config.compare_period].iloc[0]

        base_factors = self._get_factors(base_row, config)
        comp_factors = self._get_factors(comp_row, config)

        base_overall = float(base_row[config.numerator_col]) / float(base_row[config.denominator_col]) \
            if float(base_row[config.denominator_col]) != 0 else 0
        comp_overall = float(comp_row[config.numerator_col]) / float(comp_row[config.denominator_col]) \
            if float(comp_row[config.denominator_col]) != 0 else 0

        overall_change = comp_overall - base_overall
        overall_change_rate = ((comp_overall - base_overall) / base_overall * 100) if base_overall != 0 else 0

        contributions = []
        for name in base_factors:
            base_f = base_factors[name]
            comp_f = comp_factors.get(name, 0)
            weight = lmdi_weight(base_f, comp_f)
            if base_overall > 0 and comp_overall > 0:
                contrib = weight * math.log(comp_overall / base_overall)
            else:
                contrib = 0
            contributions.append(FactorContribution(
                name=name,
                value_change=contrib,
                contribution_rate=(contrib / overall_change * 100) if overall_change != 0 else 0,
                rank=0,
            ))

        contributions.sort(key=lambda c: abs(c.value_change), reverse=True)
        for i, c in enumerate(contributions, 1):
            c.rank = i

        detail = pd.DataFrame({
            "因子": [c.name for c in contributions],
            f"{config.base_period}值": [base_factors[c.name] for c in contributions],
            f"{config.compare_period}值": [comp_factors.get(c.name, 0) for c in contributions],
            "LMDI贡献": [c.value_change for c in contributions],
            "贡献率(%)": [c.contribution_rate for c in contributions],
        })

        return DecompositionResult(
            method=DecompositionMethod.DIVISION,
            mode=AnalysisMode.DYNAMIC,
            overall_change=overall_change,
            overall_change_rate=overall_change_rate,
            contributions=contributions,
            is_mece=True,
            detail_table=detail,
        )
