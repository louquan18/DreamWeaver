package com.dreamweaver.service;

public class ConflictException extends RuntimeException {

    private final String error;

    public ConflictException(String error, String message) {
        super(message);
        this.error = error;
    }

    public String error() {
        return error;
    }
}
