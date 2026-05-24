"""呼叫中心预设指标"""

from dataclasses import dataclass, field

from metric_analyzer.models import DecompositionMethod, MetricType


CALL_CENTER_PRESETS: dict[str, dict] = {
    "客户满意度": {
        "method": DecompositionMethod.DUAL_FACTOR,
        "metric_type": MetricType.RATIO,
        "dimensions": ["语言线", "班组", "渠道"],
        "numerator": "好评量",
        "denominator": "参评量",
    },
    "问题解决率": {
        "method": DecompositionMethod.DUAL_FACTOR,
        "metric_type": MetricType.RATIO,
        "dimensions": ["技能组", "工单类型"],
        "numerator": "解决量",
        "denominator": "工单量",
    },
    "接通率": {
        "method": DecompositionMethod.DUAL_FACTOR,
        "metric_type": MetricType.RATIO,
        "dimensions": ["时段", "技能组"],
        "numerator": "接通量",
        "denominator": "呼入量",
    },
    "放弃率": {
        "method": DecompositionMethod.DUAL_FACTOR,
        "metric_type": MetricType.RATIO,
        "dimensions": ["时段", "技能组"],
        "numerator": "放弃量",
        "denominator": "呼入量",
    },
    "首次解决率": {
        "method": DecompositionMethod.DUAL_FACTOR,
        "metric_type": MetricType.RATIO,
        "dimensions": ["问题类型", "坐席"],
        "numerator": "首次解决量",
        "denominator": "总工单量",
    },
    "工单处理量": {
        "method": DecompositionMethod.ADDITION,
        "metric_type": MetricType.ABSOLUTE,
        "dimensions": ["班组", "渠道"],
    },
    "通话量": {
        "method": DecompositionMethod.ADDITION,
        "metric_type": MetricType.ABSOLUTE,
        "dimensions": ["技能组", "时段"],
    },
    "单通成本": {
        "method": DecompositionMethod.SUBTRACTION,
        "metric_type": MetricType.DERIVED_DIFF,
        "dimensions": ["技能组"],
        "components": ["人力成本", "系统成本", "其他成本"],
    },
}
