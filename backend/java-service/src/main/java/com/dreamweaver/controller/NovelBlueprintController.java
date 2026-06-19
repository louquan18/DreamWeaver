package com.dreamweaver.controller;

import java.util.UUID;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.dreamweaver.dto.NovelBlueprintConfirmRequest;
import com.dreamweaver.dto.NovelBlueprintConfirmResponse;
import com.dreamweaver.dto.NovelBlueprintGenerateRequest;
import com.dreamweaver.dto.NovelBlueprintResponse;
import com.dreamweaver.dto.NovelBlueprintUpdateRequest;
import com.dreamweaver.dto.StoryResponse;
import com.dreamweaver.service.NovelBlueprintService;

import jakarta.validation.Valid;

@RestController
@RequestMapping("/api/stories/{storyId}/blueprints")
public class NovelBlueprintController {

    private final NovelBlueprintService blueprintService;

    public NovelBlueprintController(NovelBlueprintService blueprintService) {
        this.blueprintService = blueprintService;
    }

    @GetMapping("/current")
    public NovelBlueprintResponse getCurrent(@PathVariable UUID storyId) {
        return NovelBlueprintResponse.from(blueprintService.getCurrent(storyId));
    }

    @PostMapping("/generate")
    public NovelBlueprintConfirmResponse generate(
        @PathVariable UUID storyId,
        @Valid @RequestBody NovelBlueprintGenerateRequest request
    ) {
        NovelBlueprintService.GeneratedBlueprint result = blueprintService.generate(storyId, request);
        return new NovelBlueprintConfirmResponse(
            StoryResponse.from(result.story()),
            NovelBlueprintResponse.from(result.blueprint())
        );
    }

    @PatchMapping("/{blueprintId}")
    public NovelBlueprintResponse update(
        @PathVariable UUID storyId,
        @PathVariable UUID blueprintId,
        @Valid @RequestBody NovelBlueprintUpdateRequest request
    ) {
        return NovelBlueprintResponse.from(blueprintService.update(storyId, blueprintId, request));
    }

    @PostMapping("/{blueprintId}/confirm")
    public NovelBlueprintConfirmResponse confirm(
        @PathVariable UUID storyId,
        @PathVariable UUID blueprintId,
        @Valid @RequestBody(required = false) NovelBlueprintConfirmRequest request
    ) {
        NovelBlueprintService.ConfirmedBlueprint result =
            blueprintService.confirm(storyId, blueprintId, request);
        return new NovelBlueprintConfirmResponse(
            StoryResponse.from(result.story()),
            NovelBlueprintResponse.from(result.blueprint())
        );
    }
}
