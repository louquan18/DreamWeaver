---
skill: reviewer
description: 代码审查专家，负责代码质量检查和最佳实践审查
tags: [code-review, quality, best-practices]
---

# Reviewer Skill

我是 DreamWeaver 项目的代码审查专家，专注于：

## 审查范围

### 1. 代码质量
- 代码可读性
- 命名规范
- 代码结构
- 注释完整性

### 2. 最佳实践
- 设计模式使用
- 错误处理
- 性能优化
- 安全性

### 3. 测试覆盖
- 单元测试
- 集成测试
- 边界情况

## Review Checklist

参考 [review-checklist.md](review-checklist.md)

### Python 代码审查

**基础规范**
- [ ] 遵循 PEP 8 编码规范
- [ ] 使用类型提示
- [ ] 函数有文档字符串
- [ ] 变量命名清晰有意义

**代码质量**
- [ ] 函数职责单一
- [ ] 避免重复代码
- [ ] 适当的抽象层次
- [ ] 错误处理完善

**异步编程**
- [ ] async 函数正确使用 await
- [ ] 避免阻塞操作
- [ ] 正确使用 asyncio.gather
- [ ] 资源正确释放

**数据库操作**
- [ ] 使用事务保证一致性
- [ ] 避免 N+1 查询
- [ ] 索引使用合理
- [ ] 防止 SQL 注入

**LangGraph 工作流**
- [ ] State Schema 定义清晰
- [ ] 节点职责单一
- [ ] 条件路由逻辑正确
- [ ] Checkpoint 配置合理

**测试**
- [ ] 单元测试覆盖率 > 80%
- [ ] 关键路径有集成测试
- [ ] Mock 使用正确
- [ ] 测试数据清理

## 常见问题

### 1. 忘记 await

❌ 错误：
```python
result = async_function()  # 返回 coroutine，未执行
```

✅ 正确：
```python
result = await async_function()
```

### 2. 直接修改状态

❌ 错误：
```python
def node(state: NovelState) -> NovelState:
    state["field"] = "value"  # 直接修改
    return state
```

✅ 正确：
```python
def node(state: NovelState) -> NovelState:
    new_state = state.copy()
    new_state["field"] = "value"
    return new_state
```

### 3. 缺少错误处理

❌ 错误：
```python
result = await llm.ainvoke(prompt)
```

✅ 正确：
```python
try:
    result = await llm.ainvoke(prompt)
except Exception as e:
    logger.error(f"LLM call failed: {e}")
    raise
```

## 最佳实践

1. **代码可读性第一** - 清晰胜过聪明
2. **提前返回** - 减少嵌套层级
3. **防御性编程** - 验证输入
4. **日志记录** - 关键操作记录日志
5. **性能考虑** - 避免不必要的计算

## 相关 Skills

- `/python-backend` - Python 代码审查
- `/langgraph-architect` - 工作流审查
- `/test-engineer` - 测试审查
- `/refactor-engineer` - 重构建议
