package com.dreamweaver.dto;

import java.util.Map;
import java.util.UUID;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;

public record ChapterGenerationCreateRequest(
    UUID userId,
    @Min(1) Integer targetWords,
    String extraPrompt,
    @Size(max = 50) String modelProfile,
    Boolean autoAdopt,
    Map<String, Object> options
) {
}
