package com.dreamweaver.entity;

public enum NovelBlueprintStatus {
    GENERATED("generated"),
    CONFIRMED("confirmed"),
    SUPERSEDED("superseded");

    private final String value;

    NovelBlueprintStatus(String value) {
        this.value = value;
    }

    public String value() {
        return value;
    }

    public static NovelBlueprintStatus fromValue(String value) {
        for (NovelBlueprintStatus status : values()) {
            if (status.value.equals(value)) {
                return status;
            }
        }
        throw new IllegalArgumentException("Unknown novel blueprint status: " + value);
    }
}
