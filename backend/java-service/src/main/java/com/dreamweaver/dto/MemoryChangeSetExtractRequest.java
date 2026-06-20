package com.dreamweaver.dto;

import java.util.Map;
import java.util.UUID;

public record MemoryChangeSetExtractRequest(
    UUID userId,
    Map<String, Object> options
) {
}
