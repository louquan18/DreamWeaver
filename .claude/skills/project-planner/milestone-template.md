# Milestone [编号]: [里程碑名称]

**目标**: [一句话描述里程碑目标]  
**开始日期**: YYYY-MM-DD  
**目标完成日期**: YYYY-MM-DD  
**实际完成日期**: YYYY-MM-DD（完成后填写）  
**状态**: [未开始 | 进行中 | 已完成 | 已延期]  
**负责人**: [负责人姓名]

---

## 1. 里程碑概述

### 1.1 目标描述
[详细描述此里程碑要达成的目标，解决什么问题，带来什么价值]

示例：
> 完成 LangGraph 工作流核心开发，实现 Context/Planner/Writer 三个核心 Agent，建立基础的章节生成能力，支持状态持久化和断点恢复。

### 1.2 成功标准
- [ ] 标准 1: [可量化的成功标准]
- [ ] 标准 2: [可验证的成功标准]
- [ ] 标准 3: [可测试的成功标准]

示例：
- [ ] LangGraph 工作流可端到端运行，生成完整章节
- [ ] Checkpoint 机制实现，异常中断后可恢复
- [ ] 单元测试覆盖率 > 80%
- [ ] 生成一篇 3000 字章节的时间 < 5 分钟

### 1.3 不包含的内容（Out of Scope）
[明确列出此里程碑不包含的内容，避免范围蔓延]

示例：
- ❌ 一致性检查功能（Milestone 4）
- ❌ 评审与重写功能（Milestone 4）
- ❌ 前端界面开发（Milestone 8）
- ❌ 多模型动态路由（Milestone 5）

---

## 2. 交付物清单

### 2.1 代码交付物
- [ ] [模块/功能 1]
  - 文件路径: `path/to/file.py`
  - 描述: [功能描述]
- [ ] [模块/功能 2]
  - 文件路径: `path/to/file.py`
  - 描述: [功能描述]

示例：
- [ ] NovelState Schema 定义
  - 文件路径: `backend/python-ai/src/schemas/state.py`
  - 描述: 定义 LangGraph 工作流状态结构
- [ ] Context Agent 实现
  - 文件路径: `backend/python-ai/src/agents/context_agent.py`
  - 描述: 历史章节检索、人物状态提取、时间线构建
- [ ] Planner Agent 实现
  - 文件路径: `backend/python-ai/src/agents/planner_agent.py`
  - 描述: 章节规划、冲突设计、剧情推进
- [ ] Writer Agent 实现
  - 文件路径: `backend/python-ai/src/agents/writer_agent.py`
  - 描述: 根据规划生成章节草稿（流式输出）

### 2.2 测试交付物
- [ ] 单元测试
  - 覆盖率目标: > 80%
  - 测试文件: `tests/unit/test_*.py`
- [ ] 集成测试
  - 测试场景: [列举关键测试场景]
  - 测试文件: `tests/integration/test_*.py`

### 2.3 文档交付物
- [ ] API 文档
- [ ] 开发者文档
- [ ] 架构文档更新
- [ ] README 更新

---

## 3. 关键任务列表

### 3.1 核心任务（Critical Path）

#### Task 1: [任务名称] - [优先级 P0/P1/P2]
- **描述**: [任务详细描述]
- **验收标准**: [如何验证完成]
- **工作量**: [X 天]
- **依赖**: [依赖的其他任务]
- **负责人**: [负责人]
- **状态**: [未开始 | 进行中 | 已完成]

示例：
#### Task 1: 定义 NovelState Schema - P0
- **描述**: 定义 LangGraph 工作流的状态结构，包含 story_id, chapter_id, novel_context, chapter_outline, generated_draft 等字段
- **验收标准**: 
  - Schema 定义完整，包含所有必需字段
  - 通过类型检查（mypy）
  - 有完整的文档注释
- **工作量**: 1 天
- **依赖**: 无
- **负责人**: [开发者]
- **状态**: 未开始

#### Task 2: [任务名称] - [优先级]
[同上格式]

### 3.2 支持任务（Supporting Tasks）

#### Task N: [任务名称] - [优先级]
[同上格式]

---

## 4. 依赖关系

### 4.1 外部依赖
[列出依赖的外部资源、服务、团队]

示例：
- 数据库 Schema 已完成（Milestone 1）
- LangChain/LangGraph 库安装配置（Milestone 1）
- OpenRouter API Key 已申请

### 4.2 内部依赖
[列出任务之间的依赖关系]

```
Task 1 (NovelState Schema)
    ↓
Task 2 (Context Agent) ← Task 3 (Planner Agent) ← Task 4 (Writer Agent)
    ↓                          ↓                        ↓
Task 5 (Workflow 编排)
    ↓
Task 6 (Checkpoint 机制)
    ↓
Task 7 (单元测试)
```

