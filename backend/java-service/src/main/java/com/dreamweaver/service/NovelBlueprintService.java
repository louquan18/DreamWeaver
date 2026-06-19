package com.dreamweaver.service;

import java.time.OffsetDateTime;
import java.util.Map;
import java.util.UUID;

import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.dreamweaver.dto.AiBlueprintGenerateRequest;
import com.dreamweaver.dto.AiBlueprintGenerateResponse;
import com.dreamweaver.dto.NovelBlueprintConfirmRequest;
import com.dreamweaver.dto.NovelBlueprintGenerateRequest;
import com.dreamweaver.dto.NovelBlueprintUpdateRequest;
import com.dreamweaver.entity.NovelBlueprint;
import com.dreamweaver.entity.NovelBlueprintStatus;
import com.dreamweaver.entity.Story;
import com.dreamweaver.entity.StoryStatus;
import com.dreamweaver.repository.NovelBlueprintRepository;
import com.dreamweaver.repository.StoryRepository;

@Service
public class NovelBlueprintService {

    private static final String BLUEPRINT_ALREADY_CONFIRMED = "blueprint_already_confirmed";
    private static final String BLUEPRINT_NOT_EDITABLE = "blueprint_not_editable";
    private static final String BLUEPRINT_NOT_CONFIRMABLE = "blueprint_not_confirmable";
    private static final String AI_WORKER_ERROR = "ai_worker_error";

    private final NovelBlueprintRepository blueprintRepository;
    private final StoryRepository storyRepository;
    private final AiBlueprintClient aiBlueprintClient;

    public NovelBlueprintService(
        NovelBlueprintRepository blueprintRepository,
        StoryRepository storyRepository,
        AiBlueprintClient aiBlueprintClient
    ) {
        this.blueprintRepository = blueprintRepository;
        this.storyRepository = storyRepository;
        this.aiBlueprintClient = aiBlueprintClient;
    }

    @Transactional(readOnly = true)
    public NovelBlueprint getCurrent(UUID storyId) {
        getStory(storyId);
        return blueprintRepository
            .findFirstByStoryIdAndStatusOrderByCreatedAtDesc(storyId, NovelBlueprintStatus.CONFIRMED)
            .or(() -> blueprintRepository.findFirstByStoryIdAndStatusOrderByCreatedAtDesc(
                storyId,
                NovelBlueprintStatus.GENERATED
            ))
            .orElseThrow(() -> new ResourceNotFoundException(
                "Current blueprint not found for story: " + storyId
            ));
    }

    @Transactional
    public GeneratedBlueprint generate(UUID storyId, NovelBlueprintGenerateRequest request) {
        Story story = getStory(storyId);
        AiBlueprintGenerateResponse generated = aiBlueprintClient.generateBlueprint(
            storyId,
            AiBlueprintGenerateRequest.from(request)
        );
        validateGeneratedResponse(storyId, generated);

        NovelBlueprint blueprint = new NovelBlueprint();
        blueprint.setStoryId(storyId);
        blueprint.setSourcePrompt(generated.sourcePrompt());
        blueprint.setPremise(generated.premise());
        blueprint.setGenre(generated.genre());
        blueprint.setTone(generated.tone());
        blueprint.setProtagonist(generated.protagonist());
        blueprint.setMainThread(generated.mainThread());
        blueprint.setCoreConflict(generated.coreConflict());
        blueprint.setWorldSeed(generated.worldSeed());
        blueprint.setWritingPreferences(generated.writingPreferences());
        blueprint.setLockedFacts(generated.lockedFacts());
        blueprint.setStatus(NovelBlueprintStatus.GENERATED);
        return new GeneratedBlueprint(story, blueprintRepository.save(blueprint));
    }

    @Transactional
    public NovelBlueprint update(UUID storyId, UUID blueprintId, NovelBlueprintUpdateRequest request) {
        getStory(storyId);
        NovelBlueprint blueprint = getBlueprint(storyId, blueprintId);
        assertGenerated(blueprint, BLUEPRINT_NOT_EDITABLE, "Only generated blueprints can be edited");
        applyUpdate(blueprint, request);
        return blueprintRepository.save(blueprint);
    }

    @Transactional
    public ConfirmedBlueprint confirm(
        UUID storyId,
        UUID blueprintId,
        NovelBlueprintConfirmRequest request
    ) {
        Story story = getStory(storyId);
        NovelBlueprint blueprint = getBlueprint(storyId, blueprintId);
        assertGenerated(blueprint, BLUEPRINT_NOT_CONFIRMABLE, "Only generated blueprints can be confirmed");

        if (request != null && request.editedBlueprint() != null) {
            applyUpdate(blueprint, request.editedBlueprint());
        }

        validateConfirmable(blueprint);

        if (blueprintRepository.existsByStoryIdAndStatus(storyId, NovelBlueprintStatus.CONFIRMED)) {
            throw new ConflictException(
                BLUEPRINT_ALREADY_CONFIRMED,
                "Story already has a confirmed blueprint: " + storyId
            );
        }

        blueprint.setStatus(NovelBlueprintStatus.CONFIRMED);
        blueprint.setConfirmedAt(OffsetDateTime.now());
        story.setStatus(StoryStatus.WRITING);

        storyRepository.save(story);
        try {
            blueprintRepository.saveAndFlush(blueprint);
        } catch (DataIntegrityViolationException ex) {
            throw new ConflictException(
                BLUEPRINT_ALREADY_CONFIRMED,
                "Story already has a confirmed blueprint: " + storyId
            );
        }
        return new ConfirmedBlueprint(story, blueprint);
    }

