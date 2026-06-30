package com.dreamweaver.dto;

import java.util.List;
import java.util.Map;
import java.util.UUID;

public record StoryMemoryLibraryResponse(
    UUID storyId,
    String type,
    List<Map<String, Object>> items,
    Integer count,
    Map<String, Object> fingerprint
) {
    public static StoryMemoryLibraryResponse of(
        UUID storyId,
        String type,
        List<Map<String, Object>> items,
        Map<String, Object> fingerprint
    ) {
        return new StoryMemoryLibraryResponse(
            storyId,
            type,
            items,
            items == null ? 0 : items.size(),
            fingerprint
        );
    }
}
