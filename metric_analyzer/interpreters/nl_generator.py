"""自然语言解读生成器"""

from metric_analyzer.models import (
    AnalysisMode,
    DecompositionMethod,
    DecompositionResult,
)


METHOD_LABELS = {
    DecompositionMethod.ADDITION: "加法拆解",
    DecompositionMethod.SUBTRACTION: "减法拆解",
    DecompositionMethod.MULTIPLICATION: "LMDI乘法拆解",
    DecompositionMethod.DIVISION: "除法拆解",
    DecompositionMethod.DUAL_FACTOR: "双因素拆解",
}

# 量指标（加减法）用原始数值，率指标（乘除+双因素）用百分比
_ABSOLUTE_METHODS = {DecompositionMethod.ADDITION, DecompositionMethod.SUBTRACTION}


class NLGenerator:
    """自然语言解读生成器"""

    def generate(self, result: DecompositionResult, metric_name: str, top_n: int = 5) -> str:
        """生成自然语言解读"""
        if result.mode == AnalysisMode.STATIC:
            return self._static_summary(result, metric_name, top_n)
        if result.method == DecompositionMethod.DUAL_FACTOR:
            return self._dual_factor_report(result, metric_name, top_n)
        return self._dynamic_summary(result, metric_name, top_n)

    def _is_absolute(self, result) -> bool:
        return result.method in _ABSOLUTE_METHODS

    def _direction_text(self, change: float) -> str:
        if change > 0:
            return "上升"
        elif change < 0:
            return "下降"
        return "持平"

    def _pct(self, value: float) -> str:
        """将小数值转为百分比文本，如 0.85 → '85.00%'"""
        return f"{value * 100:.2f}%"

    def _pct_signed(self, value: float) -> str:
        """带正负号的百分比文本，如 -0.023 → '-2.30%'"""
        pct = value * 100
        if abs(pct) < 0.005:
            return "0.00%"
        sign = "+" if pct > 0 else ""
        return f"{sign}{pct:.2f}%"

    def _pp(self, value: float) -> str:
        """将小数值转为百分点文本，如 -0.023 → '2.30'"""
        return f"{abs(value) * 100:.2f}"

    def _fmt_value(self, value: float, result) -> str:
        """格式化数值：量指标用原始数字，率指标用百分比"""
        if self._is_absolute(result):
            if abs(value) >= 1:
                return f"{value:,.0f}"
            return f"{value:.2f}"
        return f"{value * 100:.2f}%"

    def _fmt_signed(self, value: float, result) -> str:
        """格式化带符号数值"""
        if self._is_absolute(result):
            if abs(value) >= 1:
                return f"{value:+,.0f}"
            return f"{value:+.2f}"
        return self._pct_signed(value)

    def _static_summary(self, result: DecompositionResult, name: str, top_n: int) -> str:
        """静态拆解解读"""
        lines = [f"**{name} 现状构成分析**\n"]

        if not result.contributions:
            lines.append("暂无数据可分析。")
            return "\n".join(lines)

        lines.append(f"整体值为 **{self._fmt_value(result.overall_change, result)}**。\n")
        lines.append(f"构成分解（Top {top_n}）：")

        shown = result.contributions[:top_n]
        for c in shown:
            lines.append(f"- {c.name}：{self._fmt_value(c.value_change, result)}（占比 {c.contribution_rate:.1f}%）")

        if len(result.contributions) > top_n:
            other_rate = sum(c.contribution_rate for c in result.contributions[top_n:])
            lines.append(f"- 其他：占比 {other_rate:.1f}%")

        return "\n".join(lines)

    def _dynamic_summary(self, result: DecompositionResult, name: str, top_n: int) -> str:
        """动态拆解解读（非双因素）"""
        direction = self._direction_text(result.overall_change)
        is_abs = self._is_absolute(result)

        lines = [f"**{name} 变化归因分析**\n"]

        if is_abs:
            lines.append(f"整体{direction} **{self._fmt_value(abs(result.overall_change), result)}**。\n")
        else:
            pct_text = f"{abs(result.overall_change) * 100:.2f}%"
            rate_text = f"{abs(result.overall_change_rate):.1f}%"
            lines.append(f"整体{direction} **{pct_text}**（{direction}{rate_text}）。\n")

        if not result.contributions:
            lines.append("暂无贡献数据。")
            return "\n".join(lines)

        lines.append(f"拆解结论（{METHOD_LABELS[result.method]}）：")

        shown = result.contributions[:top_n]
        for c in shown:
            val = self._fmt_signed(c.value_change, result)
            if c.value_change == 0:
                lines.append(f"- **{c.name}**：持平")
            else:
                lines.append(f"- **{c.name}**：{val}")

        if len(result.contributions) > top_n:
            other = sum(c.value_change for c in result.contributions[top_n:])
            lines.append(f"- 其他：{self._fmt_signed(other, result)}")

        negatives = [c for c in result.contributions if c.value_change < 0]
        if negatives:
            lines.append(f"\n**建议**：重点关注 **{negatives[0].name}**，是最大的拖累因素。")

        if result.is_mece:
            total = self._fmt_signed(sum(c.value_change for c in result.contributions), result)
            lines.append(f"\n*各因子贡献加总 = {total}，与整体变化一致（MECE）。*")

        return "\n".join(lines)

    def _dual_factor_report(self, result: DecompositionResult, name: str, top_n: int) -> str:
        """双因素拆解：分析报告式输出"""
        direction = self._direction_text(result.overall_change)

        lines = [f"**{name} 变化归因分析**\n"]

        pct_text = f"{abs(result.overall_change) * 100:.2f}%"
        rate_text = f"{abs(result.overall_change_rate):.1f}%"
        lines.append(f"整体{direction} **{pct_text}**（{direction}{rate_text}）。\n")

        if not result.contributions:
            lines.append("暂无贡献数据。")
            return "\n".join(lines)

        shown = result.contributions[:top_n]

        for c in shown:
            if c.rate_effect is None or c.share_effect is None:
                continue

            re = c.rate_effect
            se = c.share_effect
            total = c.value_change

            # 标题：XX线对整体XX的拖累/拉动 = ±X.XX%，拆成两块
            if total < 0:
                lines.append(f"**{c.name}**对整体{name}的拖累 = **{self._pct_signed(total)}**，拆成两块：\n")
            else:
                lines.append(f"**{c.name}**对整体{name}的拉动 = **{self._pct_signed(total)}**，拆成两块：\n")

            re_is_major = abs(re) >= abs(se)
            re_label = "大头" if re_is_major else "小头"
            se_label = "小头" if re_is_major else "大头"

            # ① 指标波动
            lines.append(f"**① 指标波动 {self._pct_signed(re)}（{re_label}）**")
            if abs(re) >= 1e-8:
                lines.append(self._rate_narrative(c.name, re, se, result))
            else:
                lines.append(f"  {'上期不存在，无指标变化可比。' if abs(se) > 1e-8 else '指标值没有变化。'}")
            lines.append("")

            # ② 占比波动
            lines.append(f"**② 占比波动 {self._pct_signed(se)}（{se_label}）**")
            if abs(se) >= 1e-8:
                lines.append(self._share_narrative(c.name, re, se, result))
            else:
                lines.append(f"  占比没有变化。")
            lines.append("")

        # 简单记
        lines.append("---")
        lines.append("**简单记：**")
        lines.append("- 指标波动 = 这条线自己好评率变了，对整体的影响")
        lines.append("- 占比波动 = 占比变了 × 这条线好坏程度（与整体均值比），正=好事，负=坏事")
        lines.append("")

        # 最大拖累项
        negatives = [c for c in result.contributions if c.value_change < 0]
        if negatives:
            lines.append(f"**建议**：重点关注 **{negatives[0].name}**，是最大的拖累因素。")

        if result.is_mece:
            lines.append(f"\n*各因子贡献加总 = {self._pct_signed(sum(c.value_change for c in result.contributions))}，与整体变化一致（MECE）。*")

        return "\n".join(lines)

    def _find_col(self, columns, *keywords):
        """找到同时包含所有关键词的列名"""
        for col in columns:
            if all(kw in col for kw in keywords):
                return col
        return None

    def _rate_narrative(self, name, re, se, result) -> str:
        """指标波动的叙述段落"""
        row = result.detail_table[result.detail_table["分项"] == name]
        if row.empty:
            return ""
        row = row.iloc[0]
        cols = row.index.tolist()

        base_rate_col = self._find_col(cols, "指标值")
        comp_rate_col = self._find_col(cols, list(reversed([c for c in cols if "指标值" in c]))[0]) if sum(1 for c in cols if "指标值" in c) >= 2 else None

        # 找所有含"指标值"的列，第一个是base，第二个是compare
        rate_cols = [c for c in cols if "指标值" in c]
        if len(rate_cols) < 2:
            return ""
        base_rate_col, comp_rate_col = rate_cols[0], rate_cols[1]

        share_cols = [c for c in cols if "占比" in c]
        base_share_col = share_cols[0] if share_cols else None

        base_rate = row[base_rate_col]
        comp_rate = row[comp_rate_col]
        base_share = row[base_share_col] if base_share_col else 0

        if isinstance(base_rate, str):
            return f"  上期不存在，无法衡量指标变化。"

        delta_pp = abs(comp_rate - base_rate) * 100
        re_pp = abs(re) * 100
        direction = "涨" if comp_rate > base_rate else "掉"
        effect = "拉高" if re > 0 else "拉低"

        return (
            f"  {name}自己的好评率从 {base_rate:.2%} {direction}到 {comp_rate:.2%}，"
            f"{direction}了 {delta_pp:.1f} 个百分点。"
            f"它在上期体量占 {base_share:.0%}，"
            f"所以光这一项服务质量{'下滑' if re < 0 else '提升'}，"
            f"就把整体好评率{effect}了 {re_pp:.2f} 个百分点。"
        )

    def _share_narrative(self, name, re, se, result) -> str:
        """占比波动的叙述段落"""
        row = result.detail_table[result.detail_table["分项"] == name]
        if row.empty:
            return ""
        row = row.iloc[0]
        cols = row.index.tolist()

        share_cols = [c for c in cols if "占比" in c]
        rate_cols = [c for c in cols if "指标值" in c]

        if len(share_cols) < 2:
            return ""

        base_share = row[share_cols[0]]
        comp_share = row[share_cols[1]]
        comp_rate = row[rate_cols[1]] if len(rate_cols) >= 2 else 0
        base_overall = row.get("上期整体均值", 0)

        if isinstance(base_share, str) or base_share == 0:
            return (
                f"  上期不存在，本期好评率 {comp_rate:.2%}，"
                f"评价量占比 {comp_share:.2%}，全部贡献来自新增。"
            )

        delta_pp = abs(comp_share - base_share) * 100
        direction = "涨" if comp_share > base_share else "降"

        # 好评率与整体的关系
        if comp_rate > base_overall:
            rate_vs_overall = f"好评率 {comp_rate:.2%} 高于整体均值 {base_overall:.2%}"
            # 高于整体：占比涨=好，占比降=拖后腿
            logic = "权重调高拉高整体" if comp_share >= base_share else "权重调低拖后腿"
        else:
            rate_vs_overall = f"好评率 {comp_rate:.2%} 低于整体均值 {base_overall:.2%}"
            # 低于整体：占比涨=拖后腿，占比降=好事
            logic = "权重调高拖后腿" if comp_share >= base_share else "权重调低反而是好事"

        return (
            f"  评价量占比从 {base_share:.2%} {direction}到 {comp_share:.2%}"
            f"（{direction}了 {delta_pp:.1f} 个百分点）。"
            f"它的{rate_vs_overall}，{logic}，"
            f"贡献了 {se*100:+.2f} 个百分点。"
        )
