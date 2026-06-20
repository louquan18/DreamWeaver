package com.dreamweaver.dto;

import java.util.List;
import java.util.Map;
import java.util.UUID;

public record AiMemoryExtractionRequest(
    UUID storyId,
    UUID chapterId,
    UUID sourceGenerationId,
    String confirmedDraft,
    Map<String, Object> story,
    Map<String, Object> chapter,
    Map<String, Object> blueprint,
    Map<String, Object> confirmedOutline,
    List<Map<String, Object>> recentChapters,
    Map<String, Object> existingMemory,
    Map<String, Object> generationMetadata,
    Map<String, Object> reviewMetadata,
    Map<String, Object> consistencyMetadata,
    Map<String, Object> repairMetadata
) {
}
