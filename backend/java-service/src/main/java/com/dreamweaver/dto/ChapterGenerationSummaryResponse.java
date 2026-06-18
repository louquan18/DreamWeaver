package com.dreamweaver.dto;

import java.time.OffsetDateTime;
import java.util.UUID;

import com.dreamweaver.entity.ChapterGeneration;

public record ChapterGenerationSummaryResponse(
    UUID id,
    UUID storyId,
    UUID chapterId,
    String status,
    Integer wordCount,
    String modelProfile,
    String modelName,
    boolean adopted,
    OffsetDateTime createdAt,
    OffsetDateTime completedAt
) {
    public static ChapterGenerationSummaryResponse from(
        ChapterGeneration generation,
        UUID adoptedGenerationId
    ) {
        return new ChapterGenerationSummaryResponse(
            generation.getId(),
            generation.getStoryId(),
            generation.getChapterId(),
            generation.getStatus().value(),
            generation.getWordCount(),
            generation.getModelProfile(),
            generation.getModelName(),
            generation.getId().equals(adoptedGenerationId),
            generation.getCreatedAt(),
            generation.getCompletedAt()
        );
    }
}
