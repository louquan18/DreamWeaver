package com.dreamweaver.dto;

import java.util.List;

public record ChapterOutlineOptionsGenerateResponse(
    ChapterResponse chapter,
    List<ChapterOutlineOptionResponse> options
) {
}
