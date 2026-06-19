package com.dreamweaver.dto;

import java.util.Map;

public record ChapterOutlineOptionsGenerateRequest(
    Map<String, Object> authorIntent
) {
}
