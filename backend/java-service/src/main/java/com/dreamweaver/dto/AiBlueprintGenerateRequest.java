package com.dreamweaver.dto;

import java.util.Map;

public record AiBlueprintGenerateRequest(
    String sourcePrompt,
    String genre,
    String tone,
    Integer targetWords,
    Map<String, Object> preferences
) {
    public static AiBlueprintGenerateRequest from(NovelBlueprintGenerateRequest request) {
        return new AiBlueprintGenerateRequest(
            request.sourcePrompt(),
            request.genre(),
            request.tone(),
            request.targetWords(),
            request.preferences() == null ? Map.of() : request.preferences()
        );
    }
}
