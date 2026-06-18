# ADR-004: 多模型适配与动态路由策略

**日期**: 2026-06-04  
**状态**: 已接受  
**决策者**: System Architect  
**替代方案**: N/A

---

## 背景（Context）

DreamWeaver 的 Agent 工作流包含多种不同类型的任务：

| 任务类型 | 特点 | 示例 Agent |
|---------|------|-----------|
| 推理规划 | 需要复杂推理，输出结构化 | Planner Agent |
| 长文本生成 | 需要大窗口，保持连贯性 | Writer Agent |
| 简单分类 | 规则明确，成本敏感 | Consistency Agent |
| 质量评审 | 需要高质量输出 | Reviewer Agent |
| 信息抽取 | 中文优化，结构化输出 | Context Agent（事件抽取）|

**问题**：
1. **单一模型无法最优** - 没有一个模型在所有任务上都表现最好
2. **成本优化需求** - 简单任务使用高端模型浪费成本
3. **供应商风险** - 依赖单一供应商（如 OpenAI）有可用性风险
4. **灵活切换需求** - 需要根据场景快速切换模型

---

## 决策驱动因素（Decision Drivers）

1. **成本优化** - 根据任务复杂度选择合适价位的模型
2. **质量保证** - 关键任务使用高质量模型
3. **可用性** - 多供应商冗余，避免单点故障
4. **可扩展性** - 方便接入新模型
5. **可维护性** - 统一的模型调用接口

---

## 备选方案（Options Considered）

### 方案 1: 单一模型（Claude-3.5-Sonnet）

**描述**:  
所有任务都使用同一个模型。

```python
from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

async def call_llm(prompt: str) -> str:
    response = await client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text
```

**优点**:
- ✅ 实现简单
- ✅ 无需模型路由逻辑
- ✅ 一致的输出质量

**缺点**:
- ❌ 成本高（简单任务也用高端模型）
- ❌ 单点故障风险（依赖 Anthropic）
- ❌ 无法针对任务优化
- ❌ 供应商锁定

**月成本估算**（1000 章生成）:
- Context Agent: $50
- Planner Agent: $200
- Writer Agent: $500
- Consistency Agent: $100
- Reviewer Agent: $150
- **总计**: ~$1000/月

---

### 方案 2: 手动模型选择

**描述**:  
为每个 Agent 手动配置模型。

```python
# 配置文件
AGENT_MODELS = {
    "context": "claude-3-5-sonnet-20241022",
    "planner": "gpt-4-turbo",
    "writer": "claude-3-5-sonnet-20241022",
    "consistency": "gpt-3.5-turbo",
    "reviewer": "claude-3-opus-20240229"
}

async def call_llm_for_agent(agent_name: str, prompt: str) -> str:
    model = AGENT_MODELS[agent_name]
    
    if model.startswith("claude"):
        client = AsyncAnthropic(api_key=...)
        # ...
    elif model.startswith("gpt"):
        client = AsyncOpenAI(api_key=...)
        # ...
```

**优点**:
- ✅ 可以针对任务优化模型
- ✅ 成本可控
- ✅ 灵活性高

**缺点**:
- ❌ 需要为每个模型编写适配代码
- ❌ 配置分散，难以管理
- ❌ 切换模型需要修改代码
- ❌ 无统一接口

**月成本估算**（优化后）:
- Context Agent: $30 (Sonnet)
- Planner Agent: $150 (GPT-4)
- Writer Agent: $500 (Sonnet)
- Consistency Agent: $20 (GPT-3.5)
- Reviewer Agent: $200 (Opus)
- **总计**: ~$900/月（省 10%）

---

### 方案 3: OpenRouter 统一聚合

**描述**:  
使用 OpenRouter 作为统一的模型聚合层，支持 100+ 模型。

```python
import openai

# OpenRouter 提供 OpenAI 兼容接口
client = openai.AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

async def call_llm(model: str, prompt: str) -> str:
    response = await client.chat.completions.create(
        model=model,  # 如 "anthropic/claude-3.5-sonnet"
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 路由配置
MODEL_ROUTER = {
    "context": "anthropic/claude-3.5-sonnet",
    "planner": "openai/gpt-4-turbo",
    "writer": "anthropic/claude-3.5-sonnet:beta",
    "consistency": "openai/gpt-3.5-turbo",
    "reviewer": "anthropic/claude-3-opus"
}
```

