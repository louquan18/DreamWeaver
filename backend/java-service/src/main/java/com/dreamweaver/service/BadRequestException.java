package com.dreamweaver.service;

public class BadRequestException extends RuntimeException {

    private final String error;

    public BadRequestException(String message) {
        this("bad_request", message);
    }

    public BadRequestException(String error, String message) {
        super(message);
        this.error = error;
    }

    public String error() {
        return error;
    }
}
