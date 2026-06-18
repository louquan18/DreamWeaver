package com.dreamweaver.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record StoryCreateRequest(
    @NotBlank @Size(max = 200) String title,
    String description,
    @Size(max = 50) String genre,
    @Min(1) Integer targetWords
) {
}
