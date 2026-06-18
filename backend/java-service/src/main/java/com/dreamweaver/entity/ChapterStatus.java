package com.dreamweaver.entity;

public enum ChapterStatus {
    DRAFT("draft"),
    GENERATING("generating"),
    GENERATED("generated"),
    APPROVED("approved");

    private final String value;

    ChapterStatus(String value) {
        this.value = value;
    }

    public String value() {
        return value;
    }

    public static ChapterStatus fromValue(String value) {
        for (ChapterStatus status : values()) {
            if (status.value.equals(value)) {
                return status;
            }
        }
        throw new IllegalArgumentException("Unknown chapter status: " + value);
    }
}
