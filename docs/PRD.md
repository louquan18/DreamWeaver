## 织梦者（Dream Weaver）Multi-Agent 长篇小说创作系统设计文档

## 1\. 项目背景

### 1.1 项目简介

织梦者（Dream Weaver）是一套面向长篇网络小说创作场景的 Multi-Agent AI 写作系统。

系统基于 LangGraph 构建 Agent 工作流，通过多阶段协作机制完成：

形成完整的 AI 长篇创作闭环。

系统重点解决：

- 长文本上下文窗口限制
- 长篇创作情节一致性问题
- 人物设定漂移问题
- 多 Agent 协作问题
- 任务中断恢复问题

---

## 2\. 设计目标

### 功能目标

支持完整小说创作流程：

```markdown
题材输入
    ↓
世界观构建
    ↓
小说规划
    ↓
章节生成
    ↓
一致性检查
    ↓
评审优化
    ↓
章节提交
```

### 技术目标

| 目标 | 说明 |
| --- | --- |
| 可扩展 | 支持多模型接入 |
| 可恢复 | 任务断点恢复 |
| 可观测 | 实时状态追踪 |
| 低成本 | 上下文压缩 |
| 高一致性 | 自动校验机制 |

---

## 3\. 总体架构

## 3.1 系统架构图

```markdown
┌─────────────────┐
                │     Frontend    │
                │ React + SSE UI  │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ API Gateway     │
                └────────┬────────┘
                         │
        ┌────────────────┴──────────────┐
        ▼                               ▼

┌─────────────────┐          ┌─────────────────────┐
│ Java Service    │          │ Python AI Service   │
│ Spring Boot     │          │ LangGraph Runtime   │
└─────────────────┘          └─────────────────────┘

        │                               │
        ▼                               ▼

 Stories管理                Agent Workflow Engine
 用户权限                  Context Manager
 审计日志                  Memory Manager
 数据管理                  Model Provider

        │                               │
        └──────────────┬────────────────┘
                       ▼

                ┌─────────────────┐
                │ PostgreSQL      │
                │ Redis           │
                │ Object Storage  │
                └─────────────────┘
```

---

## 4\. Agent 工作流设计

## 4.1 LangGraph 状态机

系统采用 LangGraph 实现状态驱动工作流。

### 工作流节点

```markdown
load_runtime_context
            │
            ▼
novel_context
            │
            ▼
plan_chapter
            │
            ▼
generate_draft
            │
            ▼
check_consistency
            │
       ┌────┴─────┐
       │          │
       ▼          ▼
   review     commit
       │
       ▼
   rewrite
       │
       └──────►review
```

---

## 4.2 State Schema

运行状态定义：

```markdown
class NovelState(TypedDict):

    story_id: str

    chapter_id: str

    novel_context: dict

    chapter_outline: dict

    generated_draft: str

    consistency_report: dict

    review_report: dict

    execution_history: list

    checkpoint_id: str
```

---

## 5\. 多 Agent 设计

## 5.1 Context Agent

负责：

- 历史章节检索
- 人物状态提取
- 世界观加载
- 时间线构建

输出：

```markdown
{
  "timeline": [],
  "characters": [],
  "foreshadows": [],
  "world_rules": []
}
```

---

## 5.2 Planner Agent

负责：

- 章节规划
- 冲突设计
- 剧情推进

输出：

```markdown
{
  "goal": "...",
  "conflict": "...",
  "plot_points": []
}
```

---

## 5.3 Writer Agent

负责：

- 根据规划生成章节草稿

特点：

- 流式输出
- Token级实时反馈

---

## 5.4 Consistency Agent

负责检测：

### 人物一致性

```markdown
性格漂移
能力变化
关系变化
```

### 世界观一致性

```markdown
规则冲突
设定矛盾
时间错误
```

### 情节一致性

```markdown
伏笔遗失
剧情跳跃
因果缺失
```

---

## 5.5 Reviewer Agent

负责：

```markdown
语言质量
节奏控制
冲突强度
阅读体验
```

生成评审报告。

---

## 5.6 Rewrite Agent

根据评审结果：

```markdown
问题定位
局部修复
重写优化
```

形成 AI 自反思（Reflection）能力。

---

## 6\. 结构化上下文管理

## 6.1 问题背景

长篇小说通常超过：

```markdown
100万字+
```

