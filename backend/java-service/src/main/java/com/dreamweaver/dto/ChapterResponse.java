package com.dreamweaver.dto;

import java.time.OffsetDateTime;
import java.util.UUID;

import com.dreamweaver.entity.Chapter;

public record ChapterResponse(
    UUID id,
    UUID storyId,
    Integer chapterNumber,
    String title,
    String content,
    String contentUrl,
    Integer wordCount,
    String status,
    UUID lastGenerationId,
    OffsetDateTime createdAt,
    OffsetDateTime updatedAt
) {
    public static ChapterResponse from(Chapter chapter) {
        return new ChapterResponse(
            chapter.getId(),
            chapter.getStoryId(),
            chapter.getChapterNumber(),
            chapter.getTitle(),
            chapter.getContent(),
            chapter.getContentUrl(),
            chapter.getWordCount(),
            chapter.getStatus().value(),
            chapter.getLastGenerationId(),
            chapter.getCreatedAt(),
            chapter.getUpdatedAt()
        );
    }
}
