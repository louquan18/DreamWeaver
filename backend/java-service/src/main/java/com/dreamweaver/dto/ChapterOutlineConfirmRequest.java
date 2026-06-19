package com.dreamweaver.dto;

import java.util.List;
import java.util.Map;
import java.util.UUID;

public record ChapterOutlineConfirmRequest(
    List<UUID> sourceOptionIds,
    String userFeedback,
    Map<String, Object> finalOutline
) {
}