---

## 5. 资源规划

### 5.1 人力资源
| 角色 | 人数 | 工作量 |
|------|------|--------|
| 后端开发 | 1-2 人 | 3 周 |
| 测试工程师 | 1 人 | 0.5 周 |
| 架构师 | 1 人 | 0.5 周（评审） |

### 5.2 技术资源
- Python 3.10+
- LangChain 0.1.0+
- LangGraph 0.1.0+
- PostgreSQL 14+
- Redis 7+

### 5.3 预算（可选）
- 开发成本: [估算]
- 云服务成本: [估算]
- LLM API 成本: [估算]

---

## 6. 风险评估

### 6.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 | 负责人 |
|------|------|------|----------|--------|
| LangGraph 框架不熟悉 | 高 | 中 | 提前学习官方文档，编写 Demo | [负责人] |
| Checkpoint 机制复杂 | 中 | 中 | 参考官方示例，逐步实现 | [负责人] |
| 流式输出技术难点 | 中 | 低 | 使用 LangGraph astream_events | [负责人] |

### 6.2 进度风险

| 风险 | 影响 | 概率 | 缓解措施 | 负责人 |
|------|------|------|----------|--------|
| 任务工作量估算不足 | 中 | 中 | 预留 20% 缓冲时间 | [负责人] |
| 依赖任务延期 | 高 | 低 | 提前识别关键路径 | [负责人] |

### 6.3 业务风险

| 风险 | 影响 | 概率 | 缓解措施 | 负责人 |
|------|------|------|----------|--------|
| 生成内容质量不达预期 | 高 | 中 | 后续里程碑优化 | [负责人] |

---

## 7. 时间线

```
Week 1:
  Day 1-2: Task 1 - NovelState Schema
  Day 3-5: Task 2 - Context Agent

Week 2:
  Day 1-3: Task 3 - Planner Agent
  Day 4-5: Task 4 - Writer Agent

Week 3:
  Day 1-2: Task 5 - Workflow 编排
  Day 3-4: Task 6 - Checkpoint 机制
  Day 5: Task 7 - 单元测试 + 文档
```

---

## 8. 验证与测试

### 8.1 单元测试
- [ ] Context Agent 测试
- [ ] Planner Agent 测试
- [ ] Writer Agent 测试
- [ ] Checkpoint 机制测试

### 8.2 集成测试
- [ ] 端到端工作流测试（输入题材 → 生成章节）
- [ ] 异常中断恢复测试
- [ ] 并发场景测试

### 8.3 性能测试
- [ ] 单章生成时间 < 5 分钟
- [ ] Checkpoint 恢复时间 < 10 秒
- [ ] 内存占用 < 2GB

---

## 9. 进度跟踪

### 9.1 每日进度（Daily Updates）

**YYYY-MM-DD**
- 完成: [完成的任务]
- 进行中: [正在进行的任务]
- 阻塞: [遇到的问题]
- 明日计划: [明天的计划]

**YYYY-MM-DD**
[同上]

### 9.2 每周总结（Weekly Summary）

**Week 1 (YYYY-MM-DD ~ YYYY-MM-DD)**
- 完成任务: [列表]
- 进度: [X%]
- 风险: [识别的风险]
- 下周计划: [计划]

---

## 10. 验收报告（Acceptance Report）

**完成日期**: YYYY-MM-DD  
**验收人**: [验收人姓名]  
**验收结果**: [通过 | 部分通过 | 不通过]

### 10.1 交付物检查
- [ ] 所有代码交付物已完成
- [ ] 单元测试覆盖率达标
- [ ] 集成测试通过
- [ ] 文档完善

### 10.2 成功标准检查
- [ ] 标准 1: [检查结果]
- [ ] 标准 2: [检查结果]
- [ ] 标准 3: [检查结果]

### 10.3 遗留问题
| 问题 | 严重性 | 计划解决时间 |
|------|--------|--------------|
| [问题描述] | 高/中/低 | Milestone X |

### 10.4 经验总结
**做得好的地方**:
- [总结 1]
- [总结 2]

**需要改进的地方**:
- [总结 1]
- [总结 2]

**教训（Lessons Learned）**:
- [教训 1]
- [教训 2]

---

## 附录

### 附录 A: 相关文档
- [架构设计文档](../../docs/architecture/)
- [API 文档](../../docs/api/)
- [相关 Issues](../../issues/)

### 附录 B: 会议记录
- [Milestone Kickoff 会议](../../docs/meetings/milestone-X-kickoff.md)
- [进度评审会议](../../docs/meetings/milestone-X-review.md)
