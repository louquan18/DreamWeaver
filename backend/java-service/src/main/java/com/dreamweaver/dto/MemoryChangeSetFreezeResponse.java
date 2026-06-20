package com.dreamweaver.dto;

import com.dreamweaver.service.MemoryChangeSetService;

public record MemoryChangeSetFreezeResponse(
    ChapterResponse chapter,
    MemoryChangeSetResponse memoryChangeSet
) {
    public static MemoryChangeSetFreezeResponse from(MemoryChangeSetService.FreezeResult result) {
        return new MemoryChangeSetFreezeResponse(
            ChapterResponse.from(result.chapter()),
            MemoryChangeSetResponse.from(result.memoryChangeSet())
        );
    }
}
