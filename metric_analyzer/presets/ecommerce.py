"""电商/零售预设指标"""

from metric_analyzer.models import DecompositionMethod, MetricType

ECOMMERCE_PRESETS: dict[str, dict] = {
    "售后率": {
        "method": DecompositionMethod.DUAL_FACTOR,
        "metric_type": MetricType.RATIO,
        "dimensions": ["品类", "渠道", "时间段"],
        "numerator": "售后量",
        "denominator": "商品销量",
    },
}
