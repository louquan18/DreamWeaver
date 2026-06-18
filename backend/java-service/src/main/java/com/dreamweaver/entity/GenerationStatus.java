package com.dreamweaver.entity;

public enum GenerationStatus {
    QUEUED("queued"),
    RUNNING("running"),
    SUCCEEDED("succeeded"),
    FAILED("failed"),
    CANCELLED("cancelled");

    private final String value;

    GenerationStatus(String value) {
        this.value = value;
    }

    public String value() {
        return value;
    }

    public static GenerationStatus fromValue(String value) {
        for (GenerationStatus status : values()) {
            if (status.value.equals(value)) {
                return status;
            }
        }
        throw new IllegalArgumentException("Unknown generation status: " + value);
    }
}
