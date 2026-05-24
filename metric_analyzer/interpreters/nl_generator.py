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


class NLGenerator:
    """自然语言解读生成器"""

    def generate(self, result: DecompositionResult, metric_name: str, top_n: int = 5) -> str:
        """生成自然语言解读"""
        if result.mode == AnalysisMode.STATIC:
            return self._static_summary(result, metric_name, top_n)
        return self._dynamic_summary(result, metric_name, top_n)

    def _direction_text(self, change: float) -> str:
        if change > 0:
            return "上升"
        elif change < 0:
            return "下降"
        return "持平"

    def _value_text(self, change: float, as_percent: bool = False) -> str:
        if as_percent:
            return f"{abs(change):.1f}%"
        if abs(change) < 1:
            return f"{abs(change):.2f}"
        return f"{abs(change):.1f}"

    def _static_summary(self, result: DecompositionResult, name: str, top_n: int) -> str:
        """静态拆解解读"""
        lines = [f"**{name} 现状构成分析**\n"]

        if not result.contributions:
            lines.append("暂无数据可分析。")
            return "\n".join(lines)

        lines.append(f"整体值为 **{result.overall_change:.2f}**。\n")
        lines.append(f"构成分解（Top {top_n}）：")

        shown = result.contributions[:top_n]
        for c in shown:
            lines.append(f"- {c.name}：{c.value_change:.2f}（占比 {c.contribution_rate:.1f}%）")

        if len(result.contributions) > top_n:
            other_rate = sum(c.contribution_rate for c in result.contributions[top_n:])
            lines.append(f"- 其他：占比 {other_rate:.1f}%")

        return "\n".join(lines)

    def _dynamic_summary(self, result: DecompositionResult, name: str, top_n: int) -> str:
        """动态拆解解读"""
        direction = self._direction_text(result.overall_change)

        lines = [f"**{name} 变化归因分析**\n"]

        change_text = self._value_text(result.overall_change)
        rate_text = self._value_text(result.overall_change_rate, as_percent=True)
        lines.append(f"整体 {direction} **{change_text}**（{direction}{rate_text}）。\n")

        if not result.contributions:
            lines.append("暂无贡献数据。")
            return "\n".join(lines)

        lines.append(f"拆解结论（{METHOD_LABELS[result.method]}）：")

        shown = result.contributions[:top_n]

        positives = [c for c in shown if c.value_change > 0]
        negatives = [c for c in shown if c.value_change < 0]

        if negatives:
            top_neg = negatives[0]
            val = self._value_text(top_neg.value_change)
            lines.append(
                f"- **主要拖累项**：{top_neg.name}，贡献率 {abs(top_neg.contribution_rate):.1f}%（-{val}）"
            )

        if len(negatives) > 1:
            for c in negatives[1:]:
                val = self._value_text(c.value_change)
                lines.append(
                    f"- **次要拖累项**：{c.name}，贡献率 {abs(c.contribution_rate):.1f}%（-{val}）"
                )

        if positives:
            for c in positives:
                val = self._value_text(c.value_change)
                lines.append(
                    f"- **正向支撑**：{c.name}，贡献率 {abs(c.contribution_rate):.1f}%（+{val}）"
                )

        if len(result.contributions) > top_n:
            other_rate = sum(c.contribution_rate for c in result.contributions[top_n:])
            lines.append(f"- 其他因子合计贡献率 {other_rate:.1f}%")

        if negatives:
            lines.append(f"\n**建议**：重点关注{negatives[0].name}。")

        if result.is_mece:
            lines.append("\n*注：本拆解结果MECE（不重不漏），各因子贡献可加总。*")

        return "\n".join(lines)
