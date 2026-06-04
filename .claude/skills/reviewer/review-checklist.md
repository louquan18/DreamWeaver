# Review Checklist - 代码审查清单

## Python 代码审查

### 基础规范 ✓

- [ ] **PEP 8 编码规范**
  - 缩进使用 4 个空格
  - 行长度不超过 120 字符
  - 导入语句分组（标准库/第三方/本地）
  
- [ ] **类型提示**
  - 函数参数有类型提示
  - 函数返回值有类型提示
  - 复杂类型使用 typing 模块
  
- [ ] **文档字符串**
  - 所有公共函数有 docstring
  - 说明参数、返回值、异常
  - 使用 Google/NumPy 风格
  
- [ ] **命名规范**
  - 类名使用 PascalCase
  - 函数/变量使用 snake_case
  - 常量使用 UPPER_SNAKE_CASE
  - 私有成员使用下划线前缀

### 代码质量 ✓

- [ ] **单一职责原则**
  - 每个函数只做一件事
  - 函数长度 < 50 行
  - 类职责明确
  
- [ ] **DRY 原则**
  - 无重复代码
  - 公共逻辑已提取
  
- [ ] **代码可读性**
  - 逻辑清晰易懂
  - 避免过深嵌套（< 4 层）
  - 使用提前返回减少嵌套
  
- [ ] **注释合理**
  - 复杂逻辑有注释说明
  - 避免无意义注释
  - 注释与代码同步更新

### 错误处理 ✓

- [ ] **异常捕获**
  - 关键操作有异常处理
  - 异常类型具体，避免裸 except
  - 记录错误日志
  
- [ ] **资源清理**
  - 文件/连接正确关闭
  - 使用 context manager
  
- [ ] **输入验证**
  - 验证外部输入
  - 使用 Pydantic 验证

### 异步编程 ✓

- [ ] **await 使用正确**
  - async 函数正确使用 await
  - 避免忘记 await
  
- [ ] **并发控制**
  - 使用 asyncio.gather 并发执行
  - 避免阻塞操作
  
- [ ] **资源管理**
  - 异步资源正确释放
  - 使用 async with

### 数据库操作 ✓

- [ ] **事务管理**
  - 写操作使用事务
  - 事务边界合理
  
- [ ] **查询优化**
  - 避免 N+1 查询
  - 使用 selectinload/joinedload
  - 合理使用索引
  
- [ ] **SQL 注入防护**
  - 使用参数化查询
  - 避免字符串拼接

### LangGraph 工作流 ✓

- [ ] **State Schema**
  - 使用 TypedDict 定义
  - 字段有类型提示
  - 有文档注释
  
- [ ] **节点实现**
  - 节点职责单一
  - 返回新状态（不修改输入）
  - 有错误处理
  
- [ ] **条件路由**
  - 路由逻辑清晰
  - 覆盖所有分支
  
- [ ] **Checkpoint 配置**
  - 生产环境使用持久化
  - thread_id 设置合理

### 测试 ✓

- [ ] **单元测试**
  - 覆盖率 > 80%
  - 测试命名清晰
  - 使用 AAA 模式
  
- [ ] **集成测试**
  - 关键路径有测试
  - 端到端测试通过
  
- [ ] **Mock 使用**
  - 外部依赖已 Mock
  - Mock 使用正确
  
- [ ] **测试数据清理**
  - 使用 fixture 管理
  - 测试后清理数据

### 性能 ✓

- [ ] **数据库查询**
  - 避免全表扫描
  - 使用批量操作
  
- [ ] **缓存策略**
  - 热数据使用缓存
  - TTL 设置合理
  
- [ ] **内存使用**
  - 避免内存泄漏
  - 大数据分批处理

### 安全 ✓

- [ ] **认证授权**
  - API 需要认证
  - 权限检查完整
  
- [ ] **敏感信息**
  - 不在代码中硬编码密钥
  - 使用环境变量
  
- [ ] **输入验证**
  - 验证用户输入
  - 防止注入攻击

---

## FastAPI 特定检查

- [ ] **路由设计**
  - URL 命名规范（RESTful）
  - HTTP 方法使用正确
  - 响应模型定义
  
- [ ] **依赖注入**
  - 使用 Depends 注入依赖
  - 数据库会话正确管理
  
- [ ] **响应码**
  - 使用正确的 HTTP 状态码
  - 错误响应格式统一

---

## 代码示例

### ✅ 好的代码

```python
async def create_story(
    story_data: StoryCreate,
    user_id: str,
    db: AsyncSession
) -> Story:
    """
    创建小说
    
    Args:
        story_data: 小说数据
        user_id: 用户 ID
        db: 数据库会话
        
    Returns:
        Story: 创建的小说对象
        
    Raises:
        ValueError: 数据验证失败
    """
    try:
        # 验证输入
        if not story_data.title.strip():
            raise ValueError("Title cannot be empty")
        
        # 创建小说
        story = Story(**story_data.dict(), user_id=user_id)
        db.add(story)
        await db.commit()
        await db.refresh(story)
        
        return story
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create story: {e}")
        raise
```

### ❌ 不好的代码

```python
async def create_story(data, uid, db):  # ❌ 缺少类型提示
    # ❌ 缺少文档字符串
    story = Story(**data, user_id=uid)
    db.add(story)
    await db.commit()  # ❌ 缺少异常处理
    return story  # ❌ 未刷新对象
```

---

## 审查流程

1. **自动检查** - 运行 linter (ruff/pylint)
2. **类型检查** - 运行 mypy
3. **测试** - 运行测试套件
4. **人工审查** - 逐条检查 checklist
5. **反馈** - 提供具体改进建议
