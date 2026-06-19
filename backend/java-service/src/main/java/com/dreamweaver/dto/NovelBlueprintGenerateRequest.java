package com.dreamweaver.dto;

import java.util.Map;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record NovelBlueprintGenerateRequest(
    @NotBlank @Size(max = 10000) String sourcePrompt,
    @Size(max = 80) String genre,
    @Size(max = 120) String tone,
    @Min(1) Integer targetWords,
    Map<String, Object> preferences
) {
}
