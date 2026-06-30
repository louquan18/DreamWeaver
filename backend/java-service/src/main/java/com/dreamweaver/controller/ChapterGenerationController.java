package com.dreamweaver.controller;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import com.dreamweaver.dto.ChapterGenerationCreateRequest;
import com.dreamweaver.dto.ChapterGenerationDetailResponse;
import com.dreamweaver.dto.ChapterGenerationSummaryResponse;
import com.dreamweaver.dto.ChapterResponse;
import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.ChapterGeneration;
import com.dreamweaver.service.AiDraftQualityClient;
import com.dreamweaver.service.ChapterGenerationService;
import com.dreamweaver.service.ChapterService;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import jakarta.validation.Valid;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

@RestController
@RequestMapping("/api/stories/{storyId}/chapters/{chapterId}/generations")
public class ChapterGenerationController {

    private final ChapterGenerationService generationService;
    private final ChapterService chapterService;
    private final AiDraftQualityClient aiDraftQualityClient;
    private final ObjectMapper objectMapper;
    private final String pythonAiBaseUrl;

    public ChapterGenerationController(
        ChapterGenerationService generationService,
        ChapterService chapterService,
        AiDraftQualityClient aiDraftQualityClient,
        ObjectMapper objectMapper,
        @Value("${dreamweaver.python-ai.base-url}") String pythonAiBaseUrl
    ) {
        this.generationService = generationService;
        this.chapterService = chapterService;
        this.aiDraftQualityClient = aiDraftQualityClient;
        this.objectMapper = objectMapper;
        this.pythonAiBaseUrl = pythonAiBaseUrl;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ChapterGenerationDetailResponse create(
        @PathVariable UUID storyId,
        @PathVariable UUID chapterId,
        @Valid @RequestBody ChapterGenerationCreateRequest request
    ) {
        var generation = generationService.create(storyId, chapterId, request);
        Chapter chapter = chapterService.get(storyId, chapterId);
        return ChapterGenerationDetailResponse.from(
            generation,
            chapter.getLastGenerationId()
        );
    }

    @GetMapping
    public List<ChapterGenerationSummaryResponse> list(
        @PathVariable UUID storyId,
        @PathVariable UUID chapterId
    ) {
        Chapter chapter = chapterService.get(storyId, chapterId);
        return generationService.list(storyId, chapterId).stream()
            .map(generation -> ChapterGenerationSummaryResponse.from(
                generation,
                chapter.getLastGenerationId()
            ))
            .toList();
    }

    @GetMapping("/{generationId}")
    public ChapterGenerationDetailResponse get(
        @PathVariable UUID storyId,
        @PathVariable UUID chapterId,
        @PathVariable UUID generationId
    ) {
        Chapter chapter = chapterService.get(storyId, chapterId);
        return ChapterGenerationDetailResponse.from(
            generationService.get(storyId, chapterId, generationId),
            chapter.getLastGenerationId()
        );
    }

    @PostMapping("/{generationId}/adopt")
    public ChapterResponse adopt(
        @PathVariable UUID storyId,
        @PathVariable UUID chapterId,
        @PathVariable UUID generationId
    ) {
        return ChapterResponse.from(generationService.adopt(storyId, chapterId, generationId));
    }

    @PostMapping("/{generationId}/confirm")
    public ChapterResponse confirm(
        @PathVariable UUID storyId,
        @PathVariable UUID chapterId,
        @PathVariable UUID generationId
    ) {
        return ChapterResponse.from(generationService.confirmDraft(storyId, chapterId, generationId));
    }

    @GetMapping(
        value = "/{generationId}/events",
        produces = MediaType.TEXT_EVENT_STREAM_VALUE
    )
    public ResponseEntity<StreamingResponseBody> events(
        @PathVariable UUID storyId,
        @PathVariable UUID chapterId,
        @PathVariable UUID generationId
    ) {
        ChapterGeneration generation = generationService.markRunning(storyId, chapterId, generationId);

        StreamingResponseBody body = outputStream -> proxyPythonSse(
            outputStream,
            generation
        );

        return ResponseEntity.ok()
            .header(HttpHeaders.CACHE_CONTROL, "no-cache")
            .header("X-Accel-Buffering", "no")
            .contentType(MediaType.TEXT_EVENT_STREAM)
            .body(body);
    }

    private void proxyPythonSse(OutputStream outputStream, ChapterGeneration generation) throws IOException {
        List<Map<String, Object>> executionHistory = new ArrayList<>();
        String currentEvent = null;
        StringBuilder dataBuffer = new StringBuilder();
        List<String> eventLines = new ArrayList<>();

        HttpURLConnection connection = null;
        try {
            URI uri = URI.create(
                pythonAiBaseUrl
                    + "/internal/ai/stories/" + encode(generation.getStoryId().toString())
                    + "/chapters/" + encode(generation.getChapterId().toString())
                    + "/drafts/stream"
            );
            connection = (HttpURLConnection) uri.toURL().openConnection();
            connection.setRequestMethod("POST");
            connection.setRequestProperty("Accept", MediaType.TEXT_EVENT_STREAM_VALUE);
            connection.setRequestProperty("Content-Type", MediaType.APPLICATION_JSON_VALUE);
            connection.setConnectTimeout(10_000);
            connection.setReadTimeout(0);
            connection.setDoOutput(true);

            try (OutputStream requestBody = connection.getOutputStream()) {
                objectMapper.writeValue(requestBody, pythonDraftRequest(generation));
            }

            try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(connection.getInputStream(), StandardCharsets.UTF_8)
            )) {
                String line;
                while ((line = reader.readLine()) != null) {
                    if (line.startsWith(":") && currentEvent == null) {
                        writeSseLine(outputStream, line);
                        continue;
                    }
                    eventLines.add(line);

                    if (line.startsWith("event:")) {
                        currentEvent = line.substring("event:".length()).trim();
                    } else if (line.startsWith("data:")) {
                        dataBuffer.append(line.substring("data:".length()).trim());
                    } else if (line.isBlank() && currentEvent != null) {
                        boolean forwardOriginal = handlePythonEvent(
                            outputStream,
                            generation,
                            currentEvent,
                            dataBuffer.toString(),
                            executionHistory
                        );
                        if (forwardOriginal) {
                            writeSseLines(outputStream, eventLines);
                        }
                        currentEvent = null;
                        dataBuffer.setLength(0);
                        eventLines.clear();
                    } else if (line.isBlank()) {
                        writeSseLines(outputStream, eventLines);
                        eventLines.clear();
                    }
                }
            }
        } catch (Exception ex) {
            generationService.failFromStream(
                generation.getStoryId(),
                generation.getChapterId(),
                generation.getId(),
                ex.getMessage()
            );
            writeJavaError(outputStream, ex.getMessage());
        } finally {
            if (connection != null) {
                connection.disconnect();
            }
        }
    }

    Map<String, Object> pythonDraftRequest(ChapterGeneration generation) {
        Map<String, Object> request = generation.getRequest();
        Map<String, Object> writingContext = mapValue(request.get("writing_context"));

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("generationId", generation.getId().toString());
        payload.put("userId", generation.getUserId().toString());
        payload.put("story", writingContext.getOrDefault("story", Map.of()));
        payload.put("chapter", writingContext.getOrDefault("chapter", Map.of()));
        payload.put("blueprint", writingContext.getOrDefault("blueprint", Map.of()));
        payload.put("confirmedOutline", writingContext.getOrDefault("confirmedOutline", Map.of()));
        payload.put("recentChapters", writingContext.getOrDefault("recentChapters", List.of()));
        payload.put("timeline", writingContext.getOrDefault("timeline", List.of()));
        payload.put("characters", writingContext.getOrDefault("characters", List.of()));
        payload.put("world", writingContext.getOrDefault("world", List.of()));
        payload.put("foreshadows", writingContext.getOrDefault("foreshadows", List.of()));
        payload.put("additionalMemory", writingContext.getOrDefault("additionalMemory", List.of()));
        payload.put("contextMetadata", writingContext.getOrDefault("contextMetadata", Map.of()));
        payload.put("extraPrompt", request.get("extra_prompt"));
        payload.put("targetWords", request.get("target_words"));
        payload.put("modelProfile", request.get("model_profile"));
        return payload;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        if (value instanceof Map<?, ?>) {
            return (Map<String, Object>) value;
        }
        return Map.of();
    }

    private boolean handlePythonEvent(
        OutputStream outputStream,
        ChapterGeneration generation,
        String event,
        String data,
        List<Map<String, Object>> executionHistory
    ) throws IOException {
        if (data == null || data.isBlank()) {
            return true;
        }

        Map<String, Object> payload = objectMapper.readValue(
            data,
            new TypeReference<Map<String, Object>>() {
            }
        );

        if ("node_end".equals(event)) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("node", payload.get("node"));
            item.put("status", "succeeded");
            executionHistory.add(item);
        } else if ("done".equals(event)) {
            String draft = asString(payload.get("draft"));
            Integer wordCount = asInteger(payload.get("word_count"));
            runQualityGatesAndComplete(outputStream, generation, draft, wordCount, executionHistory);
            return false;
        } else if ("error".equals(event)) {
            generationService.failFromStream(
                generation.getStoryId(),
                generation.getChapterId(),
                generation.getId(),
                asString(payload.get("message"))
            );
        }
        return true;
    }

    private void runQualityGatesAndComplete(
        OutputStream outputStream,
        ChapterGeneration generation,
        String draft,
        Integer wordCount,
        List<Map<String, Object>> executionHistory
    ) throws IOException {
        generationService.markReviewing(
            generation.getStoryId(),
            generation.getChapterId(),
            generation.getId()
        );

        Map<String, Object> gateRequest = pythonDraftGateRequest(generation, draft);

        yieldSse(outputStream, "node_start", Map.of("node", "check_consistency", "progress", 70));
        Map<String, Object> consistencyReport;
        try {
            consistencyReport = aiDraftQualityClient.checkConsistency(
                generation.getStoryId(),
                generation.getChapterId(),
                gateRequest
            );
        } catch (RuntimeException ex) {
            consistencyReport = gateErrorReport("consistency", ex);
        }
        executionHistory.add(historyItem("check_consistency", consistencyReport));
        yieldSse(
            outputStream,
            "node_end",
            Map.of(
                "node", "check_consistency",
                "progress", 70,
                "issues", issueCount(consistencyReport),
                "blocking", Boolean.TRUE.equals(consistencyReport.get("blocking"))
            )
        );

        yieldSse(outputStream, "node_start", Map.of("node", "review", "progress", 80));
        Map<String, Object> reviewReport;
        try {
            reviewReport = aiDraftQualityClient.reviewQuality(
                generation.getStoryId(),
                generation.getChapterId(),
                gateRequest
            );
        } catch (RuntimeException ex) {
            reviewReport = gateErrorReport("review", ex);
        }
        executionHistory.add(historyItem("review", reviewReport));
        yieldSse(
            outputStream,
            "node_end",
            Map.of(
                "node", "review",
                "progress", 80,
                "issues", issueCount(reviewReport),
                "blocking", Boolean.TRUE.equals(reviewReport.get("blocking"))
            )
        );

        generationService.completeFromStream(
            generation.getStoryId(),
            generation.getChapterId(),
            generation.getId(),
            draft,
            wordCount,
            executionHistory,
            consistencyReport,
            reviewReport
        );

        Map<String, Object> donePayload = new LinkedHashMap<>();
        donePayload.put("story_id", generation.getStoryId());
        donePayload.put("chapter_id", generation.getChapterId());
        donePayload.put("saved_chapter_id", null);
        donePayload.put("draft", draft == null ? "" : draft);
        donePayload.put("word_count", wordCount == null ? 0 : wordCount);
        donePayload.put("consistency_report", consistencyReport);
        donePayload.put("review_report", reviewReport);
        yieldSse(outputStream, "done", donePayload);
    }

    private Map<String, Object> pythonDraftGateRequest(ChapterGeneration generation, String draft) {
        Map<String, Object> request = generation.getRequest();
        Map<String, Object> writingContext = mapValue(request.get("writing_context"));

        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("generationId", generation.getId().toString());
        payload.put("story", writingContext.getOrDefault("story", Map.of()));
        payload.put("chapter", writingContext.getOrDefault("chapter", Map.of()));
        payload.put("blueprint", writingContext.getOrDefault("blueprint", Map.of()));
        payload.put("confirmedOutline", writingContext.getOrDefault("confirmedOutline", Map.of()));
        payload.put("recentChapters", writingContext.getOrDefault("recentChapters", List.of()));
        payload.put("activeForeshadows", writingContext.getOrDefault("foreshadows", List.of()));
        payload.put("timeline", writingContext.getOrDefault("timeline", List.of()));
        payload.put("characters", writingContext.getOrDefault("characters", List.of()));
        payload.put("worldState", writingContext.getOrDefault("world", List.of()));
        payload.put("draft", draft == null ? "" : draft);
        payload.put("extraPrompt", request.get("extra_prompt"));
        payload.put("targetWords", request.get("target_words"));
        return payload;
    }

    private Map<String, Object> historyItem(String node, Map<String, Object> report) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("node", node);
        item.put("status", "succeeded");
        item.put("issues", issueCount(report));
        item.put("blocking", Boolean.TRUE.equals(report.get("blocking")));
        if (report.get("overallScore") != null) {
            item.put("overallScore", report.get("overallScore"));
        }
        return item;
    }

    private Map<String, Object> gateErrorReport(String source, RuntimeException ex) {
        Map<String, Object> issue = new LinkedHashMap<>();
        issue.put("severity", "P0");
        issue.put("message", "Draft " + source + " gate failed");
        issue.put("evidence", ex.getMessage() == null ? ex.getClass().getSimpleName() : ex.getMessage());
        issue.put("suggestion", "Retry generation or review the AI worker error before confirming this draft.");
        issue.put("blocking", true);
        issue.put("autoRepairRequired", false);

        Map<String, Object> report = new LinkedHashMap<>();
        report.put("summary", "Draft " + source + " gate failed and blocks confirmation.");
        report.put("issues", List.of(issue));
        report.put("blocking", true);
        report.put("autoRepairRequired", false);
        if ("review".equals(source)) {
            issue.put("category", "continuity");
            report.put("overallScore", 0);
            report.put("revisionHints", List.of("Resolve the review gate error before confirming."));
            report.put("strengths", List.of());
        } else {
            issue.put("domain", "timeline");
            issue.put("ruleId", "GATE_ERROR");
            report.put("checkedRuleIds", List.of());
            report.put("passedRuleIds", List.of());
        }
        return report;
    }

    private int issueCount(Map<String, Object> report) {
        Object issues = report == null ? null : report.get("issues");
        return issues instanceof List<?> ? ((List<?>) issues).size() : 0;
    }

    private void writeSseLine(OutputStream outputStream, String line) throws IOException {
        outputStream.write((line + "\n").getBytes(StandardCharsets.UTF_8));
        if (line.isBlank()) {
            outputStream.flush();
        }
    }

    private void writeSseLines(OutputStream outputStream, List<String> lines) throws IOException {
        for (String line : lines) {
            writeSseLine(outputStream, line);
        }
    }

    private void yieldSse(OutputStream outputStream, String event, Map<String, Object> payload) throws IOException {
        outputStream.write(_sse(event, payload).getBytes(StandardCharsets.UTF_8));
        outputStream.flush();
    }

    private void writeJavaError(OutputStream outputStream, String message) throws IOException {
        String data = objectMapper.writeValueAsString(Map.of(
            "message",
            message == null ? "Java SSE proxy error" : message
        ));
        outputStream.write(("event: error\ndata: " + data + "\n\n").getBytes(StandardCharsets.UTF_8));
        outputStream.flush();
    }

    private String encode(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8);
    }

    private String _sse(String event, Map<String, Object> data) throws IOException {
        return "event: " + event + "\ndata: " + objectMapper.writeValueAsString(data) + "\n\n";
    }

    private String asString(Object value) {
        return value == null ? null : value.toString();
    }

    private Integer asInteger(Object value) {
        if (value instanceof Number) {
            return ((Number) value).intValue();
        }
        if (value == null) {
            return null;
        }
        return Integer.valueOf(value.toString());
    }
}
