package com.dreamweaver.dto;

import java.util.List;
import java.util.Map;

public record AiMemoryExtractionResponse(
    String storyId,
    String chapterId,
    String sourceGenerationId,
    Integer schemaVersion,
    String extractorVersion,
    String status,
    String summary,
    List<Map<String, Object>> changes,
    List<Map<String, Object>> warnings
) {
}
