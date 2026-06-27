package com.dreamweaver.controller;

import java.util.List;
import java.util.UUID;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import com.dreamweaver.dto.ChapterOutlineOptionsGenerateRequest;
import com.dreamweaver.dto.ChapterOutlineOptionsGenerateResponse;
import com.dreamweaver.dto.ChapterOutlineOptionResponse;
import com.dreamweaver.dto.ChapterResponse;
import com.dreamweaver.entity.ChapterOutlineOption;
import com.dreamweaver.repository.ChapterOutlineOptionRepository;
import com.dreamweaver.service.ChapterOutlineOptionService;

@RestController
@RequestMapping("/api/stories/{storyId}/chapters/{chapterId}/outline-options")
public class ChapterOutlineOptionController {

    private final ChapterOutlineOptionRepository optionRepository;
    private final ChapterOutlineOptionService optionService;

    public ChapterOutlineOptionController(
        ChapterOutlineOptionRepository optionRepository,
        ChapterOutlineOptionService optionService
    ) {
        this.optionRepository = optionRepository;
        this.optionService = optionService;
    }

    @GetMapping
    public List<ChapterOutlineOptionResponse> list(
        @PathVariable UUID storyId,
        @PathVariable UUID chapterId,
        @RequestParam(required = false) UUID groupId
    ) {
        List<ChapterOutlineOption> options = groupId == null
            ? optionRepository.findFirstByStoryIdAndChapterIdOrderByCreatedAtDesc(storyId, chapterId)
                .map(latest -> optionRepository.findByStoryIdAndChapterIdAndOptionGroupIdOrderByOptionCodeAsc(
                    storyId,
                    chapterId,
                    latest.getOptionGroupId()
                ))
                .orElse(List.of())
            : optionRepository.findByStoryIdAndChapterIdAndOptionGroupIdOrderByOptionCodeAsc(
                storyId,
                chapterId,
                groupId
            );
        return options.stream()
            .map(ChapterOutlineOptionResponse::from)
            .toList();
    }

    @PostMapping("/generate")
    public ChapterOutlineOptionsGenerateResponse generate(
        @PathVariable UUID storyId,
        @PathVariable UUID chapterId,
        @RequestBody(required = false) ChapterOutlineOptionsGenerateRequest request
    ) {
        ChapterOutlineOptionService.GeneratedOutlineOptions result = optionService.generate(
            storyId,
            chapterId,
            request
        );
        return new ChapterOutlineOptionsGenerateResponse(
            ChapterResponse.from(result.chapter()),
            result.options().stream()
                .map(ChapterOutlineOptionResponse::from)
                .toList()
        );
    }
}
