package com.dreamweaver.entity;

public enum MemoryChangeSetStatus {
    PENDING("pending"),
    CONFIRMED("confirmed"),
    REJECTED("rejected");

    private final String value;

    MemoryChangeSetStatus(String value) {
        this.value = value;
    }

    public String value() {
        return value;
    }

    public static MemoryChangeSetStatus fromValue(String value) {
        for (MemoryChangeSetStatus status : values()) {
            if (status.value.equals(value)) {
                return status;
            }
        }
        throw new IllegalArgumentException("Unknown memory change set status: " + value);
    }
}
