package com.dreamweaver.entity;

public enum ChapterWorkflowStage {
    CHAPTER_CREATED("chapter_created"),
    OUTLINE_OPTIONS_GENERATING("outline_options_generating"),
    OUTLINE_OPTIONS_GENERATED("outline_options_generated"),
    OUTLINE_CONFIRMED("outline_confirmed"),
    DRAFT_GENERATING("draft_generating"),
    DRAFT_GENERATED("draft_generated"),
    REVIEWING("reviewing"),
    REVISION_REQUIRED("revision_required"),
    DRAFT_READY_FOR_CONFIRMATION("draft_ready_for_confirmation"),
    DRAFT_CONFIRMED("draft_confirmed"),
    MEMORY_EXTRACTING("memory_extracting"),
    MEMORY_PENDING_CONFIRMATION("memory_pending_confirmation"),
    MEMORY_CONFIRMED("memory_confirmed"),
    CHAPTER_CONFIRMED("chapter_confirmed");

    private final String value;

    ChapterWorkflowStage(String value) {
        this.value = value;
    }

    public String value() {
        return value;
    }

    public static ChapterWorkflowStage fromValue(String value) {
        for (ChapterWorkflowStage stage : values()) {
            if (stage.value.equals(value)) {
                return stage;
            }
        }
        throw new IllegalArgumentException("Unknown chapter workflow stage: " + value);
    }
}
