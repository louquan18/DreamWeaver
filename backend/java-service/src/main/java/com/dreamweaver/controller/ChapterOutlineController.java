package com.dreamweaver.controller;

import java.util.UUID;

import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.dreamweaver.dto.ChapterOutlineConfirmRequest;
import com.dreamweaver.dto.ChapterOutlineConfirmResponse;
import com.dreamweaver.dto.ChapterOutlineResponse;
import com.dreamweaver.dto.ChapterResponse;
import com.dreamweaver.service.ChapterOutlineService;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/api/stories/{storyId}/chapters/{chapterId}/outlines")
public class ChapterOutlineController {

    private final ChapterOutlineService chapterOutlineService;

    public ChapterOutlineController(ChapterOutlineService chapterOutlineService) {
        this.chapterOutlineService = chapterOutlineService;
    }

    @PostMapping("/confirm")
    public ChapterOutlineConfirmResponse confirm(
        @PathVariable UUID storyId,
        @PathVariable UUID chapterId,
        @Valid @RequestBody ChapterOutlineConfirmRequest request
    ) {
        ChapterOutlineService.ConfirmedOutline result =
            chapterOutlineService.confirm(storyId, chapterId, request);
        return new ChapterOutlineConfirmResponse(
            ChapterResponse.from(result.chapter()),
            ChapterOutlineResponse.from(result.outline())
        );
    }
}
