package com.dreamweaver.dto;

import java.util.List;
import java.util.Map;

public record AiAdditionalMemoryRetrieveResponse(
    String storyId,
    String retrievalMethod,
    List<Map<String, Object>> additionalMemory
) {
}
