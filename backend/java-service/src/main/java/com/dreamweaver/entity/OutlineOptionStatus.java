package com.dreamweaver.entity;

public enum OutlineOptionStatus {
    GENERATED("generated"),
    SELECTED("selected"),
    DISCARDED("discarded"),
    SUPERSEDED("superseded");

    private final String value;

    OutlineOptionStatus(String value) {
        this.value = value;
    }

    public String value() {
        return value;
    }

    public static OutlineOptionStatus fromValue(String value) {
        for (OutlineOptionStatus status : values()) {
            if (status.value.equals(value)) {
                return status;
            }
        }
        throw new IllegalArgumentException("Unknown outline option status: " + value);
    }
}
