package com.dreamweaver.service;

import java.time.OffsetDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.dreamweaver.dto.ChapterGenerationCreateRequest;
import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.ChapterGeneration;
import com.dreamweaver.entity.ChapterStatus;
import com.dreamweaver.entity.GenerationStatus;
import com.dreamweaver.repository.ChapterGenerationRepository;

@Service
public class ChapterGenerationService {

    private final ChapterGenerationRepository generationRepository;
    private final ChapterService chapterService;

    public ChapterGenerationService(
        ChapterGenerationRepository generationRepository,
        ChapterService chapterService
    ) {
        this.generationRepository = generationRepository;
        this.chapterService = chapterService;
    }

    @Transactional
    public ChapterGeneration create(
        UUID storyId,
        UUID chapterId,
        ChapterGenerationCreateRequest request
    ) {
        chapterService.get(storyId, chapterId);

        Map<String, Object> requestSnapshot = new HashMap<>();
        requestSnapshot.put("target_words", request.targetWords());
        requestSnapshot.put("extra_prompt", request.extraPrompt());
        requestSnapshot.put("model_profile", modelProfile(request));
        requestSnapshot.put("auto_adopt", request.autoAdopt() == null || request.autoAdopt());
        requestSnapshot.put("source", "java-service");
        if (request.options() != null) {
            requestSnapshot.put("options", request.options());
        }

        ChapterGeneration generation = new ChapterGeneration();
        generation.setStoryId(storyId);
        generation.setChapterId(chapterId);
        generation.setUserId(request.userId() == null ? StoryService.DEFAULT_USER_ID : request.userId());
        generation.setStatus(GenerationStatus.QUEUED);
        generation.setRequest(requestSnapshot);
        generation.setModelProfile(modelProfile(request));
        return generationRepository.save(generation);
    }

    @Transactional(readOnly = true)
    public List<ChapterGeneration> list(UUID storyId, UUID chapterId) {
        chapterService.get(storyId, chapterId);
        return generationRepository.findByStoryIdAndChapterIdOrderByCreatedAtDesc(
            storyId,
            chapterId
        );
    }

    @Transactional(readOnly = true)
    public ChapterGeneration get(UUID storyId, UUID chapterId, UUID generationId) {
        return generationRepository.findByIdAndStoryIdAndChapterId(
            generationId,
            storyId,
            chapterId
        ).orElseThrow(() -> new ResourceNotFoundException(
            "Chapter generation not found: " + generationId
        ));
    }

    @Transactional
    public Chapter adopt(UUID storyId, UUID chapterId, UUID generationId) {
        Chapter chapter = chapterService.get(storyId, chapterId);
        ChapterGeneration generation = get(storyId, chapterId, generationId);

        if (generation.getStatus() != GenerationStatus.SUCCEEDED) {
            throw new BadRequestException("Only succeeded generation can be adopted");
        }

        chapter.setContent(generation.getDraft());
        chapter.setWordCount(generation.getWordCount());
        chapter.setLastGenerationId(generation.getId());
        chapter.setStatus(ChapterStatus.GENERATED);
        return chapterService.save(chapter);
    }

    private String modelProfile(ChapterGenerationCreateRequest request) {
        return request.modelProfile() == null || request.modelProfile().isBlank()
            ? "writing"
            : request.modelProfile();
    }

    @Transactional
    public ChapterGeneration markRunning(UUID storyId, UUID chapterId, UUID generationId) {
        Chapter chapter = chapterService.get(storyId, chapterId);
        ChapterGeneration generation = get(storyId, chapterId, generationId);

        generation.setStatus(GenerationStatus.RUNNING);
        generation.setStartedAt(OffsetDateTime.now());
        chapter.setStatus(ChapterStatus.GENERATING);
        chapterService.save(chapter);
        return generationRepository.save(generation);
    }

    @Transactional
    public ChapterGeneration completeFromStream(
        UUID storyId,
        UUID chapterId,
        UUID generationId,
        String draft,
        Integer wordCount,
        List<Map<String, Object>> executionHistory
    ) {
        Chapter chapter = chapterService.get(storyId, chapterId);
        ChapterGeneration generation = get(storyId, chapterId, generationId);

        generation.setStatus(GenerationStatus.SUCCEEDED);
        generation.setDraft(draft);
        generation.setWordCount(wordCount == null ? lengthOrNull(draft) : wordCount);
        generation.setExecutionHistory(executionHistory == null ? List.of() : executionHistory);
        generation.setCompletedAt(OffsetDateTime.now());
        generation = generationRepository.save(generation);

        if (autoAdopt(generation.getRequest())) {
            chapter.setContent(generation.getDraft());
            chapter.setWordCount(generation.getWordCount());
            chapter.setLastGenerationId(generation.getId());
            chapter.setStatus(ChapterStatus.GENERATED);
        } else {
            chapter.setStatus(
                chapter.getLastGenerationId() == null ? ChapterStatus.DRAFT : ChapterStatus.GENERATED
            );
        }
        chapterService.save(chapter);

        return generation;
    }

    @Transactional
    public ChapterGeneration failFromStream(
        UUID storyId,
        UUID chapterId,
        UUID generationId,
        String message
    ) {
        Chapter chapter = chapterService.get(storyId, chapterId);
        ChapterGeneration generation = get(storyId, chapterId, generationId);

        generation.setStatus(GenerationStatus.FAILED);
        generation.setErrorMessage(message);
        generation.setCompletedAt(OffsetDateTime.now());
        generation = generationRepository.save(generation);

        chapter.setStatus(
            chapter.getLastGenerationId() == null ? ChapterStatus.DRAFT : ChapterStatus.GENERATED
        );
        chapterService.save(chapter);

        return generation;
    }

    private boolean autoAdopt(Map<String, Object> requestSnapshot) {
        Object value = requestSnapshot.get("auto_adopt");
        return !(value instanceof Boolean autoAdopt) || autoAdopt;
    }

    private Integer lengthOrNull(String draft) {
        return draft == null ? null : draft.length();
    }
}
