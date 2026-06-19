package com.dreamweaver.entity;

public enum OutlineOptionType {
    STEADY("steady"),
    CONFLICT("conflict"),
    FORESHADOW("foreshadow");

    private final String value;

    OutlineOptionType(String value) {
        this.value = value;
    }

    public String value() {
        return value;
    }

    public static OutlineOptionType fromValue(String value) {
        for (OutlineOptionType type : values()) {
            if (type.value.equals(value)) {
                return type;
            }
        }
        throw new IllegalArgumentException("Unknown outline option type: " + value);
    }
}
