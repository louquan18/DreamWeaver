package com.dreamweaver.service;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.dreamweaver.dto.ChapterOutlineConfirmRequest;
import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.ChapterOutline;
import com.dreamweaver.entity.ChapterOutlineOption;
import com.dreamweaver.entity.ChapterOutlineStatus;
import com.dreamweaver.entity.ChapterWorkflowStage;
import com.dreamweaver.entity.OutlineOptionStatus;
import com.dreamweaver.repository.ChapterOutlineOptionRepository;
import com.dreamweaver.repository.ChapterOutlineRepository;
import com.dreamweaver.repository.ChapterRepository;
import com.dreamweaver.repository.StoryRepository;

@Service
public class ChapterOutlineService {

    private static final String OUTLINE_ALREADY_CONFIRMED = "outline_already_confirmed";
    private static final String OUTLINE_INVALID = "outline_invalid";
    private static final String OUTLINE_OPTION_NOT_SELECTABLE = "outline_option_not_selectable";

    private final StoryRepository storyRepository;
    private final ChapterRepository chapterRepository;
    private final ChapterOutlineRepository outlineRepository;
    private final ChapterOutlineOptionRepository optionRepository;

    public ChapterOutlineService(
        StoryRepository storyRepository,
        ChapterRepository chapterRepository,
        ChapterOutlineRepository outlineRepository,
        ChapterOutlineOptionRepository optionRepository
    ) {
        this.storyRepository = storyRepository;
        this.chapterRepository = chapterRepository;
        this.outlineRepository = outlineRepository;
        this.optionRepository = optionRepository;
    }

    @Transactional
    public ConfirmedOutline confirm(
        UUID storyId,
        UUID chapterId,
        ChapterOutlineConfirmRequest request
    ) {
        getStory(storyId);
        Chapter chapter = getChapter(storyId, chapterId);
        assertOutlineCanBeConfirmed(chapter);

        if (outlineRepository.existsByStoryIdAndChapterIdAndStatus(
            storyId,
            chapterId,
            ChapterOutlineStatus.CONFIRMED
        )) {
            throw new ConflictException(
                OUTLINE_ALREADY_CONFIRMED,
                "Chapter already has a confirmed outline: " + chapterId
            );
        }

        List<UUID> sourceOptionIds = normalizeSourceOptionIds(request);
        List<ChapterOutlineOption> sourceOptions = getSourceOptions(storyId, chapterId, sourceOptionIds);
        Map<String, Object> finalOutline = resolveFinalOutline(request, sourceOptions);
        validateFinalOutline(finalOutline);

        ChapterOutline outline = new ChapterOutline();
        outline.setStoryId(storyId);
        outline.setChapterId(chapterId);
        outline.setSourceOptionIds(sourceOptionIds);
        outline.setUserFeedback(request == null ? null : request.userFeedback());
        outline.setFinalOutline(finalOutline);
        outline.setStatus(ChapterOutlineStatus.CONFIRMED);
        outline.setConfirmedAt(OffsetDateTime.now());

        sourceOptions.forEach(this::assertSelectable);
        sourceOptions.forEach(option -> option.setStatus(OutlineOptionStatus.SELECTED));
        chapter.setWorkflowStage(ChapterWorkflowStage.OUTLINE_CONFIRMED);

        optionRepository.saveAll(sourceOptions);
        chapterRepository.save(chapter);
        try {
            outlineRepository.saveAndFlush(outline);
        } catch (DataIntegrityViolationException ex) {
            throw new ConflictException(
                OUTLINE_ALREADY_CONFIRMED,
                "Chapter already has a confirmed outline: " + chapterId
            );
        }

        return new ConfirmedOutline(chapter, outline);
    }

    private void getStory(UUID storyId) {
        storyRepository.findById(storyId)
            .orElseThrow(() -> new ResourceNotFoundException("Story not found: " + storyId));
    }

    private Chapter getChapter(UUID storyId, UUID chapterId) {
        return chapterRepository.findByIdAndStoryId(chapterId, storyId)
            .orElseThrow(() -> new ResourceNotFoundException("Chapter not found: " + chapterId));
    }

    private void assertOutlineCanBeConfirmed(Chapter chapter) {
        if (chapter.getWorkflowStage() != ChapterWorkflowStage.OUTLINE_OPTIONS_GENERATED) {
            throw new ConflictException(
                "outline_confirmation_stage_locked",
                "Chapter outline cannot be confirmed at workflow stage: " + chapter.getWorkflowStage().value()
            );
        }
    }

    private List<UUID> normalizeSourceOptionIds(ChapterOutlineConfirmRequest request) {
        if (request == null || request.sourceOptionIds() == null) {
            return List.of();
        }

        LinkedHashSet<UUID> uniqueIds = new LinkedHashSet<>();
        for (UUID optionId : request.sourceOptionIds()) {
            if (optionId == null) {
                throw invalid("sourceOptionIds must not contain null");
            }
            uniqueIds.add(optionId);
        }
        return new ArrayList<>(uniqueIds);
    }

