package com.dreamweaver.dto;

import java.util.UUID;

public record MemoryChangeSetConfirmRequest(
    UUID userId
) {
}
