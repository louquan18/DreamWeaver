package com.dreamweaver.service;

import java.time.OffsetDateTime;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.dreamweaver.dto.ChapterGenerationCreateRequest;
import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.ChapterGeneration;
import com.dreamweaver.entity.ChapterOutline;
import com.dreamweaver.entity.ChapterOutlineStatus;
import com.dreamweaver.entity.ChapterStatus;
import com.dreamweaver.entity.ChapterWorkflowStage;
import com.dreamweaver.entity.GenerationStatus;
import com.dreamweaver.entity.NovelBlueprint;
import com.dreamweaver.entity.NovelBlueprintStatus;
import com.dreamweaver.entity.Story;
import com.dreamweaver.repository.ChapterGenerationRepository;
import com.dreamweaver.repository.ChapterOutlineRepository;
import com.dreamweaver.repository.ChapterRepository;
import com.dreamweaver.repository.NovelBlueprintRepository;
import com.dreamweaver.repository.StoryRepository;

@Service
public class ChapterGenerationService {

    private static final String OUTLINE_NOT_CONFIRMED = "outline_not_confirmed";

    private static final Set<ChapterWorkflowStage> DRAFT_GENERATION_ALLOWED_STAGES = EnumSet.of(
        ChapterWorkflowStage.OUTLINE_CONFIRMED,
        ChapterWorkflowStage.DRAFT_GENERATING,
        ChapterWorkflowStage.DRAFT_GENERATED,
        ChapterWorkflowStage.REVIEWING,
        ChapterWorkflowStage.REVISION_REQUIRED,
        ChapterWorkflowStage.DRAFT_READY_FOR_CONFIRMATION,
        ChapterWorkflowStage.DRAFT_CONFIRMED,
        ChapterWorkflowStage.MEMORY_EXTRACTING,
        ChapterWorkflowStage.MEMORY_PENDING_CONFIRMATION,
        ChapterWorkflowStage.MEMORY_CONFIRMED
    );

    private static final Set<ChapterWorkflowStage> DRAFT_LOCKED_STAGES = EnumSet.of(
        ChapterWorkflowStage.DRAFT_CONFIRMED,
        ChapterWorkflowStage.MEMORY_EXTRACTING,
        ChapterWorkflowStage.MEMORY_PENDING_CONFIRMATION,
        ChapterWorkflowStage.MEMORY_CONFIRMED,
        ChapterWorkflowStage.CHAPTER_CONFIRMED
    );

    private final ChapterGenerationRepository generationRepository;
    private final ChapterService chapterService;
    private final StoryRepository storyRepository;
    private final NovelBlueprintRepository blueprintRepository;
    private final ChapterOutlineRepository outlineRepository;
    private final ChapterRepository chapterRepository;
    private final ChapterMemorySummaryService chapterMemorySummaryService;
    private final StoryMemoryService storyMemoryService;
    private final AdditionalMemoryRetriever additionalMemoryRetriever;

    public ChapterGenerationService(
        ChapterGenerationRepository generationRepository,
        ChapterService chapterService,
        StoryRepository storyRepository,
        NovelBlueprintRepository blueprintRepository,
        ChapterOutlineRepository outlineRepository,
        ChapterRepository chapterRepository,
        ChapterMemorySummaryService chapterMemorySummaryService,
        StoryMemoryService storyMemoryService,
        AdditionalMemoryRetriever additionalMemoryRetriever
    ) {
        this.generationRepository = generationRepository;
        this.chapterService = chapterService;
        this.storyRepository = storyRepository;
        this.blueprintRepository = blueprintRepository;
        this.outlineRepository = outlineRepository;
        this.chapterRepository = chapterRepository;
        this.chapterMemorySummaryService = chapterMemorySummaryService;
        this.storyMemoryService = storyMemoryService;
        this.additionalMemoryRetriever = additionalMemoryRetriever;
    }