**OpenRouter 特性**:
- 100+ 模型支持（OpenAI、Anthropic、Google、Meta、Mistral、国内模型）
- 统一 OpenAI 格式接口
- 自动 Fallback（主模型不可用时切换备用模型）
- 按需计费，无需多个 API Key
- 实时价格对比

**优点**:
- ✅ 统一接口（OpenAI 格式）
- ✅ 支持 100+ 模型
- ✅ 自动 Fallback
- ✅ 无需管理多个 API Key
- ✅ 灵活切换模型（改配置即可）
- ✅ 价格透明

**缺点**:
- ❌ 增加一层代理（延迟 +50-100ms）
- ❌ 依赖 OpenRouter 服务
- ❌ 价格略高于直连（代理费 ~5%）

**月成本估算**（优化后 + 代理费）:
- 总计: ~$945/月（省 5%，考虑代理费）

---

### 方案 4: 自建模型路由层 + LangChain

**描述**:  
使用 LangChain 的 Provider 抽象 + 自建路由层。

```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from abc import ABC, abstractmethod

class ModelRouter:
    def __init__(self):
        self.providers = {
            "openai": ChatOpenAI,
            "anthropic": ChatAnthropic,
            "google": ChatGoogleGenerativeAI
        }
        
        self.routing_config = {
            "context": ("anthropic", "claude-3-5-sonnet-20241022"),
            "planner": ("openai", "gpt-4-turbo"),
            "writer": ("anthropic", "claude-3-5-sonnet-20241022"),
            "consistency": ("openai", "gpt-3.5-turbo"),
            "reviewer": ("anthropic", "claude-3-opus-20240229")
        }
    
    def get_model(self, agent_name: str):
        provider, model = self.routing_config[agent_name]
        provider_class = self.providers[provider]
        return provider_class(model=model)

router = ModelRouter()

async def call_llm_for_agent(agent_name: str, prompt: str) -> str:
    model = router.get_model(agent_name)
    response = await model.ainvoke(prompt)
    return response.content
```

**优点**:
- ✅ 完全控制路由逻辑
- ✅ LangChain 生态集成
- ✅ 无代理延迟
- ✅ 价格最优（直连）

**缺点**:
- ❌ 需要管理多个 API Key
- ❌ 需要自己实现 Fallback
- ❌ 需要自己实现重试逻辑
- ❌ 维护成本高

**月成本估算**:
- 总计: ~$900/月（最优）

---

## 决策（Decision）

**选择**: 方案 3 - **OpenRouter 统一聚合**

**理由**:

1. **统一接口** - OpenAI 格式，代码简洁
2. **支持广泛** - 100+ 模型，包括国内模型（DeepSeek、Qwen）
3. **自动 Fallback** - 主模型不可用时自动切换
4. **开发效率** - 无需为每个 Provider 编写适配代码
5. **灵活性** - 修改配置即可切换模型，无需改代码
6. **可观测性** - OpenRouter 提供使用统计和成本分析

虽然有 ~5% 的代理费和 50-100ms 延迟，但考虑到开发效率和自动 Fallback，性价比最高。

**模型路由策略**:

| Agent | 模型 | 理由 | 月成本估算 |
|-------|------|------|-----------|
| Context Agent | Claude-3.5-Sonnet | 中文理解好，事件抽取准确 | $30 |
| Planner Agent | GPT-4-Turbo | 推理能力强 | $150 |
| Writer Agent | Claude-3.5-Sonnet-200k | 长文本窗口，写作质量高 | $500 |
| Consistency Agent | GPT-3.5-Turbo | 成本低，分类任务足够 | $20 |
| Reviewer Agent | Claude-3-Opus | 评审质量要求高 | $200 |
| Rewrite Agent | Claude-3.5-Sonnet | 写作质量 | $100 |
| **总计** | - | - | **~$1000/月** |

---

## 后果（Consequences）

### 正面影响
- ✅ 快速接入新模型（修改配置即可）
- ✅ 多供应商冗余（OpenAI、Anthropic、Google 等）
- ✅ 自动 Fallback（可用性提升）
- ✅ 代码简洁（统一 OpenAI 接口）
- ✅ 灵活实验不同模型组合

### 负面影响
- ⚠️ 代理延迟 +50-100ms
- ⚠️ 依赖 OpenRouter 服务
- ⚠️ 代理费 ~5%

### 风险与缓解措施

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| OpenRouter 服务中断 | 高 | 低 | 备用直连方案 |
| 代理延迟影响体验 | 中 | 低 | 监控延迟，必要时切换直连 |
| 成本超预算 | 中 | 中 | 成本监控 + 模型降级策略 |
| 某模型质量下降 | 中 | 中 | 定期评估 + 快速切换 |

