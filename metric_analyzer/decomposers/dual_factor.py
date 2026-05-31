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
        df = config.data.copy()

        # 多维度处理：交叉模式时合并维度为组合键
        dims = config.dimensions
        if len(dims) > 1 and config.multi_dim_mode == "cross":
            cross_dim = "×".join(dims)
            df[cross_dim] = df[dims].apply(lambda row: " - ".join(row.astype(str)), axis=1)
            dim = cross_dim
        else:
            dim = dims[0]
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
        """动态：拆为指标波动贡献 + 结构变化贡献

        对两期都存在的维度：标准双因素公式（MECE）
        对新增维度：无法定义上期指标值，作为"新增维度影响"单独计算（残差法）
        对消失维度：贡献率=0
        """
        df = config.data.copy()

        # 多维度处理
        dims = config.dimensions
        if len(dims) > 1 and config.multi_dim_mode == "cross":
            # 交叉模式：合并维度为组合键
            cross_dim = "×".join(dims)
            df[cross_dim] = df[dims].apply(lambda row: " - ".join(row.astype(str)), axis=1)
            dim = cross_dim
        elif len(dims) > 1 and config.multi_dim_mode == "hierarchy":
            # 分层模式：先按主维度拆解，再对每个主维度按次维度拆解
            return self._hierarchy_decompose(config)
        else:
            dim = dims[0]
        num_col = config.numerator_col
        den_col = config.denominator_col
        time_col = config.time_col

        base_df = df[df[time_col] == config.base_period]
        comp_df = df[df[time_col] == config.compare_period]

        base_agg = base_df.groupby(dim).agg({num_col: "sum", den_col: "sum"})
        comp_agg = comp_df.groupby(dim).agg({num_col: "sum", den_col: "sum"})

        base_agg["rate"] = base_agg[num_col] / base_agg[den_col].replace(0, float("nan"))
        comp_agg["rate"] = comp_agg[num_col] / comp_agg[den_col].replace(0, float("nan"))

        base_total_den = base_agg[den_col].sum()
        comp_total_den = comp_agg[den_col].sum()

        base_overall = float(base_agg[num_col].sum()) / base_total_den if base_total_den != 0 else 0
        comp_overall = float(comp_agg[num_col].sum()) / comp_total_den if comp_total_den != 0 else 0
        overall_change = comp_overall - base_overall

        base_agg["share"] = base_agg[den_col] / base_total_den if base_total_den != 0 else 0
        comp_agg["share"] = comp_agg[den_col] / comp_total_den if comp_total_den != 0 else 0

        both_dims = sorted(set(base_agg.index) & set(comp_agg.index))
        new_dims = sorted(set(comp_agg.index) - set(base_agg.index))
        gone_dims = sorted(set(base_agg.index) - set(comp_agg.index))

        contributions = []

        # 两期都存在的维度：标准双因素公式
        for d in both_dims:
            base_rate = float(base_agg.loc[d, "rate"])
            comp_rate = float(comp_agg.loc[d, "rate"])
            base_share = float(base_agg.loc[d, "share"])
            comp_share = float(comp_agg.loc[d, "share"])

            rate_effect = (comp_rate - base_rate) * base_share
            share_effect = (comp_share - base_share) * (comp_rate - base_overall)
            total_effect = rate_effect + share_effect

            contributions.append(FactorContribution(
                name=str(d),
                value_change=total_effect,
                contribution_rate=0,
                rank=0,
                rate_effect=rate_effect,
                share_effect=share_effect,
            ))

        # 新增维度：base_share=0, rate_effect=0, share_effect=comp_share*comp_rate
        for d in new_dims:
            comp_rate = float(comp_agg.loc[d, "rate"])
            comp_share = float(comp_agg.loc[d, "share"])

            rate_effect = 0
            share_effect = comp_share * (comp_rate - base_overall)
            total_effect = rate_effect + share_effect

            contributions.append(FactorContribution(
                name=str(d),
                value_change=total_effect,
                contribution_rate=0,
                rank=0,
                rate_effect=rate_effect,
                share_effect=share_effect,
            ))

        # 消失维度：贡献为0
        for d in gone_dims:
            contributions.append(FactorContribution(
                name=str(d),
                value_change=0.0,
                contribution_rate=0,
                rank=0,
                rate_effect=0.0,
                share_effect=0.0,
            ))

        # 计算贡献率
        for c in contributions:
            c.contribution_rate = (c.value_change / overall_change * 100) if overall_change != 0 else 0

        # 按贡献值排序（从小到大，负值在前）
        contributions.sort(key=lambda c: c.value_change)
        for i, c in enumerate(contributions, 1):
            c.rank = i

        # 验证MECE
        total_contrib = sum(c.value_change for c in contributions)
        is_mece = bool(abs(total_contrib - overall_change) < 1e-6)

        overall_rate_pct = (overall_change / base_overall * 100) if base_overall != 0 else 0

        # 构建详细表格
        detail_rows = []
        for c in contributions:
            d = c.name
            if d in both_dims:
                base_rate = float(base_agg.loc[d, "rate"])
                comp_rate = float(comp_agg.loc[d, "rate"])
                base_share = float(base_agg.loc[d, "share"])
                comp_share = float(comp_agg.loc[d, "share"])
                rate_effect = (comp_rate - base_rate) * base_share
                share_effect = (comp_share - base_share) * (comp_rate - base_overall)
                detail_rows.append({
                    "分项": d,
                    f"{config.base_period}指标值": base_rate,
                    f"{config.compare_period}指标值": comp_rate,
                    f"{config.base_period}占比": base_share,
                    f"{config.compare_period}占比": comp_share,
                    "指标波动贡献": rate_effect,
                    "结构变化贡献": share_effect,
                    "总贡献": c.value_change,
                    "上期整体均值": base_overall,
                    "本期整体均值": comp_overall,
                })
            elif d in new_dims:
                comp_rate = float(comp_agg.loc[d, "rate"])
                comp_share = float(comp_agg.loc[d, "share"])
                detail_rows.append({
                    "分项": d,
                    f"{config.base_period}指标值": "（新增）",
                    f"{config.compare_period}指标值": comp_rate,
                    f"{config.base_period}占比": 0,
                    f"{config.compare_period}占比": comp_share,
                    "指标波动贡献": "—",
                    "结构变化贡献": comp_share * (comp_rate - base_overall),
                    "总贡献": c.value_change,
                    "上期整体均值": base_overall,
                    "本期整体均值": comp_overall,
                })

        detail = pd.DataFrame(detail_rows)

        return DecompositionResult(
            method=DecompositionMethod.DUAL_FACTOR,
            mode=AnalysisMode.DYNAMIC,
            overall_change=overall_change,
            overall_change_rate=overall_rate_pct,
            contributions=contributions,
            is_mece=is_mece,
            detail_table=detail,
            chart_data={
                "labels": [c.name for c in contributions],
                "changes": [c.value_change for c in contributions],
                "rates": [c.contribution_rate for c in contributions],
            },
        )

    def _hierarchy_decompose(self, config: MetricConfig) -> DecompositionResult:
        """分层模式：先按主维度拆解，再对每个主维度按次维度细分"""
        df = config.data.copy()
        dims = config.dimensions
        main_dim = dims[0]
        sub_dims = dims[1:]
        num_col = config.numerator_col
        den_col = config.denominator_col
        time_col = config.time_col

        base_df = df[df[time_col] == config.base_period]
        comp_df = df[df[time_col] == config.compare_period]

        # 按主维度聚合
        base_main = base_df.groupby(main_dim).agg({num_col: "sum", den_col: "sum"})
        comp_main = comp_df.groupby(main_dim).agg({num_col: "sum", den_col: "sum"})

        base_main["rate"] = base_main[num_col] / base_main[den_col].replace(0, float("nan"))
        comp_main["rate"] = comp_main[num_col] / comp_main[den_col].replace(0, float("nan"))

        base_total_den = base_main[den_col].sum()
        comp_total_den = comp_main[den_col].sum()

        base_overall = float(base_main[num_col].sum()) / base_total_den if base_total_den != 0 else 0
        comp_overall = float(comp_main[num_col].sum()) / comp_total_den if comp_total_den != 0 else 0
        overall_change = comp_overall - base_overall

        base_main["share"] = base_main[den_col] / base_total_den if base_total_den != 0 else 0
        comp_main["share"] = comp_main[den_col] / comp_total_den if comp_total_den != 0 else 0

        all_main_dims = sorted(set(base_main.index) | set(comp_main.index))

        contributions = []
        child_results = {}

        for main_name in all_main_dims:
            # 主维度贡献
            base_rate = float(base_main.loc[main_name, "rate"]) if main_name in base_main.index else 0
            comp_rate = float(comp_main.loc[main_name, "rate"]) if main_name in comp_main.index else 0
            base_share = float(base_main.loc[main_name, "share"]) if main_name in base_main.index else 0
            comp_share = float(comp_main.loc[main_name, "share"]) if main_name in comp_main.index else 0

            if main_name in base_main.index and main_name in comp_main.index:
                rate_effect = (comp_rate - base_rate) * base_share
                share_effect = (comp_share - base_share) * (comp_rate - base_overall)
            elif main_name in comp_main.index:
                rate_effect = 0
                share_effect = comp_share * (comp_rate - base_overall)
            else:
                rate_effect = 0
                share_effect = 0

            total_effect = rate_effect + share_effect
            contributions.append(FactorContribution(
                name=str(main_name),
                value_change=total_effect,
                contribution_rate=0,
                rank=0,
                rate_effect=rate_effect,
                share_effect=share_effect,
            ))

            # 对该主维度进行次维度细分
            main_base_df = base_df[base_df[main_dim] == main_name] if main_name in base_main.index else pd.DataFrame()
            main_comp_df = comp_df[comp_df[main_dim] == main_name] if main_name in comp_main.index else pd.DataFrame()

            if not main_base_df.empty and not main_comp_df.empty and sub_dims:
                sub_result = self._decompose_sub_level(
                    main_base_df, main_comp_df, sub_dims[0],
                    num_col, den_col, time_col,
                    base_overall, config.base_period, config.compare_period
                )
                child_results[main_name] = sub_result

        # 计算贡献率
        for c in contributions:
            c.contribution_rate = (c.value_change / overall_change * 100) if overall_change != 0 else 0

        contributions.sort(key=lambda c: c.value_change)
        for i, c in enumerate(contributions, 1):
            c.rank = i

        total_contrib = sum(c.value_change for c in contributions)
        is_mece = bool(abs(total_contrib - overall_change) < 1e-6)
        overall_rate_pct = (overall_change / base_overall * 100) if base_overall != 0 else 0

        # 构建详情表
        detail_rows = []
        for c in contributions:
            main_name = c.name
            base_rate = float(base_main.loc[main_name, "rate"]) if main_name in base_main.index else 0
            comp_rate = float(comp_main.loc[main_name, "rate"]) if main_name in comp_main.index else 0
            base_share = float(base_main.loc[main_name, "share"]) if main_name in base_main.index else 0
            comp_share = float(comp_main.loc[main_name, "share"]) if main_name in comp_main.index else 0
            detail_rows.append({
                "分项": main_name,
                f"{config.base_period}指标值": base_rate,
                f"{config.compare_period}指标值": comp_rate,
                f"{config.base_period}占比": base_share,
                f"{config.compare_period}占比": comp_share,
                "指标波动贡献": c.rate_effect,
                "结构变化贡献": c.share_effect,
                "总贡献": c.value_change,
                "上期整体均值": base_overall,
                "本期整体均值": comp_overall,
            })

        detail = pd.DataFrame(detail_rows)

        return DecompositionResult(
            method=DecompositionMethod.DUAL_FACTOR,
            mode=AnalysisMode.DYNAMIC,
            overall_change=overall_change,
            overall_change_rate=overall_rate_pct,
            contributions=contributions,
            is_mece=is_mece,
            detail_table=detail,
            child_results=child_results,
            chart_data={
                "labels": [c.name for c in contributions],
                "changes": [c.value_change for c in contributions],
                "rates": [c.contribution_rate for c in contributions],
            },
        )

    def _decompose_sub_level(self, base_df, comp_df, sub_dim, num_col, den_col, time_col, base_overall, base_period, compare_period):
        """对单个主维度进行次维度拆解"""
        base_agg = base_df.groupby(sub_dim).agg({num_col: "sum", den_col: "sum"})
        comp_agg = comp_df.groupby(sub_dim).agg({num_col: "sum", den_col: "sum"})

        base_agg["rate"] = base_agg[num_col] / base_agg[den_col].replace(0, float("nan"))
        comp_agg["rate"] = comp_agg[num_col] / comp_agg[den_col].replace(0, float("nan"))

        base_total_den = base_agg[den_col].sum()
        comp_total_den = comp_agg[den_col].sum()

        base_sub_overall = float(base_agg[num_col].sum()) / base_total_den if base_total_den != 0 else 0
        comp_sub_overall = float(comp_agg[num_col].sum()) / comp_total_den if comp_total_den != 0 else 0
        sub_overall_change = comp_sub_overall - base_sub_overall

        base_agg["share"] = base_agg[den_col] / base_total_den if base_total_den != 0 else 0
        comp_agg["share"] = comp_agg[den_col] / comp_total_den if comp_total_den != 0 else 0

        all_dims = sorted(set(base_agg.index) | set(comp_agg.index))
        contributions = []

        for d in all_dims:
            base_rate = float(base_agg.loc[d, "rate"]) if d in base_agg.index else 0
            comp_rate = float(comp_agg.loc[d, "rate"]) if d in comp_agg.index else 0
            base_share = float(base_agg.loc[d, "share"]) if d in base_agg.index else 0
            comp_share = float(comp_agg.loc[d, "share"]) if d in comp_agg.index else 0

            if d in base_agg.index and d in comp_agg.index:
                rate_effect = (comp_rate - base_rate) * base_share
                share_effect = (comp_share - base_share) * (comp_rate - base_sub_overall)
            elif d in comp_agg.index:
                rate_effect = 0
                share_effect = comp_share * (comp_rate - base_sub_overall)
            else:
                rate_effect = 0
                share_effect = 0

            total_effect = rate_effect + share_effect
            contributions.append(FactorContribution(
                name=str(d),
                value_change=total_effect,
                contribution_rate=0,
                rank=0,
                rate_effect=rate_effect,
                share_effect=share_effect,
            ))

        for c in contributions:
            c.contribution_rate = (c.value_change / sub_overall_change * 100) if sub_overall_change != 0 else 0

        contributions.sort(key=lambda c: c.value_change)
        for i, c in enumerate(contributions, 1):
            c.rank = i

        return {
            "overall_change": sub_overall_change,
            "base_overall": base_sub_overall,
            "comp_overall": comp_sub_overall,
            "contributions": contributions,
        }
