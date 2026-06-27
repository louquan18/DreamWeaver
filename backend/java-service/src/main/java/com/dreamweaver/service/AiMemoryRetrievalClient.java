package com.dreamweaver.service;

import java.time.Duration;
import java.util.Map;
import java.util.UUID;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

import com.dreamweaver.dto.AiAdditionalMemoryIndexRequest;
import com.dreamweaver.dto.AiAdditionalMemoryIndexResponse;
import com.dreamweaver.dto.AiAdditionalMemoryRetrieveRequest;
import com.dreamweaver.dto.AiAdditionalMemoryRetrieveResponse;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

@Component
public class AiMemoryRetrievalClient {

    private static final String AI_VALIDATION_ERROR = "ai_validation_error";
    private static final String AI_WORKER_ERROR = "ai_worker_error";

    private final RestClient restClient;
    private final ObjectMapper objectMapper;

    public AiMemoryRetrievalClient(
        @Value("${dreamweaver.python-ai.base-url}") String pythonAiBaseUrl,
        ObjectMapper objectMapper
    ) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Duration.ofSeconds(5));
        requestFactory.setReadTimeout(Duration.ofSeconds(20));

        this.restClient = RestClient.builder()
            .baseUrl(stripTrailingSlash(pythonAiBaseUrl))
            .requestFactory(requestFactory)
            .build();
        this.objectMapper = objectMapper;
    }

    public AiAdditionalMemoryIndexResponse indexChapter(
        UUID storyId,
        AiAdditionalMemoryIndexRequest request
    ) {
        try {
            AiAdditionalMemoryIndexResponse response = restClient.post()
                .uri("/internal/ai/stories/{storyId}/memory/index", storyId)
                .body(request)
                .retrieve()
                .body(AiAdditionalMemoryIndexResponse.class);
            if (response == null) {
                throw new AiWorkerException(AI_WORKER_ERROR, "AI worker returned an empty response");
            }
            return response;
        } catch (RestClientResponseException ex) {
            throw mapWorkerException(ex);
        } catch (ResourceAccessException ex) {
            throw new AiWorkerException(AI_WORKER_ERROR, "AI worker is unavailable: " + ex.getMessage());
        }
    }

    public AiAdditionalMemoryRetrieveResponse retrieve(
        UUID storyId,
        AiAdditionalMemoryRetrieveRequest request
    ) {
        try {
            AiAdditionalMemoryRetrieveResponse response = restClient.post()
                .uri("/internal/ai/stories/{storyId}/memory/retrieve", storyId)
                .body(request)
                .retrieve()
                .body(AiAdditionalMemoryRetrieveResponse.class);
            if (response == null) {
                throw new AiWorkerException(AI_WORKER_ERROR, "AI worker returned an empty response");
            }
            return response;
        } catch (RestClientResponseException ex) {
            throw mapWorkerException(ex);
        } catch (ResourceAccessException ex) {
            throw new AiWorkerException(AI_WORKER_ERROR, "AI worker is unavailable: " + ex.getMessage());
        }
    }

    private RuntimeException mapWorkerException(RestClientResponseException ex) {
        if (ex.getStatusCode().is4xxClientError()) {
            return new BadRequestException(AI_VALIDATION_ERROR, workerMessage(ex));
        }
        return new AiWorkerException(AI_WORKER_ERROR, workerMessage(ex));
    }

    private String workerMessage(RestClientResponseException ex) {
        String body = ex.getResponseBodyAsString();
        if (body == null || body.isBlank()) {
            return "AI worker request failed with status " + ex.getStatusCode().value();
        }
        try {
            Map<String, Object> payload = objectMapper.readValue(
                body,
                new TypeReference<Map<String, Object>>() {
                }
            );
            Object detail = payload.get("detail");
            if (detail instanceof Map<?, ?> detailMap) {
                Object message = detailMap.get("message");
                if (message != null) {
                    return message.toString();
                }
            }
            Object message = payload.get("message");
            return message == null ? body : message.toString();
        } catch (Exception ignored) {
            return body;
        }
    }

    private String stripTrailingSlash(String value) {
        if (value == null || value.isBlank()) {
            return "http://localhost:8000";
        }
        return value.endsWith("/") ? value.substring(0, value.length() - 1) : value;
    }
}
