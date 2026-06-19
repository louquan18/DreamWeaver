package com.dreamweaver.service;

public class AiWorkerException extends RuntimeException {

    private final String error;

    public AiWorkerException(String error, String message) {
        super(message);
        this.error = error;
    }

    public String error() {
        return error;
    }
}