    @Transactional
    public ChapterGeneration create(
        UUID storyId,
        UUID chapterId,
        ChapterGenerationCreateRequest request
    ) {
        Chapter chapter = chapterService.get(storyId, chapterId);
        assertOutlineConfirmed(chapter);

        Map<String, Object> requestSnapshot = new HashMap<>();
        requestSnapshot.put("target_words", request.targetWords());
        requestSnapshot.put("extra_prompt", request.extraPrompt());
        requestSnapshot.put("model_profile", modelProfile(request));
        requestSnapshot.put("auto_adopt", request.autoAdopt() == null || request.autoAdopt());
        requestSnapshot.put("source", "java-service");
        requestSnapshot.put("quality_gate", "draft-review-v1");
        requestSnapshot.put("writing_context", buildWritingContext(storyId, chapter));
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

    @Transactional
    public Chapter confirmDraft(UUID storyId, UUID chapterId, UUID generationId) {
        Chapter chapter = chapterService.get(storyId, chapterId);
        ChapterGeneration generation = get(storyId, chapterId, generationId);

        if (DRAFT_LOCKED_STAGES.contains(chapter.getWorkflowStage())
            && !generationId.equals(chapter.getLastGenerationId())) {
            throw new ConflictException(
                "draft_already_confirmed",
                "Chapter draft has already been confirmed with another generation: " + chapterId
            );
        }

        assertConfirmableGeneration(generation);
        assertQualityGatePassed(generation);

        if (DRAFT_LOCKED_STAGES.contains(chapter.getWorkflowStage())) {
            return chapter;
        }

        chapter.setContent(generation.getDraft());
        chapter.setWordCount(
            generation.getWordCount() == null ? lengthOrNull(generation.getDraft()) : generation.getWordCount()
        );
        chapter.setLastGenerationId(generation.getId());
        chapter.setStatus(ChapterStatus.APPROVED);
        chapter.setWorkflowStage(ChapterWorkflowStage.DRAFT_CONFIRMED);
        return chapterService.save(chapter);
    }

    private void assertConfirmableGeneration(ChapterGeneration generation) {
        if (generation.getStatus() != GenerationStatus.SUCCEEDED) {
            throw new BadRequestException(
                "generation_not_succeeded",
                "Only succeeded generation can be confirmed"
            );
        }
        if (generation.getDraft() == null || generation.getDraft().isBlank()) {
            throw new BadRequestException(
                "generation_draft_empty",
                "Succeeded generation has no draft content to confirm"
            );
        }
    }

    private String modelProfile(ChapterGenerationCreateRequest request) {
        return request.modelProfile() == null || request.modelProfile().isBlank()
            ? "writing"
            : request.modelProfile();
    }

    private void assertOutlineConfirmed(Chapter chapter) {
        if (chapter.getWorkflowStage() == ChapterWorkflowStage.CHAPTER_CONFIRMED) {
            throw new ConflictException(
                "chapter_already_confirmed",
                "Chapter has already been confirmed and frozen: " + chapter.getId()
            );
        }
        if (!DRAFT_GENERATION_ALLOWED_STAGES.contains(chapter.getWorkflowStage())) {
            throw new BadRequestException(
                OUTLINE_NOT_CONFIRMED,
                "Chapter outline must be confirmed before draft generation: " + chapter.getId()
            );
        }
    }

    private Map<String, Object> buildWritingContext(UUID storyId, Chapter chapter) {
        Story story = storyRepository.findById(storyId)
            .orElseThrow(() -> new ResourceNotFoundException("Story not found: " + storyId));
        NovelBlueprint blueprint = blueprintRepository
            .findFirstByStoryIdAndStatusOrderByCreatedAtDesc(storyId, NovelBlueprintStatus.CONFIRMED)
            .orElseThrow(() -> new BadRequestException(
                "blueprint_not_confirmed",
                "Story blueprint must be confirmed before draft generation: " + storyId
            ));
        ChapterOutline outline = outlineRepository
            .findFirstByStoryIdAndChapterIdAndStatusOrderByCreatedAtDesc(
                storyId,
                chapter.getId(),
                ChapterOutlineStatus.CONFIRMED
            )
            .orElseThrow(() -> new BadRequestException(
                OUTLINE_NOT_CONFIRMED,
                "Chapter outline must be confirmed before draft generation: " + chapter.getId()
            ));

        StoryMemoryService.MemoryContext memoryContext = storyMemoryService.buildOutlineMemoryContext(storyId);
        Map<String, Object> storyContext = storyContext(story);
        Map<String, Object> chapterContext = chapterContext(chapter);
        Map<String, Object> blueprintContext = blueprintContext(blueprint);
        Map<String, Object> outlineContext = outlineContext(outline);

        Map<String, Object> context = new HashMap<>();
        context.put("story", storyContext);
        context.put("chapter", chapterContext);
        context.put("blueprint", blueprintContext);
        context.put("confirmedOutline", outlineContext);
        context.put("recentChapters", recentChapterContexts(storyId, chapter));
        context.put("timeline", memoryContext.timeline());
        context.put("characters", memoryContext.characters());
        context.put("world", memoryContext.world());
        context.put("foreshadows", memoryContext.foreshadows());
        context.put("additionalMemory", additionalMemoryRetriever.retrieve(
            storyId,
            storyContext,
            chapterContext,
            blueprintContext,
            outlineContext,
            Map.of()
        ));
        context.put("contextMetadata", contextMetadata());
        return context;
    }

    private Map<String, Object> contextMetadata() {
        return Map.of(
            "version", 1,
            "policy", "structured-memory-v1",
            "assembledAt", OffsetDateTime.now().toString(),
            "limits", Map.of(
                "recentFullTextChapters", ChapterMemorySummaryService.RECENT_FULL_TEXT_CHAPTERS,
                "recentSummaryChapters", ChapterMemorySummaryService.RECENT_SUMMARY_CHAPTERS,
                "timeline", StoryMemoryService.TIMELINE_LIMIT,
                "characters", StoryMemoryService.CHARACTER_LIMIT,
                "world", StoryMemoryService.WORLD_LIMIT,
                "foreshadows", StoryMemoryService.FORESHADOW_LIMIT,
                "additionalMemory", StoryMemoryService.ADDITIONAL_MEMORY_LIMIT
            )
        );
    }

    private Map<String, Object> storyContext(Story story) {
        Map<String, Object> values = new HashMap<>();
        values.put("id", story.getId());
        values.put("title", story.getTitle());
        values.put("description", story.getDescription());
        values.put("genre", story.getGenre());
        values.put("targetWords", story.getTargetWords());
        values.put("status", story.getStatus().value());
        return values;
    }

    private Map<String, Object> chapterContext(Chapter chapter) {
        Map<String, Object> values = new HashMap<>();
        values.put("id", chapter.getId());
        values.put("storyId", chapter.getStoryId());
        values.put("chapterNumber", chapter.getChapterNumber());
        values.put("title", chapter.getTitle());
        values.put("status", chapter.getStatus().value());
        values.put("workflowStage", chapter.getWorkflowStage().value());
        return values;
    }

    private Map<String, Object> blueprintContext(NovelBlueprint blueprint) {
        Map<String, Object> values = new HashMap<>();
        values.put("id", blueprint.getId());
        values.put("storyId", blueprint.getStoryId());
        values.put("sourcePrompt", blueprint.getSourcePrompt());
        values.put("premise", blueprint.getPremise());
        values.put("genre", blueprint.getGenre());
        values.put("tone", blueprint.getTone());
        values.put("protagonist", blueprint.getProtagonist());
        values.put("mainThread", blueprint.getMainThread());
        values.put("coreConflict", blueprint.getCoreConflict());
        values.put("worldSeed", blueprint.getWorldSeed());
        values.put("writingPreferences", blueprint.getWritingPreferences());
        values.put("lockedFacts", blueprint.getLockedFacts());
        values.put("status", blueprint.getStatus().value());
        return values;
    }

    private Map<String, Object> outlineContext(ChapterOutline outline) {
        Map<String, Object> values = new HashMap<>();
        values.put("id", outline.getId());
        values.put("storyId", outline.getStoryId());
        values.put("chapterId", outline.getChapterId());
        values.put("sourceOptionIds", outline.getSourceOptionIds());
        values.put("userFeedback", outline.getUserFeedback());
        values.put("finalOutline", outline.getFinalOutline());
        values.put("status", outline.getStatus().value());
        return values;
    }

    private List<Map<String, Object>> recentChapterContexts(UUID storyId, Chapter currentChapter) {
        return chapterMemorySummaryService.recentChapterContexts(
            storyId,
            currentChapter,
            chapterRepository.findByStoryIdOrderByChapterNumberAsc(storyId)
        );
    }

    @Transactional
    public ChapterGeneration markRunning(UUID storyId, UUID chapterId, UUID generationId) {
        Chapter chapter = chapterService.get(storyId, chapterId);
        ChapterGeneration generation = get(storyId, chapterId, generationId);

        generation.setStatus(GenerationStatus.RUNNING);
        generation.setStartedAt(OffsetDateTime.now());
        if (!DRAFT_LOCKED_STAGES.contains(chapter.getWorkflowStage())) {
            chapter.setStatus(ChapterStatus.GENERATING);
            chapter.setWorkflowStage(ChapterWorkflowStage.DRAFT_GENERATING);
            chapterService.save(chapter);
        }
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
        return completeFromStream(
            storyId,
            chapterId,
            generationId,
            draft,
            wordCount,
            executionHistory,
            null,
            null
        );
    }

    @Transactional
    public ChapterGeneration markReviewing(UUID storyId, UUID chapterId, UUID generationId) {
        Chapter chapter = chapterService.get(storyId, chapterId);
        ChapterGeneration generation = get(storyId, chapterId, generationId);

        if (!DRAFT_LOCKED_STAGES.contains(chapter.getWorkflowStage())) {
            chapter.setWorkflowStage(ChapterWorkflowStage.REVIEWING);
            chapterService.save(chapter);
        }
        return generation;
    }

    @Transactional
    public ChapterGeneration completeFromStream(
        UUID storyId,
        UUID chapterId,
        UUID generationId,
        String draft,
        Integer wordCount,
        List<Map<String, Object>> executionHistory,
        Map<String, Object> consistencyReport,
        Map<String, Object> reviewReport
    ) {
        Chapter chapter = chapterService.get(storyId, chapterId);
        ChapterGeneration generation = get(storyId, chapterId, generationId);
        boolean blocked = qualityGateMissing(generation.getRequest(), consistencyReport, reviewReport)
            || qualityGateBlocked(consistencyReport)
            || qualityGateBlocked(reviewReport);

        generation.setStatus(GenerationStatus.SUCCEEDED);
        generation.setDraft(draft);
        generation.setWordCount(wordCount == null ? lengthOrNull(draft) : wordCount);
        generation.setExecutionHistory(executionHistory == null ? List.of() : executionHistory);
        generation.setConsistencyReport(consistencyReport);
        generation.setReviewReport(reviewReport);
        generation.setCompletedAt(OffsetDateTime.now());
        generation = generationRepository.save(generation);

        if (!DRAFT_LOCKED_STAGES.contains(chapter.getWorkflowStage())) {
            if (!blocked && autoAdopt(generation.getRequest())) {
                chapter.setContent(generation.getDraft());
                chapter.setWordCount(generation.getWordCount());
                chapter.setLastGenerationId(generation.getId());
                chapter.setStatus(ChapterStatus.GENERATED);
            } else {
                chapter.setStatus(
                    chapter.getLastGenerationId() == null ? ChapterStatus.DRAFT : ChapterStatus.GENERATED
                );
            }
            chapter.setWorkflowStage(
                blocked ? ChapterWorkflowStage.REVISION_REQUIRED : ChapterWorkflowStage.DRAFT_READY_FOR_CONFIRMATION
            );
            chapterService.save(chapter);
        }

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

        if (!DRAFT_LOCKED_STAGES.contains(chapter.getWorkflowStage())) {
            chapter.setStatus(
                chapter.getLastGenerationId() == null ? ChapterStatus.DRAFT : ChapterStatus.GENERATED
            );
            if (chapter.getWorkflowStage() == ChapterWorkflowStage.DRAFT_GENERATING) {
                chapter.setWorkflowStage(ChapterWorkflowStage.REVISION_REQUIRED);
            }
            chapterService.save(chapter);
        }

        return generation;
    }

    private boolean autoAdopt(Map<String, Object> requestSnapshot) {
        Object value = requestSnapshot.get("auto_adopt");
        return !(value instanceof Boolean) || (Boolean) value;
    }

    private void assertQualityGatePassed(ChapterGeneration generation) {
        if (!qualityGateRequired(generation.getRequest())) {
            return;
        }
        Map<String, Object> consistencyReport = generation.getConsistencyReport();
        Map<String, Object> reviewReport = generation.getReviewReport();
        if (consistencyReport == null || consistencyReport.isEmpty()
            || reviewReport == null || reviewReport.isEmpty()) {
            throw new BadRequestException(
                "draft_quality_gate_missing",
                "Draft quality gate reports are required before confirmation"
            );
        }
        if (qualityGateBlocked(consistencyReport) || qualityGateBlocked(reviewReport)) {
            throw new BadRequestException(
                "draft_quality_gate_blocked",
                "Draft has blocking review or consistency issues"
            );
        }
    }

    private boolean qualityGateRequired(Map<String, Object> requestSnapshot) {
        return "draft-review-v1".equals(requestSnapshot.get("quality_gate"));
    }

    private boolean qualityGateMissing(
        Map<String, Object> requestSnapshot,
        Map<String, Object> consistencyReport,
        Map<String, Object> reviewReport
    ) {
        if (!qualityGateRequired(requestSnapshot)) {
            return false;
        }
        return consistencyReport == null || consistencyReport.isEmpty()
            || reviewReport == null || reviewReport.isEmpty();
    }

    private boolean qualityGateBlocked(Map<String, Object> report) {
        if (report == null || report.isEmpty()) {
            return false;
        }
        Object blocking = report.get("blocking");
        if (blocking instanceof Boolean && (Boolean) blocking) {
            return true;
        }
        Object issues = report.get("issues");
        if (issues instanceof List<?>) {
            for (Object item : (List<?>) issues) {
                if (item instanceof Map<?, ?>) {
                    Map<?, ?> issue = (Map<?, ?>) item;
                    Object issueBlocking = issue.get("blocking");
                    Object severity = issue.get("severity");
                    if ((issueBlocking instanceof Boolean && (Boolean) issueBlocking) || "P0".equals(severity)) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    private Integer lengthOrNull(String draft) {
        return draft == null ? null : draft.length();
    }
}