---

## 技术债务（Technical Debt）

**债务 1**: 当前所有模型通过 OpenRouter，未来可能需要直连优化延迟
- **计划偿还**: 监控延迟，超过 200ms 时评估直连关键路径（Writer Agent）

**债务 2**: 模型路由策略静态配置，未来可能需要动态路由（基于负载、成本）
- **计划偿还**: MVP 后实现智能路由（根据成本/延迟/质量评分）

**债务 3**: 未实现模型质量监控和自动切换
- **计划偿还**: 实现质量评分系统，自动下线低质量模型

---

## 实施计划（Implementation Plan）

### 阶段 1: OpenRouter 集成（2 天）
- [ ] 注册 OpenRouter 账号
- [ ] 配置 API Key
- [ ] 实现统一调用接口
- [ ] 测试基础调用

**预计时间**: 2 天  
**负责人**: Python Backend Team

### 阶段 2: 模型路由配置（1 天）
- [ ] 定义路由配置（YAML/JSON）
- [ ] 实现配置加载
- [ ] 为每个 Agent 配置模型

**预计时间**: 1 天  
**负责人**: AI Team

### 阶段 3: Fallback 机制（2 天）
- [ ] 配置备用模型
- [ ] 实现自动切换逻辑
- [ ] 测试 Fallback

**预计时间**: 2 天  
**负责人**: Python Backend Team

### 阶段 4: 监控和优化（3 天）
- [ ] 集成成本监控
- [ ] 集成延迟监控
- [ ] 质量评估
- [ ] 告警配置

**预计时间**: 3 天  
**负责人**: DevOps + AI Team

---

## 实施示例

### 1. 配置文件

```yaml
# config/models.yaml
model_routing:
  context_agent:
    primary:
      provider: "anthropic/claude-3.5-sonnet"
      temperature: 0.3
      max_tokens: 2000
    fallback:
      - "openai/gpt-4-turbo"
  
  planner_agent:
    primary:
      provider: "openai/gpt-4-turbo"
      temperature: 0.7
      max_tokens: 1000
    fallback:
      - "anthropic/claude-3.5-sonnet"
  
  writer_agent:
    primary:
      provider: "anthropic/claude-3.5-sonnet:beta"  # 200k context
      temperature: 0.8
      max_tokens: 4000
    fallback:
      - "openai/gpt-4-turbo"
  
  consistency_agent:
    primary:
      provider: "openai/gpt-3.5-turbo"
      temperature: 0.2
      max_tokens: 500
    fallback:
      - "deepseek/deepseek-chat"  # 低成本备用
  
  reviewer_agent:
    primary:
      provider: "anthropic/claude-3-opus-20240229"
      temperature: 0.5
      max_tokens: 1500
    fallback:
      - "openai/gpt-4-turbo"
  
  rewrite_agent:
    primary:
      provider: "anthropic/claude-3.5-sonnet"
      temperature: 0.8
      max_tokens: 3000
    fallback:
      - "openai/gpt-4-turbo"
```

### 2. 模型路由器

```python
# src/models/router.py
import openai
import yaml
from typing import Optional, Dict, Any

class ModelRouter:
    """模型路由器"""
    
    def __init__(self, config_path: str):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.client = openai.AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
    
    async def call(
        self,
        agent_name: str,
        messages: list,
        **kwargs
    ) -> str:
        """调用模型（带 Fallback）"""
        
        agent_config = self.config["model_routing"][agent_name]
        
        # 尝试主模型
        try:
            return await self._call_model(
                agent_config["primary"],
                messages,
                **kwargs
            )
        except Exception as e:
            logger.warning(f"Primary model failed: {e}")
            
            # Fallback
            for fallback_model in agent_config.get("fallback", []):
                try:
                    logger.info(f"Trying fallback: {fallback_model}")
                    return await self._call_model(
                        {"provider": fallback_model},
                        messages,
                        **kwargs
                    )
                except Exception as e2:
                    logger.warning(f"Fallback {fallback_model} failed: {e2}")
                    continue
            
            raise Exception("All models failed")
    
    async def _call_model(
        self,
        model_config: Dict[str, Any],
        messages: list,
        **kwargs
    ) -> str:
        """实际调用模型"""
        
        response = await self.client.chat.completions.create(
            model=model_config["provider"],
            messages=messages,
            temperature=model_config.get("temperature", 0.7),
            max_tokens=model_config.get("max_tokens", 2000),
            **kwargs
        )
        
        return response.choices[0].message.content
    
    async def stream(
        self,
        agent_name: str,
        messages: list,
        **kwargs
    ):
        """流式调用"""
        
        agent_config = self.config["model_routing"][agent_name]
        model_config = agent_config["primary"]
        
        stream = await self.client.chat.completions.create(
            model=model_config["provider"],
            messages=messages,
            temperature=model_config.get("temperature", 0.7),
            max_tokens=model_config.get("max_tokens", 2000),
            stream=True,
            **kwargs
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

# 全局实例
router = ModelRouter("config/models.yaml")
```

