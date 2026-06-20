package com.dreamweaver.dto;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.dreamweaver.entity.MemoryChangeSet;

public record MemoryChangeSetResponse(
    UUID id,
    UUID storyId,
    UUID chapterId,
    UUID sourceGenerationId,
    String status,
    Integer schemaVersion,
    List<Map<String, Object>> timelineChanges,
    List<Map<String, Object>> characterChanges,
    List<Map<String, Object>> worldChanges,
    List<Map<String, Object>> foreshadowChanges,
    List<Map<String, Object>> conflicts,
    Map<String, Object> baseMemoryFingerprint,
    String sourceDraftHash,
    Map<String, Object> extractionMetadata,
    Map<String, Object> applyResult,
    UUID createdBy,
    UUID confirmedBy,
    UUID rejectedBy,
    OffsetDateTime confirmedAt,
    OffsetDateTime rejectedAt,
    OffsetDateTime createdAt,
    OffsetDateTime updatedAt
) {
    public static MemoryChangeSetResponse from(MemoryChangeSet changeSet) {
        return new MemoryChangeSetResponse(
            changeSet.getId(),
            changeSet.getStoryId(),
            changeSet.getChapterId(),
            changeSet.getSourceGenerationId(),
            changeSet.getStatus().value(),
            changeSet.getSchemaVersion(),
            changeSet.getTimelineChanges(),
            changeSet.getCharacterChanges(),
            changeSet.getWorldChanges(),
            changeSet.getForeshadowChanges(),
            changeSet.getConflicts(),
            changeSet.getBaseMemoryFingerprint(),
            changeSet.getSourceDraftHash(),
            changeSet.getExtractionMetadata(),
            changeSet.getApplyResult(),
            changeSet.getCreatedBy(),
            changeSet.getConfirmedBy(),
            changeSet.getRejectedBy(),
            changeSet.getConfirmedAt(),
            changeSet.getRejectedAt(),
            changeSet.getCreatedAt(),
            changeSet.getUpdatedAt()
        );
    }
}
