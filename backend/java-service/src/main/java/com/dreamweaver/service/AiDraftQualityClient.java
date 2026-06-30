package com.dreamweaver.service;

import java.time.Duration;
import java.util.Map;
import java.util.UUID;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

@Component
public class AiDraftQualityClient {

    private static final String AI_VALIDATION_ERROR = "ai_validation_error";
    private static final String AI_WORKER_ERROR = "ai_worker_error";

    private final RestClient restClient;
    private final ObjectMapper objectMapper;

    public AiDraftQualityClient(
        @Value("${dreamweaver.python-ai.base-url}") String pythonAiBaseUrl,
        ObjectMapper objectMapper
    ) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Duration.ofSeconds(10));
        requestFactory.setReadTimeout(Duration.ofSeconds(120));

        this.restClient = RestClient.builder()
            .baseUrl(stripTrailingSlash(pythonAiBaseUrl))
            .requestFactory(requestFactory)
            .build();
        this.objectMapper = objectMapper;
    }

    public Map<String, Object> checkConsistency(
        UUID storyId,
        UUID chapterId,
        Map<String, Object> request
    ) {
        return postGate(storyId, chapterId, "/consistency", request);
    }

    public Map<String, Object> reviewQuality(
        UUID storyId,
        UUID chapterId,
        Map<String, Object> request
    ) {
        return postGate(storyId, chapterId, "/review", request);
    }

    private Map<String, Object> postGate(
        UUID storyId,
        UUID chapterId,
        String path,
        Map<String, Object> request
    ) {
        try {
            Map<String, Object> response = restClient.post()
                .uri(
                    "/internal/ai/stories/{storyId}/chapters/{chapterId}/drafts" + path,
                    storyId,
                    chapterId
                )
                .body(request)
                .retrieve()
                .body(new ParameterizedTypeReference<Map<String, Object>>() {
                });

            if (response == null) {
                throw new AiWorkerException(AI_WORKER_ERROR, "AI worker returned an empty response");
            }
            return response;
        } catch (RestClientResponseException ex) {
            if (ex.getStatusCode().is4xxClientError()) {
                throw new BadRequestException(AI_VALIDATION_ERROR, workerMessage(ex));
            }
            throw new AiWorkerException(AI_WORKER_ERROR, workerMessage(ex));
        } catch (ResourceAccessException ex) {
            throw new AiWorkerException(AI_WORKER_ERROR, "AI worker is unavailable: " + ex.getMessage());
        } catch (AiWorkerException | BadRequestException ex) {
            throw ex;
        } catch (RuntimeException ex) {
            throw new AiWorkerException(AI_WORKER_ERROR, "AI worker response could not be processed");
        }
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
            if (detail instanceof Map<?, ?>) {
                Map<?, ?> detailMap = (Map<?, ?>) detail;
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
