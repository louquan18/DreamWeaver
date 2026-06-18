package com.dreamweaver.dto;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.dreamweaver.entity.ChapterGeneration;

public record ChapterGenerationDetailResponse(
    UUID id,
    UUID storyId,
    UUID chapterId,
    UUID userId,
    String status,
    Map<String, Object> request,
    String draft,
    String draftUrl,
    Integer wordCount,
    String modelProfile,
    String modelName,
    List<Map<String, Object>> executionHistory,
    Map<String, Object> consistencyReport,
    Map<String, Object> reviewReport,
    UUID checkpointId,
    String errorMessage,
    boolean adopted,
    OffsetDateTime startedAt,
    OffsetDateTime completedAt,
    OffsetDateTime createdAt,
    OffsetDateTime updatedAt
) {
    public static ChapterGenerationDetailResponse from(
        ChapterGeneration generation,
        UUID adoptedGenerationId
    ) {
        return new ChapterGenerationDetailResponse(
            generation.getId(),
            generation.getStoryId(),
            generation.getChapterId(),
            generation.getUserId(),
            generation.getStatus().value(),
            generation.getRequest(),
            generation.getDraft(),
            generation.getDraftUrl(),
            generation.getWordCount(),
            generation.getModelProfile(),
            generation.getModelName(),
            generation.getExecutionHistory(),
            generation.getConsistencyReport(),
            generation.getReviewReport(),
            generation.getCheckpointId(),
            generation.getErrorMessage(),
            generation.getId().equals(adoptedGenerationId),
            generation.getStartedAt(),
            generation.getCompletedAt(),
            generation.getCreatedAt(),
            generation.getUpdatedAt()
        );
    }
}
