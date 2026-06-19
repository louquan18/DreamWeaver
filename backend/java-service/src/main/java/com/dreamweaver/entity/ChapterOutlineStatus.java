package com.dreamweaver.entity;

public enum ChapterOutlineStatus {
    DRAFT("draft"),
    CONFIRMED("confirmed"),
    SUPERSEDED("superseded");

    private final String value;

    ChapterOutlineStatus(String value) {
        this.value = value;
    }

    public String value() {
        return value;
    }

    public static ChapterOutlineStatus fromValue(String value) {
        for (ChapterOutlineStatus status : values()) {
            if (status.value.equals(value)) {
                return status;
            }
        }
        throw new IllegalArgumentException("Unknown chapter outline status: " + value);
    }
}
