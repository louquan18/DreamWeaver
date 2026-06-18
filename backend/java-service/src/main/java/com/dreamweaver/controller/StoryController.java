package com.dreamweaver.controller;

import java.util.List;
import java.util.UUID;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import com.dreamweaver.dto.StoryCreateRequest;
import com.dreamweaver.dto.StoryResponse;
import com.dreamweaver.service.StoryService;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/api/stories")
public class StoryController {

    private final StoryService storyService;

    public StoryController(StoryService storyService) {
        this.storyService = storyService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public StoryResponse create(@Valid @RequestBody StoryCreateRequest request) {
        return StoryResponse.from(storyService.create(request));
    }

    @GetMapping
    public List<StoryResponse> list() {
        return storyService.list().stream()
            .map(StoryResponse::from)
            .toList();
    }

    @GetMapping("/{storyId}")
    public StoryResponse get(@PathVariable UUID storyId) {
        return StoryResponse.from(storyService.get(storyId));
    }
}
