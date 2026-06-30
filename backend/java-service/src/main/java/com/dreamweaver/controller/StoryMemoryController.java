package com.dreamweaver.controller;

import java.util.UUID;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.dreamweaver.dto.StoryMemoryLibraryResponse;
import com.dreamweaver.service.StoryMemoryService;
import com.dreamweaver.service.StoryService;

@RestController
@RequestMapping("/api/stories/{storyId}/memories")
public class StoryMemoryController {

    private final StoryService storyService;
    private final StoryMemoryService storyMemoryService;

    public StoryMemoryController(
        StoryService storyService,
        StoryMemoryService storyMemoryService
    ) {
        this.storyService = storyService;
        this.storyMemoryService = storyMemoryService;
    }

    @GetMapping("/{memoryType}")
    public StoryMemoryLibraryResponse getMemory(
        @PathVariable UUID storyId,
        @PathVariable String memoryType
    ) {
        storyService.get(storyId);
        StoryMemoryService.MemoryLibrary library = storyMemoryService.library(storyId, memoryType);
        return StoryMemoryLibraryResponse.of(
            storyId,
            library.type(),
            library.items(),
            library.fingerprint()
        );
    }
}
