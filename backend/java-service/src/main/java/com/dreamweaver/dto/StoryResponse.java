package com.dreamweaver.dto;

import java.time.OffsetDateTime;
import java.util.UUID;

import com.dreamweaver.entity.Story;

public record StoryResponse(
    UUID id,
    UUID userId,
    String title,
    String description,
    String genre,
    Integer targetWords,
    String status,
    OffsetDateTime createdAt,
    OffsetDateTime updatedAt
) {
    public static StoryResponse from(Story story) {
        return new StoryResponse(
            story.getId(),
            story.getUserId(),
            story.getTitle(),
            story.getDescription(),
            story.getGenre(),
            story.getTargetWords(),
            story.getStatus().value(),
            story.getCreatedAt(),
            story.getUpdatedAt()
        );
    }
}
