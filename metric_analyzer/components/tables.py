"""数据表格组件"""

import pandas as pd

from metric_analyzer.models import DecompositionResult


def result_table(result: DecompositionResult, top_n: int = 5) -> pd.DataFrame:
    """格式化结果表格，用于Streamlit展示"""
    if result.detail_table is not None and not result.detail_table.empty:
        return result.detail_table.head(top_n)

    rows = []
    for c in result.contributions[:top_n]:
        rows.append({
            "因子": c.name,
            "变化量": round(c.value_change, 4),
            "贡献率(%)": round(c.contribution_rate, 1),
            "排名": c.rank,
        })
    return pd.DataFrame(rows)
