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

import com.dreamweaver.dto.ChapterCreateRequest;
import com.dreamweaver.dto.ChapterResponse;
import com.dreamweaver.service.ChapterService;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/api/stories/{storyId}/chapters")
public class ChapterController {

    private final ChapterService chapterService;

    public ChapterController(ChapterService chapterService) {
        this.chapterService = chapterService;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ChapterResponse create(
        @PathVariable UUID storyId,
        @Valid @RequestBody ChapterCreateRequest request
    ) {
        return ChapterResponse.from(chapterService.create(storyId, request));
    }

    @GetMapping
    public List<ChapterResponse> list(@PathVariable UUID storyId) {
        return chapterService.list(storyId).stream()
            .map(ChapterResponse::from)
            .toList();
    }

    @GetMapping("/{chapterId}")
    public ChapterResponse get(
        @PathVariable UUID storyId,
        @PathVariable UUID chapterId
    ) {
        return ChapterResponse.from(chapterService.get(storyId, chapterId));
    }
}
