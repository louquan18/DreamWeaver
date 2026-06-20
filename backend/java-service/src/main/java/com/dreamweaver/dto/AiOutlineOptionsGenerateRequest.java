package com.dreamweaver.dto;

import java.util.List;
import java.util.Map;

public record AiOutlineOptionsGenerateRequest(
    String optionGroupId,
    Map<String, Object> story,
    Map<String, Object> chapter,
    Map<String, Object> blueprint,
    Map<String, Object> authorIntent,
    List<Map<String, Object>> recentChapters,
    List<Map<String, Object>> timeline,
    List<Map<String, Object>> characters,
    List<Map<String, Object>> world,
    List<Map<String, Object>> foreshadows,
    List<Map<String, Object>> additionalMemory
) {
}
