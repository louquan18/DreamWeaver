package com.dreamweaver.dto;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.dreamweaver.entity.NovelBlueprint;

public record NovelBlueprintResponse(
    UUID id,
    UUID storyId,
    String sourcePrompt,
    String premise,
    String genre,
    String tone,
    Map<String, Object> protagonist,
    Map<String, Object> mainThread,
    Map<String, Object> coreConflict,
    Map<String, Object> worldSeed,
    Map<String, Object> writingPreferences,
    List<Map<String, Object>> lockedFacts,
    String status,
    OffsetDateTime confirmedAt,
    OffsetDateTime supersededAt,
    OffsetDateTime createdAt,
    OffsetDateTime updatedAt
) {
    public static NovelBlueprintResponse from(NovelBlueprint blueprint) {
        return new NovelBlueprintResponse(
            blueprint.getId(),
            blueprint.getStoryId(),
            blueprint.getSourcePrompt(),
            blueprint.getPremise(),
            blueprint.getGenre(),
            blueprint.getTone(),
            blueprint.getProtagonist(),
            blueprint.getMainThread(),
            blueprint.getCoreConflict(),
            blueprint.getWorldSeed(),
            blueprint.getWritingPreferences(),
            blueprint.getLockedFacts(),
            blueprint.getStatus().value(),
            blueprint.getConfirmedAt(),
            blueprint.getSupersededAt(),
            blueprint.getCreatedAt(),
            blueprint.getUpdatedAt()
        );
    }
}
