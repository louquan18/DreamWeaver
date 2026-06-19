package com.dreamweaver.dto;

import java.util.List;
import java.util.Map;

public record AiOutlineOptionResponse(
    String storyId,
    String chapterId,
    String optionGroupId,
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
    String status
) {
}
