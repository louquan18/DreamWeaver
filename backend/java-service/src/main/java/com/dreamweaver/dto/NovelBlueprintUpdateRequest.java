package com.dreamweaver.dto;

import java.util.List;
import java.util.Map;

import jakarta.validation.constraints.Size;

public record NovelBlueprintUpdateRequest(
    @Size(max = 10000) String sourcePrompt,
    @Size(max = 2000) String premise,
    @Size(max = 50) String genre,
    @Size(max = 100) String tone,
    Map<String, Object> protagonist,
    Map<String, Object> mainThread,
    Map<String, Object> coreConflict,
    Map<String, Object> worldSeed,
    Map<String, Object> writingPreferences,
    List<Map<String, Object>> lockedFacts
) {
}
