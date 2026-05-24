"""拆解器抽象基类"""

from abc import ABC, abstractmethod

from metric_analyzer.models import DecompositionResult, MetricConfig


class BaseDecomposer(ABC):
    """所有拆解器的基类"""

    @abstractmethod
    def can_handle(self, config: MetricConfig) -> bool:
        """判断是否能处理该配置"""
        ...

    @abstractmethod
    def decompose(self, config: MetricConfig) -> DecompositionResult:
        """执行拆解，返回统一结果"""
        ...
