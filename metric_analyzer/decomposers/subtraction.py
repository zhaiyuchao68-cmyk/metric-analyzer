"""减法拆解器"""

import pandas as pd

from metric_analyzer.decomposers.base import BaseDecomposer
from metric_analyzer.models import (
    AnalysisMode,
    DecompositionMethod,
    DecompositionResult,
    FactorContribution,
    MetricConfig,
)


class SubtractionDecomposer(BaseDecomposer):
    """衍生差值指标的拆解（如利润=收入-成本-费用）"""

    def can_handle(self, config: MetricConfig) -> bool:
        return config.method == DecompositionMethod.SUBTRACTION

    def decompose(self, config: MetricConfig) -> DecompositionResult:
        if config.time_col and config.base_period and config.compare_period:
            return self._dynamic_decompose(config)
        return self._static_decompose(config)

    def _static_decompose(self, config: MetricConfig) -> DecompositionResult:
        """静态：计算各组成项"""
        df = config.data
        components = config.components
        dim = config.dimensions[0] if config.dimensions else None

        if dim:
            grouped = df.groupby(dim)[components].sum()
            total_by_component = grouped.sum()
        else:
            total_by_component = df[components].sum()

        result_val = float(total_by_component[components[0]])
        for comp in components[1:]:
            result_val -= float(total_by_component[comp])

        contributions = []
        for rank, comp in enumerate(components, 1):
            val = float(total_by_component[comp])
            contributions.append(FactorContribution(
                name=comp,
                value_change=val,
                contribution_rate=val,
                rank=rank,
            ))

        detail = pd.DataFrame({
            "组成项": components,
            "数值": [float(total_by_component[c]) for c in components],
        })

        return DecompositionResult(
            method=DecompositionMethod.SUBTRACTION,
            mode=AnalysisMode.STATIC,
            overall_change=result_val,
            overall_change_rate=0.0,
            contributions=contributions,
            is_mece=True,
            detail_table=detail,
        )

    def _dynamic_decompose(self, config: MetricConfig) -> DecompositionResult:
        """动态：各组成项变化直接即贡献"""
        df = config.data
        components = config.components
        time_col = config.time_col

        base_row = df[df[time_col] == config.base_period]
        comp_row = df[df[time_col] == config.compare_period]

        base_vals = {c: float(base_row[c].sum()) for c in components}
        comp_vals = {c: float(comp_row[c].sum()) for c in components}

        base_result = base_vals[components[0]] - sum(base_vals[c] for c in components[1:])
        comp_result = comp_vals[components[0]] - sum(comp_vals[c] for c in components[1:])
        overall_change = comp_result - base_result

        contributions = []
        for comp in components:
            change = comp_vals[comp] - base_vals[comp]
            if comp == components[0]:
                effect = change
            else:
                effect = -change
            rate = (effect / overall_change * 100) if overall_change != 0 else 0
            contributions.append(FactorContribution(
                name=comp,
                value_change=effect,
                contribution_rate=rate,
                rank=0,
            ))

        contributions.sort(key=lambda c: abs(c.value_change), reverse=True)
        for i, c in enumerate(contributions, 1):
            c.rank = i

        overall_rate = ((comp_result - base_result) / abs(base_result) * 100) if base_result != 0 else 0

        detail = pd.DataFrame({
            "组成项": [c.name for c in contributions],
            f"{config.base_period}值": [base_vals[c.name] for c in contributions],
            f"{config.compare_period}值": [comp_vals[c.name] for c in contributions],
            "变化量": [c.value_change for c in contributions],
            "贡献率(%)": [c.contribution_rate for c in contributions],
        })

        return DecompositionResult(
            method=DecompositionMethod.SUBTRACTION,
            mode=AnalysisMode.DYNAMIC,
            overall_change=overall_change,
            overall_change_rate=overall_rate,
            contributions=contributions,
            is_mece=True,
            detail_table=detail,
        )
