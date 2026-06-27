package com.dreamweaver.dto;

public record AiAdditionalMemoryIndexResponse(
    String storyId,
    Integer chapterNumber,
    Boolean summaryIndexed,
    Boolean fulltextIndexed,
    Boolean vectorAvailable
) {
}
