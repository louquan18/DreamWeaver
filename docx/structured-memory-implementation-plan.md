# 结构化记忆上下文压缩实施计划

**状态**: Draft  
**来源设计**: `.docs/p2-t4-structured-memory-context-compression-design.md`  
**目标**: 将当前“最近章节全文上下文”为主的写作链路，升级为“确认后的结构化长期记忆 + 短期章节摘要 + 按需补充召回”的上下文系统。  
**推荐执行顺序**: Phase 1 -> Phase 2 -> Phase 3 -> Phase 4

---

## 1. 总体交付物

| 阶段 | 目标 | 任务文档 |
| --- | --- | --- |
| Phase 1 | 打通正式长期记忆 apply 与读取闭环 | `p2-t4-phase-1-memory-apply-and-read-context.md` |
| Phase 2 | 压缩 `recentChapters`，引入章节摘要 | `p2-t4-phase-2-recent-chapter-summary-compression.md` |
| Phase 3 | 草稿生成接入结构化记忆上下文 | `p2-t4-phase-3-draft-structured-memory-context.md` |
| Phase 4 | 引入 `additionalMemory` 动态补充召回 | `p2-t4-phase-4-additional-memory-retrieval.md` |

---

## 2. 当前基线

当前 Java -> Python 的有效历史上下文主要来自：

- 最近 3 章完整正文 `recentChapters[].content`
- `story`
- `chapter`
- `blueprint`
- `confirmedOutline`
- 当前确认正文 `confirmedDraft`

当前已经预留但未充分使用的字段：

- `timeline`
- `characters`
- `world`
- `foreshadows`
- `additionalMemory`
- `existingMemory`

当前主要缺口：

1. `MemoryChangeSet` 确认后没有真正应用到正式长期记忆。
2. `existingMemory` 当前固定为空对象。
3. 中纲生成 DTO 虽有结构化字段，Java 当前传空列表。
4. 草稿生成 DTO 当前没有结构化记忆字段。
5. `recentChapters` 仍传最近 3 章全文，缺少摘要压缩策略。

---

## 3. 目标上下文结构

后续 Java 组装给 Python 的上下文应逐步收敛为：

```json
{
  "story": {},
  "chapter": {},
  "blueprint": {},
  "confirmedOutline": {},
  "recentChapters": [],
  "timeline": [],
  "characters": [],
  "world": [],
  "foreshadows": [],
  "additionalMemory": [],
  "contextMetadata": {
    "version": 1,
    "policy": "structured-memory-v1",
    "assembledAt": "2026-06-26T00:00:00Z",
    "limits": {
      "recentFullTextChapters": 1,
      "recentSummaryChapters": 5,
      "timeline": 20,
      "characters": 12,
      "foreshadows": 10,
      "additionalMemory": 8
    }
  }
}
```

---

## 4. 执行原则

1. **先闭环，再优化**：先让确认后的记忆能被下一章读取，再做 token 压缩和检索增强。
2. **确认事实优先**：`blueprint.lockedFacts`、`confirmedOutline`、正式长期记忆优先级高于历史正文和补充召回。
3. **pending 不入上下文**：未确认的 `MemoryChangeSet` 不得进入正式生成上下文。
4. **短期全文有限**：只保留最近 1 章全文或结尾片段，更早章节使用摘要和结构化记忆。
5. **可追溯**：长期记忆必须记录来源章节、来源 generation、证据文本或 hash。
6. **可回滚**：apply 失败时章节不能冻结，change set 保持 pending。

---

## 5. 推荐分支与提交粒度

建议按阶段分别提交：

1. `feat(memory): apply confirmed memory changes to official snapshot`
2. `feat(context): assemble structured memory for outline generation`
3. `feat(context): compress recent chapter context with summaries`
4. `feat(draft): pass structured memory to draft generation`
5. `feat(memory): add additional memory retrieval context`

每个阶段必须配套测试；不要把四个阶段合并成一个大提交。

---

## 6. 最小验收链路

必须能跑通：

```text
第 1 章生成正文
  -> 确认正文
  -> 抽取记忆
  -> 作者确认记忆
  -> 章节冻结
  -> 创建第 2 章
  -> 生成中纲
```

验收点：

1. 第 2 章中纲请求包含第 1 章确认后的 timeline。
2. 第 2 章中纲请求包含第 1 章确认后更新的人物状态。
3. 第 2 章中纲请求包含 open 伏笔。
4. `existingMemory` 不再是空对象。
5. `recentChapters` 不再默认传 3 章完整正文。

---

## 7. 文档清单

- `p2-t4-phase-1-memory-apply-and-read-context.md`
- `p2-t4-phase-2-recent-chapter-summary-compression.md`
- `p2-t4-phase-3-draft-structured-memory-context.md`
- `p2-t4-phase-4-additional-memory-retrieval.md`

