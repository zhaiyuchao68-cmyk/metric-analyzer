# CLAUDE.md — 项目约定

## 语言要求

- 所有回复、注释、文档、commit message 统一使用中文
- 报错信息和技术术语保留英文原文（如 pandas、Streamlit、LMDI）
- 不要在代码注释里写英文

## 项目概况

- 项目名：指标拆解自动化工具
- 用途：为呼叫中心业务提供自动化指标拆解分析
- 技术栈：Python + Streamlit + Plotly + pandas
- 设计文档：docs/superpowers/specs/2025-05-24-metric-decomposition-design.md

## 关键决策

- 架构：Streamlit 前端 + 独立分析引擎（metric_analyzer 包）
- 拆解方法：加法、减法、乘法(LMDI)、双因素，4种方法统一接口
- 指标检测：关键词匹配 + 数据结构分析，自动推荐 + 用户确认
- 预设指标：呼叫中心常见指标内置，支持 YAML 自定义扩展
- 输出：自然语言解读 + Plotly 图表 + 数据表格
- Top N 默认5，用户可调3~10

## 开发规范

- 先写测试再写实现
- 每个拆解器独立单元测试
- 用示例数据文件验证端到端流程