直接拼接 Prompt 存在：

- Token 超限
- 成本高
- 注意力衰减

问题。

---

## 6.2 Structured Memory 设计

采用四层记忆结构。

```markdown
Novel Memory
│
├── Timeline
├── Character Graph
├── Foreshadow Memory
└── World State
```

---

### Timeline

记录事件链：

```markdown
[
  {
    "chapter": 15,
    "event": "主角获得系统"
  }
]
```

---

### Character Graph

人物关系图谱：

```markdown
张三
├── 李四(好友)
├── 王五(敌人)
└── 赵六(导师)
```

---

### Foreshadow Memory

记录：

```markdown
埋下伏笔
触发条件
是否回收
```

---

### World State

记录：

```markdown
势力状态
地图状态
资源状态
规则状态
```

---

## 6.3 Context Compression

压缩流程：

```markdown
原始章节
     ↓
事件抽取
     ↓
摘要生成
     ↓
结构化表示
     ↓
上下文组装
```

平均压缩率：

```markdown
40%+
```

---

## 7\. Checkpoint 恢复机制

## 7.1 设计目标

保证：

```markdown
服务重启
网络中断
模型异常
```

后任务能够继续执行。

---

## 7.2 Checkpoint 数据结构

```markdown
{
  "execution_id": "",
  "current_node": "",
  "state_snapshot": {},
  "pending_tasks": [],
  "timestamp": ""
}
```

---

## 7.3 恢复流程

```markdown
任务启动
      │
      ▼
创建Checkpoint
      │
      ▼
节点执行
      │
      ▼
保存状态
      │
      ▼
异常中断
      │
      ▼
恢复Checkpoint
      │
      ▼
继续执行
```

恢复时间：

```markdown
< 10 秒
```

---

## 8\. 多模型适配层设计

## 8.1 Provider 抽象

统一模型调用接口：

```markdown
class LLMProvider:

    async def generate():

    async def stream():

    async def embedding():
```

---

## 8.2 支持模型

通过 OpenRouter 聚合接入：

- GPT 系列
- Claude 系列
- Gemini 系列
- DeepSeek 系列
- Qwen 系列

---

## 8.3 路由策略

根据任务动态选择模型：

| 任务 | 模型特点 |
| --- | --- |
| 规划 | 推理模型 |
| 写作 | 长文本模型 |
| 校验 | 低成本模型 |
| 评审 | 高质量模型 |

实现成本与效果平衡。

---

## 9\. SSE 实时流式输出

## 9.1 实现方案

```markdown
LLM Stream
      │
      ▼
LangGraph Event
      │
      ▼
SSE Channel
      │
      ▼
Frontend
```

---

## 9.2 推送内容

### Token Stream

```markdown
{
  "type":"token",
  "content":"..."
}
```

### Node Status

```markdown
{
  "type":"node",
  "node":"generate_draft",
  "status":"running"
}
```

### Progress

```markdown
{
  "type":"progress",
  "percent":65
}
```

---

## 10\. Skill 知识库系统

## 10.1 目标

沉淀网文创作经验。

支持：

```markdown
题材分析
套路拆解
范本检索
结构学习
```

---

## 10.2 语料蒸馏流水线

```markdown
原始小说
      │
      ▼
文本清洗
      │
      ▼
摘要生成
      │
      ▼
标签提取
      │
      ▼
结构抽取
      │
      ▼
向量索引
```

---

## 10.3 Skill 结构

```markdown
{
  "genre":"玄幻",
  "tags":["升级流","系统流"],
  "summary":"...",
  "structure":"..."
}
```

目前已覆盖：

```markdown
20+
网文题材
```

---

## 11\. 性能指标

| 指标 | 结果 |
| --- | --- |
| 上下文压缩率 | 40%+ |
| 恢复时间 | <10s |
| 状态完整性 | 100% |
| 覆盖题材 | 20+ |
| 一致性问题修复 | 80+ |
| Agent节点数 | 8+ |
| 支持模型 | 多Provider |

---

## 12\. 项目成果

- 构建完整 LangGraph Multi-Agent 长篇创作框架
- 实现结构化记忆与上下文压缩机制
- 建立 AI 自评审、自修复闭环
- 支持多模型动态编排与流式生成
- 实现生产级 Checkpoint 恢复架构
- 沉淀可复用中文网文 Skill 知识库体系