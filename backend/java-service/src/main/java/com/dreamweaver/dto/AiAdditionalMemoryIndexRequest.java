package com.dreamweaver.dto;

import java.util.Map;

public record AiAdditionalMemoryIndexRequest(
    Integer chapterNumber,
    String title,
    String summary,
    String content,
    Map<String, Object> metadata
) {
}
