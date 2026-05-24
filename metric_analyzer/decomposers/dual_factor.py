"""双因素拆解器（相对数指标按维度拆分）"""

import pandas as pd

from metric_analyzer.decomposers.base import BaseDecomposer
from metric_analyzer.models import (
    AnalysisMode,
    DecompositionMethod,
    DecompositionResult,
    FactorContribution,
    MetricConfig,
)


class DualFactorDecomposer(BaseDecomposer):
    """相对数指标的维度拆解（如满意度=好评量/参评量，按语言线拆）"""

    def can_handle(self, config: MetricConfig) -> bool:
        return config.method == DecompositionMethod.DUAL_FACTOR

    def decompose(self, config: MetricConfig) -> DecompositionResult:
        if config.time_col and config.base_period and config.compare_period:
            return self._dynamic_decompose(config)
        return self._static_decompose(config)

    def _static_decompose(self, config: MetricConfig) -> DecompositionResult:
        """静态：各分项的相对数指标值"""
        df = config.data
        dim = config.dimensions[0]
        num_col = config.numerator_col
        den_col = config.denominator_col

        grouped = df.groupby(dim).agg({num_col: "sum", den_col: "sum"})
        grouped["rate"] = grouped[num_col] / grouped[den_col].replace(0, float("nan"))

        total_num = grouped[num_col].sum()
        total_den = grouped[den_col].sum()
        overall_rate = total_num / total_den if total_den != 0 else 0

        contributions = []
        for rank, (name, row) in enumerate(grouped.sort_values("rate", ascending=False).iterrows(), 1):
            contributions.append(FactorContribution(
                name=str(name),
                value_change=float(row["rate"]),
                contribution_rate=float(row[den_col] / total_den * 100) if total_den != 0 else 0,
                rank=rank,
            ))

        detail = pd.DataFrame({
            "分项": [c.name for c in contributions],
            num_col: [float(grouped.loc[c.name, num_col]) for c in contributions],
            den_col: [float(grouped.loc[c.name, den_col]) for c in contributions],
            "指标值": [c.value_change for c in contributions],
            "占比(%)": [c.contribution_rate for c in contributions],
        })

        return DecompositionResult(
            method=DecompositionMethod.DUAL_FACTOR,
            mode=AnalysisMode.STATIC,
            overall_change=overall_rate,
            overall_change_rate=0.0,
            contributions=contributions,
            is_mece=True,
            detail_table=detail,
        )

    def _dynamic_decompose(self, config: MetricConfig) -> DecompositionResult:
        """动态：拆为指标波动贡献 + 结构变化贡献"""
        df = config.data
        dim = config.dimensions[0]
        num_col = config.numerator_col
        den_col = config.denominator_col
        time_col = config.time_col

        base_df = df[df[time_col] == config.base_period]
        comp_df = df[df[time_col] == config.compare_period]

        base_agg = base_df.groupby(dim).agg({num_col: "sum", den_col: "sum"})
        comp_agg = comp_df.groupby(dim).agg({num_col: "sum", den_col: "sum"})

        # 处理新增维度：上期值设为1
        for d in comp_agg.index:
            if d not in base_agg.index:
                base_agg.loc[d] = {num_col: 1, den_col: 1}

        base_agg["rate"] = base_agg[num_col] / base_agg[den_col].replace(0, float("nan"))
        comp_agg["rate"] = comp_agg[num_col] / comp_agg[den_col].replace(0, float("nan"))

        base_total_num = base_agg[num_col].sum()
        base_total_den = base_agg[den_col].sum()
        comp_total_num = comp_agg[num_col].sum()
        comp_total_den = comp_agg[den_col].sum()

        base_overall = base_total_num / base_total_den if base_total_den != 0 else 0
        comp_overall = comp_total_num / comp_total_den if comp_total_den != 0 else 0
        overall_change = comp_overall - base_overall

        base_agg["share"] = base_agg[den_col] / base_total_den if base_total_den != 0 else 0
        comp_agg["share"] = comp_agg[den_col] / comp_total_den if comp_total_den != 0 else 0

        all_dims = sorted(set(base_agg.index) | set(comp_agg.index))

        contributions = []
        for d in all_dims:
            base_rate = float(base_agg.loc[d, "rate"]) if d in base_agg.index and pd.notna(base_agg.loc[d, "rate"]) else 0
            comp_rate = float(comp_agg.loc[d, "rate"]) if d in comp_agg.index and pd.notna(comp_agg.loc[d, "rate"]) else 0
            base_share = float(base_agg.loc[d, "share"]) if d in base_agg.index else 0
            comp_share = float(comp_agg.loc[d, "share"]) if d in comp_agg.index else 0

            rate_effect = (comp_rate - base_rate) * base_share
            share_effect = (comp_share - base_share) * (base_rate - base_overall)
            total_effect = rate_effect + share_effect

            contributions.append(FactorContribution(
                name=str(d),
                value_change=total_effect,
                contribution_rate=0,
                rank=0,
            ))

        for c in contributions:
            c.contribution_rate = (c.value_change / overall_change * 100) if overall_change != 0 else 0

        contributions.sort(key=lambda c: c.value_change)
        for i, c in enumerate(contributions, 1):
            c.rank = i

        overall_rate_pct = (overall_change / base_overall * 100) if base_overall != 0 else 0

        detail = pd.DataFrame({
            "分项": [c.name for c in contributions],
            f"{config.base_period}指标值": [
                float(base_agg.loc[c.name, "rate"]) if c.name in base_agg.index and pd.notna(base_agg.loc[c.name, "rate"]) else 0
                for c in contributions
            ],
            f"{config.compare_period}指标值": [
                float(comp_agg.loc[c.name, "rate"]) if c.name in comp_agg.index and pd.notna(comp_agg.loc[c.name, "rate"]) else 0
                for c in contributions
            ],
            "指标波动贡献": [
                (float(comp_agg.loc[c.name, "rate"]) - float(base_agg.loc[c.name, "rate"])) * float(base_agg.loc[c.name, "share"])
                if c.name in base_agg.index and c.name in comp_agg.index
                   and pd.notna(base_agg.loc[c.name, "rate"]) and pd.notna(comp_agg.loc[c.name, "rate"])
                else 0
                for c in contributions
            ],
            "结构变化贡献": [
                (float(comp_agg.loc[c.name, "share"]) - float(base_agg.loc[c.name, "share"]))
                * (float(base_agg.loc[c.name, "rate"]) - base_overall)
                if c.name in base_agg.index and c.name in comp_agg.index
                   and pd.notna(base_agg.loc[c.name, "rate"])
                else 0
                for c in contributions
            ],
            "总贡献": [c.value_change for c in contributions],
            "贡献率(%)": [c.contribution_rate for c in contributions],
        })

        return DecompositionResult(
            method=DecompositionMethod.DUAL_FACTOR,
            mode=AnalysisMode.DYNAMIC,
            overall_change=overall_change,
            overall_change_rate=overall_rate_pct,
            contributions=contributions,
            is_mece=True,
            detail_table=detail,
            chart_data={
                "labels": [c.name for c in contributions],
                "changes": [c.value_change for c in contributions],
                "rates": [c.contribution_rate for c in contributions],
            },
        )
