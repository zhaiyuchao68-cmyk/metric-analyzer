"""核心数据模型"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import pandas as pd


class DecompositionMethod(Enum):
    """拆解方法"""
    ADDITION = "加法拆解"
    SUBTRACTION = "减法拆解"
    MULTIPLICATION = "乘法拆解"
    DUAL_FACTOR = "双因素拆解"


class MetricType(Enum):
    """指标类型"""
    ABSOLUTE = "绝对量"
    DERIVED_DIFF = "衍生差值"
    FLOW_CHAIN = "流程链路"
    RATIO = "比例指标"
    EFFICIENCY = "效率指标"


class AnalysisMode(Enum):
    """分析模式"""
    STATIC = "静态"
    DYNAMIC = "动态"


METRIC_TYPE_TO_METHOD = {
    MetricType.ABSOLUTE: DecompositionMethod.ADDITION,
    MetricType.DERIVED_DIFF: DecompositionMethod.SUBTRACTION,
    MetricType.FLOW_CHAIN: DecompositionMethod.MULTIPLICATION,
    MetricType.RATIO: DecompositionMethod.DUAL_FACTOR,
    MetricType.EFFICIENCY: DecompositionMethod.MULTIPLICATION,
}


@dataclass
class MetricConfig:
    """指标拆解配置"""
    name: str
    metric_type: MetricType
    method: DecompositionMethod
    data: pd.DataFrame
    dimensions: list[str]
    numerator_col: Optional[str] = None
    denominator_col: Optional[str] = None
    value_col: Optional[str] = None
    components: list[str] = field(default_factory=list)
    time_col: Optional[str] = None
    base_period: Optional[str] = None
    compare_period: Optional[str] = None
    top_n: int = 5
    multi_dim_mode: str = "cross"  # "cross"=交叉, "hierarchy"=分层

    def __post_init__(self):
        if self.top_n < 3:
            self.top_n = 3
        if self.top_n > 10:
            self.top_n = 10


@dataclass
class FactorContribution:
    """单个因子的贡献"""
    name: str
    value_change: float
    contribution_rate: float
    rank: int
    rate_effect: Optional[float] = None
    share_effect: Optional[float] = None
    explanation: Optional[str] = None


@dataclass
class DecompositionResult:
    """拆解结果"""
    method: DecompositionMethod
    mode: AnalysisMode
    overall_change: float
    overall_change_rate: float
    contributions: list[FactorContribution]
    is_mece: bool
    summary: str = ""
    detail_table: pd.DataFrame = field(default_factory=pd.DataFrame)
    chart_data: dict = field(default_factory=dict)
