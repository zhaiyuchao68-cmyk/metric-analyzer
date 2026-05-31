"""加法拆解器"""

import pandas as pd

from metric_analyzer.decomposers.base import BaseDecomposer
from metric_analyzer.models import (
    AnalysisMode,
    DecompositionMethod,
    DecompositionResult,
    FactorContribution,
    MetricConfig,
)


class AdditionDecomposer(BaseDecomposer):
    """绝对量指标的维度拆解"""

    def can_handle(self, config: MetricConfig) -> bool:
        return config.method == DecompositionMethod.ADDITION

    def decompose(self, config: MetricConfig) -> DecompositionResult:
        if config.time_col and config.base_period and config.compare_period:
            return self._dynamic_decompose(config)
        return self._static_decompose(config)

    def _static_decompose(self, config: MetricConfig) -> DecompositionResult:
        """静态拆解：各分项占比"""
        df = config.data.copy()
        dims = config.dimensions
        if len(dims) > 1 and config.multi_dim_mode == "cross":
            cross_dim = "×".join(dims)
            df[cross_dim] = df[dims].apply(lambda row: " - ".join(row.astype(str)), axis=1)
            dim = cross_dim
        else:
            dim = dims[0]
        val_col = config.value_col

        grouped = df.groupby(dim)[val_col].sum().sort_values(ascending=False)
        total = grouped.sum()

        contributions = []
        for rank, (name, value) in enumerate(grouped.items(), 1):
            rate = (value / total * 100) if total != 0 else 0
            contributions.append(FactorContribution(
                name=str(name),
                value_change=float(value),
                contribution_rate=float(rate),
                rank=rank,
            ))

        detail = pd.DataFrame({
            "因子": [c.name for c in contributions],
            "数值": [c.value_change for c in contributions],
            "占比(%)": [c.contribution_rate for c in contributions],
            "排名": [c.rank for c in contributions],
        })

        return DecompositionResult(
            method=DecompositionMethod.ADDITION,
            mode=AnalysisMode.STATIC,
            overall_change=float(total),
            overall_change_rate=0.0,
            contributions=contributions,
            is_mece=True,
            detail_table=detail,
            chart_data={"labels": [c.name for c in contributions],
                        "values": [c.value_change for c in contributions]},
        )

    def _dynamic_decompose(self, config: MetricConfig) -> DecompositionResult:
        """动态拆解：各分项变化贡献"""
        df = config.data.copy()
        dims = config.dimensions
        if len(dims) > 1 and config.multi_dim_mode == "cross":
            cross_dim = "×".join(dims)
            df[cross_dim] = df[dims].apply(lambda row: " - ".join(row.astype(str)), axis=1)
            dim = cross_dim
        else:
            dim = dims[0]
        val_col = config.value_col
        time_col = config.time_col

        base_df = df[df[time_col] == config.base_period]
        comp_df = df[df[time_col] == config.compare_period]

        base_grouped = base_df.groupby(dim)[val_col].sum()
        comp_grouped = comp_df.groupby(dim)[val_col].sum()

        all_dims = sorted(set(base_grouped.index) | set(comp_grouped.index))
        base_total = base_grouped.sum()
        comp_total = comp_grouped.sum()
        overall_change = float(comp_total - base_total)

        contributions = []
        for d in all_dims:
            base_val = float(base_grouped.get(d, 0))
            comp_val = float(comp_grouped.get(d, 0))
            change = comp_val - base_val
            rate = (change / overall_change * 100) if overall_change != 0 else 0
            contributions.append(FactorContribution(
                name=str(d),
                value_change=change,
                contribution_rate=rate,
                rank=0,
            ))

        contributions.sort(key=lambda c: abs(c.value_change), reverse=True)
        for i, c in enumerate(contributions, 1):
            c.rank = i

        overall_rate = ((comp_total - base_total) / base_total * 100) if base_total != 0 else 0

        detail = pd.DataFrame({
            "因子": [c.name for c in contributions],
            f"{config.base_period}值": [float(base_grouped.get(c.name, 0)) for c in contributions],
            f"{config.compare_period}值": [float(comp_grouped.get(c.name, 0)) for c in contributions],
            "变化量": [c.value_change for c in contributions],
            "贡献率(%)": [c.contribution_rate for c in contributions],
            "排名": [c.rank for c in contributions],
        })

        return DecompositionResult(
            method=DecompositionMethod.ADDITION,
            mode=AnalysisMode.DYNAMIC,
            overall_change=overall_change,
            overall_change_rate=overall_rate,
            contributions=contributions,
            is_mece=True,
            detail_table=detail,
            chart_data={
                "labels": [c.name for c in contributions],
                "changes": [c.value_change for c in contributions],
                "rates": [c.contribution_rate for c in contributions],
            },
        )
