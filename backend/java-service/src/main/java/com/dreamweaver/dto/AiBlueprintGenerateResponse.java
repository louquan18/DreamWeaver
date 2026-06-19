package com.dreamweaver.dto;

import java.util.List;
import java.util.Map;

public record AiBlueprintGenerateResponse(
    String storyId,
    String sourcePrompt,
    String premise,
    String genre,
    String tone,
    Map<String, Object> protagonist,
    Map<String, Object> mainThread,
    Map<String, Object> coreConflict,
    Map<String, Object> worldSeed,
    Map<String, Object> writingPreferences,
    List<Map<String, Object>> lockedFacts,
    List<Map<String, Object>> validationIssues,
    String status
) {
}
