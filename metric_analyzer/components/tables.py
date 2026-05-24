"""数据表格组件"""

import pandas as pd

from metric_analyzer.models import DecompositionMethod, DecompositionResult


# 这些列的值是小数，需要转为百分比显示
_PCT_COLS_KEYWORDS = ["指标值", "占比", "波动贡献", "结构变化贡献", "总贡献"]
# 内部列，不展示
_INTERNAL_COLS = ["上期整体均值", "本期整体均值", "贡献率(%)"]
# 量指标方法（加减法），数值列不转百分比
_ABSOLUTE_METHODS = {DecompositionMethod.ADDITION, DecompositionMethod.SUBTRACTION}
_MUL_METHODS = {DecompositionMethod.MULTIPLICATION, DecompositionMethod.DIVISION}
# 量指标的数值列关键词（不转百分比）
_ABSOLUTE_VALUE_KEYWORDS = ["值", "变化量", "变化", "LMDI贡献", "数值", "总贡献", "波动贡献", "结构变化贡献"]


def result_table(result: DecompositionResult, top_n: int = 5) -> pd.DataFrame:
    """格式化结果表格，用于Streamlit展示"""
    is_abs = result.method in _ABSOLUTE_METHODS
    is_mul = result.method in _MUL_METHODS

    if result.detail_table is not None and not result.detail_table.empty:
        df = result.detail_table.head(top_n).copy()
        # 去掉内部列
        df = df.drop(columns=[c for c in _INTERNAL_COLS if c in df.columns], errors="ignore")
        # 乘法/除法：重算贡献率 = LMDI值 / 上期总量 × 100%
        if is_mul and "贡献率(%)" in df.columns:
            base_overall = result.overall_change * 100 / result.overall_change_rate if result.overall_change_rate != 0 else 1
            lmdi_col = next((c for c in df.columns if "LMDI" in c or "总贡献" in c), None)
            if lmdi_col:
                df["贡献率(%)"] = df[lmdi_col].apply(
                    lambda v: f"{v / base_overall * 100:.2f}%" if isinstance(v, (int, float)) else v
                )
        # 将小数值转为百分比格式
        for col in df.columns:
            if col == "贡献率(%)" and is_mul:
                continue  # 已经处理过
            # 乘法/除法：LMDI相关列取整显示
            if is_mul and any(kw in col for kw in _ABSOLUTE_VALUE_KEYWORDS):
                df[col] = df[col].apply(
                    lambda v: f"{v:+,.0f}" if isinstance(v, (int, float)) else v
                )
                continue
            if any(kw in col for kw in _PCT_COLS_KEYWORDS):
                # 量指标的数值列不转百分比
                if is_abs and any(kw in col for kw in _ABSOLUTE_VALUE_KEYWORDS):
                    df[col] = df[col].apply(
                        lambda v: f"{v:,.0f}" if isinstance(v, (int, float)) else v
                    )
                elif is_mul:
                    # 乘法/除法：同列有任一值>1则按数值，否则按百分比
                    numeric_vals = [v for v in df[col] if isinstance(v, (int, float))]
                    if any(abs(v) > 1 for v in numeric_vals):
                        df[col] = df[col].apply(
                            lambda v: f"{v:,.0f}" if isinstance(v, (int, float)) else v
                        )
                    else:
                        df[col] = df[col].apply(
                            lambda v: f"{v * 100:.2f}%" if isinstance(v, (int, float)) else v
                        )
                else:
                    df[col] = df[col].apply(
                        lambda v: f"{v * 100:.2f}%" if isinstance(v, (int, float)) else v
                    )
        return df

    rows = []
    for c in result.contributions[:top_n]:
        if is_abs:
            change_text = f"{c.value_change:+,.0f}"
        elif is_mul:
            base_overall = result.overall_change * 100 / result.overall_change_rate if result.overall_change_rate != 0 else 1
            change_text = f"{c.value_change / base_overall * 100:.2f}%"
        else:
            change_text = f"{c.value_change * 100:.2f}%"
        rows.append({
            "因子": c.name,
            "变化量": change_text,
            "排名": c.rank,
        })
    return pd.DataFrame(rows)
