package com.dreamweaver.dto;

import java.util.List;
import java.util.Map;

public record MemoryChangeSetUpdateRequest(
    List<Map<String, Object>> timelineChanges,
    List<Map<String, Object>> characterChanges,
    List<Map<String, Object>> worldChanges,
    List<Map<String, Object>> foreshadowChanges,
    List<Map<String, Object>> conflicts,
    Map<String, Object> extractionMetadata
) {
}
