package com.dreamweaver.dto;

public record ChapterOutlineConfirmResponse(
    ChapterResponse chapter,
    ChapterOutlineResponse outline
) {
}
