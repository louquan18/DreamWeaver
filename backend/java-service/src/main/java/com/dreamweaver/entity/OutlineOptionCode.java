package com.dreamweaver.entity;

public enum OutlineOptionCode {
    A("A"),
    B("B"),
    C("C");

    private final String value;

    OutlineOptionCode(String value) {
        this.value = value;
    }

    public String value() {
        return value;
    }

    public static OutlineOptionCode fromValue(String value) {
        for (OutlineOptionCode code : values()) {
            if (code.value.equals(value)) {
                return code;
            }
        }
        throw new IllegalArgumentException("Unknown outline option code: " + value);
    }
}