    private List<ChapterOutlineOption> getSourceOptions(
        UUID storyId,
        UUID chapterId,
        List<UUID> sourceOptionIds
    ) {
        List<ChapterOutlineOption> options = new ArrayList<>();
        for (UUID optionId : sourceOptionIds) {
            ChapterOutlineOption option = optionRepository.findByIdAndStoryIdAndChapterId(
                optionId,
                storyId,
                chapterId
            ).orElseThrow(() -> new ResourceNotFoundException(
                "Chapter outline option not found: " + optionId
            ));
            options.add(option);
        }
        return options;
    }

    private Map<String, Object> resolveFinalOutline(
        ChapterOutlineConfirmRequest request,
        List<ChapterOutlineOption> sourceOptions
    ) {
        Map<String, Object> requestedOutline = request == null ? null : request.finalOutline();
        if (requestedOutline != null && !requestedOutline.isEmpty()) {
            return new LinkedHashMap<>(requestedOutline);
        }
        if (sourceOptions.size() == 1) {
            return deriveFinalOutline(sourceOptions.get(0));
        }
        throw new BadRequestException(
            OUTLINE_INVALID,
            "finalOutline is required when confirming without exactly one source option"
        );
    }

    private Map<String, Object> deriveFinalOutline(ChapterOutlineOption option) {
        Map<String, Object> outline = new LinkedHashMap<>();
        outline.put("titleCandidates", option.getTitleCandidates());
        outline.put("chapterGoal", option.getChapterGoal());
        outline.put("storySummary", option.getStorySummary());
        outline.put("sceneOutline", option.getSceneOutline());
        outline.put("charactersInvolved", option.getCharactersInvolved());
        outline.put("conflict", option.getConflict());
        outline.put("highlightMoment", option.getHighlightMoment());
        outline.put("foreshadowActions", option.getForeshadowActions());
        outline.put("memoryReferences", option.getMemoryReferences());
        outline.put("whyThisPlan", option.getWhyThisPlan());
        outline.put("endingHook", option.getEndingHook());
        outline.put("riskNotes", option.getRiskNotes());
        return outline;
    }

    private void assertSelectable(ChapterOutlineOption option) {
        if (option.getStatus() != OutlineOptionStatus.GENERATED) {
            throw new BadRequestException(
                OUTLINE_OPTION_NOT_SELECTABLE,
                "Only generated outline options can be selected: " + option.getId()
            );
        }
    }

    private void validateFinalOutline(Map<String, Object> finalOutline) {
        if (finalOutline == null || finalOutline.isEmpty()) {
            throw invalid("finalOutline is required");
        }
        requireNonEmptyList(finalOutline, "titleCandidates");
        requireText(finalOutline, "chapterGoal");
        requireText(finalOutline, "storySummary");
        requireSceneOutline(finalOutline);
        requireNonEmptyList(finalOutline, "charactersInvolved");
        requireNonEmptyMap(finalOutline, "conflict");
        requireText(finalOutline, "highlightMoment");
        requireText(finalOutline, "whyThisPlan");
        requireText(finalOutline, "endingHook");
        requireList(finalOutline, "foreshadowActions");
        requireList(finalOutline, "memoryReferences");
        requireList(finalOutline, "riskNotes");
    }

    private void requireText(Map<String, Object> values, String field) {
        Object value = values.get(field);
        if (!(value instanceof String text) || text.isBlank()) {
            throw invalid("finalOutline." + field + " is required");
        }
    }

    private void requireList(Map<String, Object> values, String field) {
        Object value = values.get(field);
        if (!(value instanceof List<?>)) {
            throw invalid("finalOutline." + field + " must be an array");
        }
    }

    private void requireNonEmptyList(Map<String, Object> values, String field) {
        Object value = values.get(field);
        if (!(value instanceof List<?> list) || list.isEmpty()) {
            throw invalid("finalOutline." + field + " is required");
        }
    }

    private void requireSceneOutline(Map<String, Object> values) {
        Object value = values.get("sceneOutline");
        if (!(value instanceof List<?> list) || list.size() < 3 || list.size() > 5) {
            throw invalid("finalOutline.sceneOutline must contain 3 to 5 scenes");
        }
    }

    private void requireNonEmptyMap(Map<String, Object> values, String field) {
        Object value = values.get(field);
        if (!(value instanceof Map<?, ?> map) || map.isEmpty()) {
            throw invalid("finalOutline." + field + " is required");
        }
    }

    private BadRequestException invalid(String message) {
        return new BadRequestException(OUTLINE_INVALID, message);
    }

    public record ConfirmedOutline(Chapter chapter, ChapterOutline outline) {
    }
}
