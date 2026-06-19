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
    private final ObjectMapper objectMapper;
    private final String pythonAiBaseUrl;

    public ChapterGenerationController(
        ChapterGenerationService generationService,
        ChapterService chapterService,
        ObjectMapper objectMapper,
        @Value("${dreamweaver.python-ai.base-url}") String pythonAiBaseUrl
    ) {
        this.generationService = generationService;
        this.chapterService = chapterService;
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
                    writeSseLine(outputStream, line);

                    if (line.startsWith("event:")) {
                        currentEvent = line.substring("event:".length()).trim();
                    } else if (line.startsWith("data:")) {
                        dataBuffer.append(line.substring("data:".length()).trim());
                    } else if (line.isBlank() && currentEvent != null) {
                        handlePythonEvent(generation, currentEvent, dataBuffer.toString(), executionHistory);
                        currentEvent = null;
                        dataBuffer.setLength(0);
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
        payload.put("extraPrompt", request.get("extra_prompt"));
        payload.put("targetWords", request.get("target_words"));
        payload.put("modelProfile", request.get("model_profile"));
        return payload;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        if (value instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Map.of();
    }

    private void handlePythonEvent(
        ChapterGeneration generation,
        String event,
        String data,
        List<Map<String, Object>> executionHistory
    ) throws IOException {
        if (data == null || data.isBlank()) {
            return;
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
            generationService.completeFromStream(
                generation.getStoryId(),
                generation.getChapterId(),
                generation.getId(),
                draft,
                wordCount,
                executionHistory
            );
        } else if ("error".equals(event)) {
            generationService.failFromStream(
                generation.getStoryId(),
                generation.getChapterId(),
                generation.getId(),
                asString(payload.get("message"))
            );
        }
    }

    private void writeSseLine(OutputStream outputStream, String line) throws IOException {
        outputStream.write((line + "\n").getBytes(StandardCharsets.UTF_8));
        if (line.isBlank()) {
            outputStream.flush();
        }
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

    private String asString(Object value) {
        return value == null ? null : value.toString();
    }

    private Integer asInteger(Object value) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        if (value == null) {
            return null;
        }
        return Integer.valueOf(value.toString());
    }
}
