# DreamWeaver 架构可视化

本文档提供 DreamWeaver 项目的可视化架构图。

---

## 1. 系统总体架构

```mermaid
graph TB
    subgraph "前端层"
        A[React 前端]
        A1[创作控制台]
        A2[实时预览]
        A3[Agent 状态监控]
    end
    
    subgraph "API 网关层"
        B[Nginx]
        B1[认证/授权]
        B2[限流/熔断]
        B3[负载均衡]
    end
    
    subgraph "应用服务层"
        C[Java Service<br/>Spring Boot]
        C1[用户管理]
        C2[小说元数据]
        C3[审计日志]
        
        D[Python AI Service<br/>FastAPI + LangGraph]
        D1[Agent 工作流]
        D2[Context Manager]
        D3[Memory Manager]
        D4[Model Provider]
    end
    
    subgraph "数据层"
        E[(PostgreSQL)]
        F[(Redis)]
        G[Object Storage]
    end
    
    A -->|HTTPS/SSE| B
    B --> C
    B --> D
    C --> E
    C --> F
    D --> E
    D --> F
    D --> G
```

---

## 2. Agent 工作流状态机

```mermaid
stateDiagram-v2
    [*] --> LoadRuntimeContext
    LoadRuntimeContext --> NovelContext
    NovelContext --> PlanChapter
    PlanChapter --> GenerateDraft
    GenerateDraft --> CheckConsistency
    
    CheckConsistency --> Review: 发现问题
    CheckConsistency --> Commit: 无问题
    
    Review --> Rewrite: 分数低
    Review --> Commit: 分数高
    
    Rewrite --> Review
    
    Commit --> [*]
```

---

## 3. 结构化记忆系统

```mermaid
graph LR
    subgraph "四层记忆结构"
        A[Timeline<br/>时间线]
        B[Character Graph<br/>人物关系图]
        C[Foreshadow Memory<br/>伏笔记忆]
        D[World State<br/>世界状态]
    end
    
    subgraph "压缩流水线"
        E[原始章节<br/>3000字]
        F[事件抽取]
        G[人物状态提取]
        H[摘要生成]
        I[结构化存储<br/>~1000字]
    end
    
    E --> F
    F --> G
    G --> H
    H --> I
    
    I --> A
    I --> B
    I --> C
    I --> D
```

---

## 4. Checkpoint 恢复机制

```mermaid
sequenceDiagram
    participant User
    participant API
    participant LangGraph
    participant PostgreSQL
    
    User->>API: 启动章节生成
    API->>LangGraph: invoke(initial_state)
    
    loop 每个节点执行后
        LangGraph->>PostgreSQL: 保存 Checkpoint
    end
    
    Note over LangGraph: 网络中断/服务重启
    
    User->>API: 恢复任务
    API->>LangGraph: invoke(None, thread_id)
    LangGraph->>PostgreSQL: 加载最新 Checkpoint
    PostgreSQL-->>LangGraph: 返回状态快照
    LangGraph->>LangGraph: 从中断点继续执行
    LangGraph-->>API: 返回结果
    API-->>User: 完成
```

---

## 5. 多模型路由策略

```mermaid
graph TD
    A[Task 请求] --> B{任务类型?}
    
    B -->|Context 加载| C[Claude-3.5-Sonnet<br/>中文理解好]
    B -->|Chapter 规划| D[GPT-4-Turbo<br/>推理能力强]
    B -->|Draft 生成| E[Claude-3.5-Sonnet-200k<br/>长文本窗口]
    B -->|一致性检查| F[GPT-3.5-Turbo<br/>成本低]
    B -->|质量评审| G[Claude-3-Opus<br/>质量高]
    
    C --> H[OpenRouter]
    D --> H
    E --> H
    F --> H
    G --> H
    
    H -->|主模型失败| I{Fallback}
    I -->|重试| H
    I -->|切换备用| J[备用模型]
```

---

## 6. 数据流图

```mermaid
graph LR
    A[用户输入] --> B[API Gateway]
    B --> C[Python AI Service]
    
    C --> D{Context Agent}
    D --> E[(PostgreSQL<br/>读取历史章节)]
    D --> F[(Redis<br/>读取缓存)]
    E --> D
    F --> D
    
    D --> G[Structured Memory]
    G --> H[Timeline]
    G --> I[Character Graph]
    G --> J[Foreshadow]
    G --> K[World State]
    
    H --> L[Planner Agent]
    I --> L
    J --> L
    K --> L
    
    L --> M[Writer Agent]
    M -->|Token Stream| N[SSE 推送]
    N --> O[前端实时显示]
    
    M --> P[Consistency Agent]
    P --> Q[Reviewer Agent]
    Q --> R[Commit]
    R --> S[(PostgreSQL<br/>保存章节)]
    R --> T[(OSS<br/>保存内容)]
```

---

## 7. 部署架构（生产环境）

