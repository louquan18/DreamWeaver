package com.dreamweaver.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;

public record ChapterCreateRequest(
    @Min(1) Integer chapterNumber,
    @Size(max = 200) String title
) {
}