### 3. Agent 使用示例

```python
# src/agents/planner_agent.py
from src.models.router import router

async def planner_agent(state: NovelState) -> NovelState:
    """章节规划 Agent"""
    
    prompt = f"""
    基于以下上下文，规划第 {state['chapter_id']} 章：
    
    {state['novel_context']}
    
    请输出：
    1. 章节目标
    2. 主要冲突
    3. 关键情节点
    """
    
    # 通过路由器调用（自动使用 GPT-4-Turbo）
    response = await router.call(
        agent_name="planner_agent",
        messages=[{"role": "user", "content": prompt}]
    )
    
    # 解析响应
    outline = parse_outline(response)
    
    state["chapter_outline"] = outline
    state["execution_history"].append("planner_agent")
    
    return state
```

### 4. 成本监控

```python
# src/monitoring/cost_tracker.py
from prometheus_client import Counter, Histogram

# Prometheus 指标
llm_calls_total = Counter(
    'llm_calls_total',
    'Total LLM calls',
    ['agent', 'model', 'status']
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total tokens used',
    ['agent', 'model', 'type']
)

llm_cost_total = Counter(
    'llm_cost_total',
    'Total cost in USD',
    ['agent', 'model']
)

async def track_llm_call(
    agent_name: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost: float,
    status: str
):
    """追踪 LLM 调用"""
    
    llm_calls_total.labels(
        agent=agent_name,
        model=model,
        status=status
    ).inc()
    
    llm_tokens_total.labels(
        agent=agent_name,
        model=model,
        type="input"
    ).inc(input_tokens)
    
    llm_tokens_total.labels(
        agent=agent_name,
        model=model,
        type="output"
    ).inc(output_tokens)
    
    llm_cost_total.labels(
        agent=agent_name,
        model=model
    ).inc(cost)
```

---

## 验证标准（Validation Criteria）

- [x] 支持 5+ 模型供应商
- [x] 统一调用接口（OpenAI 格式）
- [ ] Fallback 成功率 > 95%
- [ ] 代理延迟 < 100ms (P95)
- [ ] 成本监控实时更新
- [ ] 支持流式输出
- [ ] 配置热更新（无需重启）

---

## 参考资料（References）

- [OpenRouter 官网](https://openrouter.ai/)
- [OpenRouter 模型列表](https://openrouter.ai/models)
- [OpenRouter 定价](https://openrouter.ai/docs#pricing)
- [LangChain Multi-Provider](https://python.langchain.com/docs/integrations/chat/)

---

## 现状更新（Status Update · 2026-06-17）

> 本节为事实校正，不修改上方原始决策记录。

- **决策方向不变**：仍计划走 OpenAI 兼容接口聚合（OpenRouter / 本地部署等）。
- **实际现状**：当前实际接入的是**小米 MiMo 单一模型**，六个 Agent 在 `backend/python-ai/src/core/config.py:37-42` 全部配置为 `mimo-7b`；`models/provider.py` 提供"按 Agent 选模型 + 温度"机制，但无独立 `router.py`、无多 Provider 路由、无自动 Fallback。
- **校正"验证标准"**：上文「验证标准」中被勾选为 `[x]` 的两项（"支持 5+ 模型供应商""统一调用接口"）——统一 OpenAI 接口成立，但"5+ 供应商路由"**当前未实现**；下方成本估算表为规划假设，非实测。
- 权威状态见 [STATUS.md](../../STATUS.md) 第 5 节。

---

## 更新历史（Update History）

| 日期 | 修改内容 | 修改人 |
|------|----------|--------|
| 2026-06-04 | 初始版本 | System Architect |
| 2026-06-17 | 追加"现状更新"小节，校正单模型现状与误标完成项 | louquan |