    private Story getStory(UUID storyId) {
        return storyRepository.findById(storyId)
            .orElseThrow(() -> new ResourceNotFoundException("Story not found: " + storyId));
    }

    private NovelBlueprint getBlueprint(UUID storyId, UUID blueprintId) {
        return blueprintRepository.findByIdAndStoryId(blueprintId, storyId)
            .orElseThrow(() -> new ResourceNotFoundException("Blueprint not found: " + blueprintId));
    }

    private void assertGenerated(NovelBlueprint blueprint, String error, String message) {
        if (blueprint.getStatus() != NovelBlueprintStatus.GENERATED) {
            throw new ConflictException(error, message);
        }
    }

    private void applyUpdate(NovelBlueprint blueprint, NovelBlueprintUpdateRequest request) {
        if (request == null) {
            return;
        }
        if (request.sourcePrompt() != null) {
            blueprint.setSourcePrompt(request.sourcePrompt());
        }
        if (request.premise() != null) {
            blueprint.setPremise(request.premise());
        }
        if (request.genre() != null) {
            blueprint.setGenre(request.genre());
        }
        if (request.tone() != null) {
            blueprint.setTone(request.tone());
        }
        if (request.protagonist() != null) {
            blueprint.setProtagonist(request.protagonist());
        }
        if (request.mainThread() != null) {
            blueprint.setMainThread(request.mainThread());
        }
        if (request.coreConflict() != null) {
            blueprint.setCoreConflict(request.coreConflict());
        }
        if (request.worldSeed() != null) {
            blueprint.setWorldSeed(request.worldSeed());
        }
        if (request.writingPreferences() != null) {
            blueprint.setWritingPreferences(request.writingPreferences());
        }
        if (request.lockedFacts() != null) {
            blueprint.setLockedFacts(request.lockedFacts());
        }
    }

    private void validateConfirmable(NovelBlueprint blueprint) {
        if (isBlank(blueprint.getPremise())) {
            throw new BadRequestException("Blueprint premise is required");
        }
        if (isBlank(stringValue(blueprint.getProtagonist(), "name"))) {
            throw new BadRequestException("Blueprint protagonist.name is required");
        }
        if (isBlank(stringValue(blueprint.getMainThread(), "goal"))) {
            throw new BadRequestException("Blueprint mainThread.goal is required");
        }
        if (
            isBlank(stringValue(blueprint.getCoreConflict(), "external"))
                && isBlank(stringValue(blueprint.getCoreConflict(), "internal"))
        ) {
            throw new BadRequestException(
                "Blueprint coreConflict.external or coreConflict.internal is required"
            );
        }
        Object rules = blueprint.getWorldSeed() == null ? null : blueprint.getWorldSeed().get("rules");
        if (rules != null && !(rules instanceof java.util.List<?>)) {
            throw new BadRequestException("Blueprint worldSeed.rules must be an array");
        }
        if (blueprint.getLockedFacts() == null) {
            throw new BadRequestException("Blueprint lockedFacts must be an array");
        }
        for (Map<String, Object> lockedFact : blueprint.getLockedFacts()) {
            if (isBlank(stringValue(lockedFact, "text"))) {
                throw new BadRequestException("Blueprint lockedFacts[].text is required");
            }
        }
    }

    private void validateGeneratedResponse(UUID storyId, AiBlueprintGenerateResponse response) {
        if (response.storyId() != null && !response.storyId().equals(storyId.toString())) {
            throw new AiWorkerException(AI_WORKER_ERROR, "AI worker returned a blueprint for a different story");
        }
        if (isBlank(response.sourcePrompt())) {
            throw new AiWorkerException(AI_WORKER_ERROR, "AI worker returned blueprint without sourcePrompt");
        }
        if (isBlank(response.premise())) {
            throw new AiWorkerException(AI_WORKER_ERROR, "AI worker returned blueprint without premise");
        }
        if (response.protagonist() == null
            || response.mainThread() == null
            || response.coreConflict() == null
            || response.worldSeed() == null
            || response.writingPreferences() == null
            || response.lockedFacts() == null) {
            throw new AiWorkerException(AI_WORKER_ERROR, "AI worker returned incomplete blueprint JSON");
        }
        for (Map<String, Object> lockedFact : response.lockedFacts()) {
            if (lockedFact == null || isBlank(stringValue(lockedFact, "text"))) {
                throw new AiWorkerException(AI_WORKER_ERROR, "AI worker returned invalid lockedFacts");
            }
        }
    }

    private String stringValue(Map<String, Object> values, String key) {
        if (values == null) {
            return null;
        }
        Object value = values.get(key);
        return value == null ? null : value.toString();
    }

    private boolean isBlank(String value) {
        return value == null || value.isBlank();
    }

    public record ConfirmedBlueprint(Story story, NovelBlueprint blueprint) {
    }

    public record GeneratedBlueprint(Story story, NovelBlueprint blueprint) {
    }
}
