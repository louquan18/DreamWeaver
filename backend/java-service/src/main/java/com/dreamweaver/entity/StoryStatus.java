package com.dreamweaver.entity;

public enum StoryStatus {
    DRAFT("draft"),
    WRITING("writing"),
    COMPLETED("completed");

    private final String value;

    StoryStatus(String value) {
        this.value = value;
    }

    public String value() {
        return value;
    }

    public static StoryStatus fromValue(String value) {
        for (StoryStatus status : values()) {
            if (status.value.equals(value)) {
                return status;
            }
        }
        throw new IllegalArgumentException("Unknown story status: " + value);
    }
}
