"""基于规则的指标类型检测器"""

import pandas as pd

from metric_analyzer.models import METRIC_TYPE_TO_METHOD, DecompositionMethod, MetricType


# 关键词 → 指标类型
KEYWORD_RULES: dict[MetricType, list[str]] = {
    MetricType.RATIO: ["率", "占比", "满意度", "好评率", "CSAT", "接通率",
                        "首次解决率", "FCR", "转化率", "留存率", "解决率"],
    MetricType.EFFICIENCY: ["效率", "人效", "单位", "人均", "每小时"],
    MetricType.FLOW_CHAIN: ["漏斗", "激活", "购买", "成交"],
    MetricType.DERIVED_DIFF: ["利润", "净收入", "毛利", "差值", "缺口"],
    MetricType.ABSOLUTE: ["量", "数", "收入", "保费", "通话", "工单", "新增"],
}

METHOD_DESCRIPTIONS = {
    DecompositionMethod.ADDITION: "适用于绝对量指标按维度拆分（如通话量按技能组拆）",
    DecompositionMethod.SUBTRACTION: "适用于衍生差值指标（如利润=收入-成本-费用）",
    DecompositionMethod.MULTIPLICATION: "适用于流程链路指标（如成交用户=新增×激活率×留存率×购买率）",
    DecompositionMethod.DIVISION: "适用于效率/比例指标的分母拆分（如单位人员效率）",
    DecompositionMethod.DUAL_FACTOR: "适用于相对数指标按维度拆分（如满意度按语言线拆）",
}


class MetricDetector:
    """指标类型检测器：关键词匹配 + 数据结构分析"""

    def detect(self, df: pd.DataFrame, name: str) -> list[dict]:
        """检测指标类型，返回候选方法列表，按置信度降序"""
        keyword_hits = self._keyword_match(name)
        structure_hits = self._structure_analyze(df)

        scores: dict[MetricType, float] = {}
        reasons: dict[MetricType, str] = {}

        for mt, score, reason in keyword_hits:
            scores[mt] = scores.get(mt, 0) + score
            reasons[mt] = reason

        for mt, score, reason in structure_hits:
            scores[mt] = scores.get(mt, 0) + score
            if mt in reasons:
                reasons[mt] += f"；{reason}"
            else:
                reasons[mt] = reason

        results = []
        for mt, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            method = METRIC_TYPE_TO_METHOD[mt]
            results.append({
                "metric_type": mt,
                "method": method,
                "confidence": min(score / 2.0, 1.0),
                "reason": reasons.get(mt, ""),
                "description": METHOD_DESCRIPTIONS[method],
            })

        if not results:
            for method in DecompositionMethod:
                results.append({
                    "metric_type": None,
                    "method": method,
                    "confidence": 0.0,
                    "reason": "无法自动识别，请手动选择",
                    "description": METHOD_DESCRIPTIONS[method],
                })

        return results

    def _keyword_match(self, name: str) -> list[tuple[MetricType, float, str]]:
        hits = []
        for mt, keywords in KEYWORD_RULES.items():
            for kw in keywords:
                if kw in name:
                    hits.append((mt, 1.0, f"指标名含'{kw}'"))
                    break
        return hits

    def _structure_analyze(self, df: pd.DataFrame) -> list[tuple[MetricType, float, str]]:
        hits = []
        if df.empty:
            return hits

        cols = set(df.columns)

        ratio_pairs = [("好评", "参评"), ("接通", "呼入"), ("解决", "工单"),
                       ("放弃", "呼入"), ("首次解决", "总工单")]
        for num_kw, den_kw in ratio_pairs:
            has_num = any(num_kw in c for c in cols)
            has_den = any(den_kw in c for c in cols)
            if has_num and has_den:
                hits.append((MetricType.RATIO, 0.8, f"数据含'{num_kw}'和'{den_kw}'列"))
                break

        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if len(numeric_cols) >= 3 and not hits:
            hits.append((MetricType.DERIVED_DIFF, 0.5, f"数据含{len(numeric_cols)}个数值列，可能为减法拆解"))

        flow_keywords = ["激活", "留存", "购买", "成交", "转化"]
        if any(kw in c for c in cols for kw in flow_keywords):
            hits.append((MetricType.FLOW_CHAIN, 0.7, "数据含流程相关列名"))

        return hits
