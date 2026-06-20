package com.dreamweaver.controller;

import java.util.List;
import java.util.UUID;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.dreamweaver.dto.MemoryChangeSetConfirmRequest;
import com.dreamweaver.dto.MemoryChangeSetExtractRequest;
import com.dreamweaver.dto.MemoryChangeSetFreezeResponse;
import com.dreamweaver.dto.MemoryChangeSetResponse;
import com.dreamweaver.dto.MemoryChangeSetUpdateRequest;
import com.dreamweaver.service.MemoryChangeSetService;

@RestController
@RequestMapping("/api/stories/{storyId}/chapters/{chapterId}/memory-change-sets")
public class MemoryChangeSetController {

    private final MemoryChangeSetService changeSetService;

    public MemoryChangeSetController(MemoryChangeSetService changeSetService) {
        this.changeSetService = changeSetService;
    }

    @PostMapping("/extract")
    public MemoryChangeSetResponse extract(
        @PathVariable UUID storyId,
        @PathVariable UUID chapterId,
        @RequestBody(required = false) MemoryChangeSetExtractRequest request
    ) {
        return MemoryChangeSetResponse.from(changeSetService.extract(
            storyId,
            chapterId,
            request == null ? new MemoryChangeSetExtractRequest(null, null) : request
        ));
    }

    @GetMapping
    public List<MemoryChangeSetResponse> list(
        @PathVariable UUID storyId,
        @PathVariable UUID chapterId
    ) {
        return changeSetService.list(storyId, chapterId).stream()
            .map(MemoryChangeSetResponse::from)
            .toList();
    }

    @GetMapping("/{changeSetId}")
    public MemoryChangeSetResponse get(
        @PathVariable UUID storyId,
        @PathVariable UUID chapterId,
        @PathVariable UUID changeSetId
    ) {
        return MemoryChangeSetResponse.from(changeSetService.get(storyId, chapterId, changeSetId));
    }

    @PatchMapping("/{changeSetId}")
    public MemoryChangeSetResponse update(
        @PathVariable UUID storyId,
        @PathVariable UUID chapterId,
        @PathVariable UUID changeSetId,
        @RequestBody MemoryChangeSetUpdateRequest request
    ) {
        return MemoryChangeSetResponse.from(changeSetService.update(
            storyId,
            chapterId,
            changeSetId,
            request
        ));
    }

    @PostMapping("/{changeSetId}/confirm")
    public MemoryChangeSetResponse confirm(
        @PathVariable UUID storyId,
        @PathVariable UUID chapterId,
        @PathVariable UUID changeSetId,
        @RequestBody(required = false) MemoryChangeSetConfirmRequest request
    ) {
        return MemoryChangeSetResponse.from(changeSetService.confirm(
            storyId,
            chapterId,
            changeSetId,
            request == null ? new MemoryChangeSetConfirmRequest(null) : request
        ));
    }

    @PostMapping("/{changeSetId}/freeze")
    public MemoryChangeSetFreezeResponse freeze(
        @PathVariable UUID storyId,
        @PathVariable UUID chapterId,
        @PathVariable UUID changeSetId
    ) {
        return MemoryChangeSetFreezeResponse.from(changeSetService.freeze(storyId, chapterId, changeSetId));
    }
}
