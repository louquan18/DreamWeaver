package com.dreamweaver.dto;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import com.dreamweaver.entity.ChapterOutlineOption;

public record ChapterOutlineOptionResponse(
    UUID id,
    UUID storyId,
    UUID chapterId,
    UUID optionGroupId,
    String optionCode,
    String optionType,
    List<String> titleCandidates,
    String chapterGoal,
    String storySummary,
    List<Map<String, Object>> sceneOutline,
    List<Map<String, Object>> charactersInvolved,
    Map<String, Object> conflict,
    String highlightMoment,
    List<Map<String, Object>> foreshadowActions,
    List<Map<String, Object>> memoryReferences,
    String whyThisPlan,
    String endingHook,
    List<String> riskNotes,
    String status,
    OffsetDateTime createdAt,
    OffsetDateTime updatedAt
) {
    public static ChapterOutlineOptionResponse from(ChapterOutlineOption option) {
        return new ChapterOutlineOptionResponse(
            option.getId(),
            option.getStoryId(),
            option.getChapterId(),
            option.getOptionGroupId(),
            option.getOptionCode().value(),
            option.getOptionType().value(),
            option.getTitleCandidates(),
            option.getChapterGoal(),
            option.getStorySummary(),
            option.getSceneOutline(),
            option.getCharactersInvolved(),
            option.getConflict(),
            option.getHighlightMoment(),
            option.getForeshadowActions(),
            option.getMemoryReferences(),
            option.getWhyThisPlan(),
            option.getEndingHook(),
            option.getRiskNotes(),
            option.getStatus().value(),
            option.getCreatedAt(),
            option.getUpdatedAt()
        );
    }
}
