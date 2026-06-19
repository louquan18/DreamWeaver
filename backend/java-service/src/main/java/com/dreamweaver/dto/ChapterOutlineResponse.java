package com.dreamweaver.dto;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.dreamweaver.entity.ChapterOutline;

public record ChapterOutlineResponse(
    UUID id,
    UUID storyId,
    UUID chapterId,
    List<UUID> sourceOptionIds,
    String userFeedback,
    Map<String, Object> finalOutline,
    String status,
    OffsetDateTime confirmedAt,
    OffsetDateTime createdAt,
    OffsetDateTime updatedAt
) {
    public static ChapterOutlineResponse from(ChapterOutline outline) {
        return new ChapterOutlineResponse(
            outline.getId(),
            outline.getStoryId(),
            outline.getChapterId(),
            outline.getSourceOptionIds(),
            outline.getUserFeedback(),
            outline.getFinalOutline(),
            outline.getStatus().value(),
            outline.getConfirmedAt(),
            outline.getCreatedAt(),
            outline.getUpdatedAt()
        );
    }
}
