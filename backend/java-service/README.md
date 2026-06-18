# DreamWeaver Java Service

Java Service 是 DreamWeaver 面向前端的业务后端，目标技术栈为 Spring Boot 3.x + Spring Data JPA。

## 职责边界

- 小说、章节、生成任务等业务 API。
- 生成历史查询与生成结果采用。
- 用户、权限、审计日志。
- 对内调用 Python AI Service 执行 LangGraph 工作流。

Python AI Service 长期只负责 AI 工作流、上下文压缩、模型路由、Checkpoint 和生成结果返回。

## 当前目录结构

```text
src/main/java/com/dreamweaver/
├── DreamWeaverJavaServiceApplication.java
├── audit/
├── client/
├── config/
├── controller/
├── dto/
├── entity/
├── repository/
├── security/
└── service/
```

## 本地运行

```bash
./mvnw spring-boot:run
```

Windows PowerShell:

```powershell
.\mvnw.cmd spring-boot:run
```

默认端口：`8080`

健康检查：

```text
GET /api/health
GET /actuator/health
```

## P0 API

```text
POST /api/stories
GET  /api/stories
GET  /api/stories/{storyId}

POST /api/stories/{storyId}/chapters
GET  /api/stories/{storyId}/chapters
GET  /api/stories/{storyId}/chapters/{chapterId}

POST /api/stories/{storyId}/chapters/{chapterId}/generations
GET  /api/stories/{storyId}/chapters/{chapterId}/generations
GET  /api/stories/{storyId}/chapters/{chapterId}/generations/{generationId}
GET  /api/stories/{storyId}/chapters/{chapterId}/generations/{generationId}/events
POST /api/stories/{storyId}/chapters/{chapterId}/generations/{generationId}/adopt
```

当前 `POST generations` 创建 Java 业务侧生成任务记录；`GET .../events` 由 Java 代理 Python AI Service 的 SSE，并在收到 `done` / `error` 时写回 `chapter_generations`。`autoAdopt=true` 时会同步更新 `chapters.content`。