```mermaid
graph TB
    subgraph "云负载均衡"
        A[Load Balancer]
    end
    
    subgraph "Kubernetes 集群"
        B[Ingress<br/>Nginx]
        
        subgraph "Java Service"
            C1[Pod 1]
            C2[Pod 2]
            C3[Pod 3]
        end
        
        subgraph "Python AI Service"
            D1[Pod 1]
            D2[Pod 2]
            D3[Pod 3]
        end
    end
    
    subgraph "托管服务"
        E[(PostgreSQL<br/>主从复制)]
        F[(Redis<br/>集群模式)]
        G[Object Storage<br/>OSS/S3]
    end
    
    subgraph "监控"
        H[Prometheus]
        I[Grafana]
        J[日志收集]
    end
    
    A --> B
    B --> C1
    B --> C2
    B --> C3
    B --> D1
    B --> D2
    B --> D3
    
    C1 --> E
    C2 --> E
    C3 --> E
    D1 --> E
    D2 --> E
    D3 --> E
    
    C1 --> F
    C2 --> F
    C3 --> F
    D1 --> F
    D2 --> F
    D3 --> F
    
    D1 --> G
    D2 --> G
    D3 --> G
    
    C1 --> H
    C2 --> H
    C3 --> H
    D1 --> H
    D2 --> H
    D3 --> H
    
    H --> I
    H --> J
```

---

## 8. 时序图：完整章节生成流程

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant API
    participant Context
    participant Planner
    participant Writer
    participant Consistency
    participant Reviewer
    participant DB
    
    User->>Frontend: 点击"生成章节"
    Frontend->>API: POST /chapters/generate-stream
    API->>Context: 加载上下文
    Context->>DB: 查询历史章节
    DB-->>Context: 返回数据
    Context->>Context: 构建结构化记忆
    Context-->>API: novel_context
    
    API->>Planner: 规划章节
    Planner->>Planner: LLM 推理
    Planner-->>API: chapter_outline
    
    API->>Writer: 生成草稿
    loop Token 流式输出
        Writer->>API: Token chunk
        API->>Frontend: SSE: token event
        Frontend->>User: 实时显示
    end
    Writer-->>API: generated_draft
    
    API->>Consistency: 一致性检查
    Consistency->>DB: 查询记忆数据
    DB-->>Consistency: 人物/世界观/伏笔
    Consistency->>Consistency: 检测冲突
    Consistency-->>API: consistency_report
    
    alt 发现问题
        API->>Reviewer: 评审
        Reviewer->>Reviewer: 质量评分
        Reviewer-->>API: review_report
        
        alt 分数低
            API->>Writer: 重写
            Writer-->>API: 更新 draft
            API->>Reviewer: 再次评审
        end
    end
    
    API->>DB: 保存章节
    DB-->>API: 确认
    API->>Frontend: SSE: done event
    Frontend->>User: 显示完成
```

---

## 9. 成本优化流程

```mermaid
graph TD
    A[任务到达] --> B{任务复杂度分析}
    
    B -->|高复杂度| C[高端模型<br/>GPT-4/Claude-3-Opus]
    B -->|中复杂度| D[中端模型<br/>Claude-3.5-Sonnet]
    B -->|低复杂度| E[低端模型<br/>GPT-3.5-Turbo]
    
    C --> F{Token 数预估}
    D --> F
    E --> F
    
    F -->|<2000 tokens| G[直接调用]
    F -->|2000-5000 tokens| H[上下文压缩]
    F -->|>5000 tokens| I[结构化记忆]
    
    G --> J[成本记录]
    H --> J
    I --> J
    
    J --> K{月度成本监控}
    K -->|超预算| L[降级策略]
    K -->|正常| M[继续]
    
    L --> N[切换低成本模型]
    N --> M
```

---

## 10. 技术演进路线图

```mermaid
gantt
    title DreamWeaver 技术演进路线
    dateFormat  YYYY-MM-DD
    section Phase 1: MVP
    核心 Agent 工作流           :2026-06-04, 30d
    基础记忆系统               :2026-06-20, 20d
    单模型支持                 :2026-06-25, 15d
    基础 Checkpoint            :2026-07-01, 14d
    
    section Phase 2: 优化
    多模型接入                 :2026-07-15, 10d
    上下文压缩优化             :2026-07-20, 15d
    SSE 流式输出               :2026-07-25, 10d
    性能优化                   :2026-08-01, 14d
    
    section Phase 3: 增强
    小说技能库                 :2026-08-15, 30d
    高级伏笔管理               :2026-09-01, 20d
    人工介入机制               :2026-09-10, 20d
    监控告警                   :2026-09-20, 15d
```

---

## 图例说明

### 节点类型
- 🟦 **蓝色方框**: 服务/组件
- 🟨 **黄色菱形**: 决策点
- 🟩 **绿色圆角**: 数据存储
- 🟪 **紫色圆形**: 外部系统

### 连接类型
- **实线箭头**: 同步调用
- **虚线箭头**: 异步调用
- **双向箭头**: 双向通信

---

## 如何查看图表

本文档使用 Mermaid 语法编写图表。可以通过以下方式查看：

1. **GitHub**: 直接在 GitHub 上查看（自动渲染 Mermaid）
2. **VS Code**: 安装 Mermaid 插件
3. **在线工具**: [Mermaid Live Editor](https://mermaid.live/)
4. **Markdown 编辑器**: Typora、Mark Text 等支持 Mermaid

---

## 相关文档

- [系统架构设计文档](./system-architecture.md)
- [技术选型总结](./tech-stack.md)
- [架构决策记录 (ADR)](./adr/)

---

**最后更新**: 2026-06-04
