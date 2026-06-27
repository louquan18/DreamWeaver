package com.dreamweaver.service;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.EnumSet;
import java.util.Set;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.dreamweaver.dto.AiOutlineOptionResponse;
import com.dreamweaver.dto.AiOutlineOptionsGenerateRequest;
import com.dreamweaver.dto.AiOutlineOptionsGenerateResponse;
import com.dreamweaver.dto.ChapterOutlineOptionsGenerateRequest;
import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.ChapterOutlineOption;
import com.dreamweaver.entity.ChapterWorkflowStage;
import com.dreamweaver.entity.NovelBlueprint;
import com.dreamweaver.entity.NovelBlueprintStatus;
import com.dreamweaver.entity.OutlineOptionCode;
import com.dreamweaver.entity.OutlineOptionStatus;
import com.dreamweaver.entity.OutlineOptionType;
import com.dreamweaver.entity.Story;
import com.dreamweaver.repository.ChapterOutlineOptionRepository;
import com.dreamweaver.repository.ChapterRepository;
import com.dreamweaver.repository.NovelBlueprintRepository;
import com.dreamweaver.repository.StoryRepository;
import com.dreamweaver.service.StoryMemoryService.MemoryContext;

@Service
public class ChapterOutlineOptionService {

    private static final String AI_WORKER_ERROR = "ai_worker_error";
    private static final Set<ChapterWorkflowStage> OUTLINE_OPTION_GENERATION_ALLOWED_STAGES = EnumSet.of(
        ChapterWorkflowStage.CHAPTER_CREATED,
        ChapterWorkflowStage.OUTLINE_OPTIONS_GENERATING,
        ChapterWorkflowStage.OUTLINE_OPTIONS_GENERATED
    );

    private final StoryRepository storyRepository;
    private final ChapterRepository chapterRepository;
    private final NovelBlueprintRepository blueprintRepository;
    private final ChapterOutlineOptionRepository optionRepository;
    private final AiOutlineClient aiOutlineClient;
    private final StoryMemoryService storyMemoryService;
    private final ChapterMemorySummaryService chapterMemorySummaryService;
    private final AdditionalMemoryRetriever additionalMemoryRetriever;

    public ChapterOutlineOptionService(
        StoryRepository storyRepository,
        ChapterRepository chapterRepository,
        NovelBlueprintRepository blueprintRepository,
        ChapterOutlineOptionRepository optionRepository,
        AiOutlineClient aiOutlineClient,
        StoryMemoryService storyMemoryService,
        ChapterMemorySummaryService chapterMemorySummaryService,
        AdditionalMemoryRetriever additionalMemoryRetriever
    ) {
        this.storyRepository = storyRepository;
        this.chapterRepository = chapterRepository;
        this.blueprintRepository = blueprintRepository;
        this.optionRepository = optionRepository;
        this.aiOutlineClient = aiOutlineClient;
        this.storyMemoryService = storyMemoryService;
        this.chapterMemorySummaryService = chapterMemorySummaryService;
        this.additionalMemoryRetriever = additionalMemoryRetriever;
    }

    @Transactional
    public GeneratedOutlineOptions generate(
        UUID storyId,
        UUID chapterId,
        ChapterOutlineOptionsGenerateRequest request
    ) {
        Story story = getStory(storyId);
        Chapter chapter = getChapter(storyId, chapterId);
        assertOutlineOptionsCanBeGenerated(chapter);
        NovelBlueprint blueprint = getConfirmedBlueprint(storyId);
        UUID optionGroupId = UUID.randomUUID();
        MemoryContext memoryContext = storyMemoryService.buildOutlineMemoryContext(storyId);
        Map<String, Object> storyContext = storyContext(story);
        Map<String, Object> chapterContext = chapterContext(chapter);
        Map<String, Object> blueprintContext = blueprintContext(blueprint);
        Map<String, Object> authorIntent = request == null ? null : request.authorIntent();

        AiOutlineOptionsGenerateResponse generated = aiOutlineClient.generateOutlineOptions(
            storyId,
            chapterId,
            new AiOutlineOptionsGenerateRequest(
                optionGroupId.toString(),
                storyContext,
                chapterContext,
                blueprintContext,
                authorIntent,
                recentChapterContexts(storyId, chapter),
                memoryContext.timeline(),
                memoryContext.characters(),
                memoryContext.world(),
                memoryContext.foreshadows(),
                additionalMemoryRetriever.retrieve(
                    storyId,
                    storyContext,
                    chapterContext,
                    blueprintContext,
                    Map.of(),
                    authorIntent
                )
            )
        );
        validateGeneratedResponse(storyId, chapterId, optionGroupId, generated);

        List<ChapterOutlineOption> options = generated.options().stream()
            .map(option -> toEntity(storyId, chapterId, optionGroupId, option))
            .toList();
        List<ChapterOutlineOption> savedOptions = optionRepository.saveAll(options);

        chapter.setWorkflowStage(ChapterWorkflowStage.OUTLINE_OPTIONS_GENERATED);
        chapterRepository.save(chapter);

        return new GeneratedOutlineOptions(chapter, savedOptions);
    }

    private Story getStory(UUID storyId) {
        return storyRepository.findById(storyId)
            .orElseThrow(() -> new ResourceNotFoundException("Story not found: " + storyId));
    }

    private Chapter getChapter(UUID storyId, UUID chapterId) {
        return chapterRepository.findByIdAndStoryId(chapterId, storyId)
            .orElseThrow(() -> new ResourceNotFoundException("Chapter not found: " + chapterId));
    }

    private NovelBlueprint getConfirmedBlueprint(UUID storyId) {
        return blueprintRepository
            .findFirstByStoryIdAndStatusOrderByCreatedAtDesc(storyId, NovelBlueprintStatus.CONFIRMED)
            .orElseThrow(() -> new BadRequestException(
                "blueprint_not_confirmed",
                "Story blueprint must be confirmed before outline generation: " + storyId
            ));
    }

    private void assertOutlineOptionsCanBeGenerated(Chapter chapter) {
        if (!OUTLINE_OPTION_GENERATION_ALLOWED_STAGES.contains(chapter.getWorkflowStage())) {
            throw new ConflictException(
                "outline_options_stage_locked",
                "Chapter outline options cannot be generated after outline confirmation: " + chapter.getId()
            );
        }
    }

    private Map<String, Object> storyContext(Story story) {
        Map<String, Object> values = new LinkedHashMap<>();
        values.put("id", story.getId());
        values.put("title", story.getTitle());
        values.put("description", story.getDescription());
        values.put("genre", story.getGenre());
        values.put("targetWords", story.getTargetWords());
        values.put("status", story.getStatus().value());
        return values;
    }

    private Map<String, Object> chapterContext(Chapter chapter) {
        Map<String, Object> values = new LinkedHashMap<>();
        values.put("id", chapter.getId());
        values.put("storyId", chapter.getStoryId());
        values.put("chapterNumber", chapter.getChapterNumber());
        values.put("title", chapter.getTitle());
        values.put("status", chapter.getStatus().value());
        values.put("workflowStage", chapter.getWorkflowStage().value());
        return values;
    }

    private Map<String, Object> blueprintContext(NovelBlueprint blueprint) {
        Map<String, Object> values = new LinkedHashMap<>();
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

    private List<Map<String, Object>> recentChapterContexts(UUID storyId, Chapter currentChapter) {
        return chapterMemorySummaryService.recentChapterContexts(
            storyId,
            currentChapter,
            chapterRepository.findByStoryIdOrderByChapterNumberAsc(storyId)
        );
    }

    private void validateGeneratedResponse(
        UUID storyId,
        UUID chapterId,
        UUID optionGroupId,
        AiOutlineOptionsGenerateResponse generated
    ) {
        if (generated == null || generated.options() == null || generated.options().size() != 3) {
            throw new AiWorkerException(AI_WORKER_ERROR, "AI worker must return exactly three outline options");
        }
        if (generated.storyId() != null && !generated.storyId().equals(storyId.toString())) {
            throw new AiWorkerException(AI_WORKER_ERROR, "AI worker returned options for a different story");
        }
        if (generated.chapterId() != null && !generated.chapterId().equals(chapterId.toString())) {
            throw new AiWorkerException(AI_WORKER_ERROR, "AI worker returned options for a different chapter");
        }
        if (generated.optionGroupId() != null && !generated.optionGroupId().equals(optionGroupId.toString())) {
            throw new AiWorkerException(AI_WORKER_ERROR, "AI worker returned options for a different group");
        }
    }

    private ChapterOutlineOption toEntity(
        UUID storyId,
        UUID chapterId,
        UUID optionGroupId,
        AiOutlineOptionResponse generated
    ) {
        ChapterOutlineOption option = new ChapterOutlineOption();
        option.setStoryId(storyId);
        option.setChapterId(chapterId);
        option.setOptionGroupId(optionGroupId);
        option.setOptionCode(OutlineOptionCode.fromValue(generated.optionCode()));
        option.setOptionType(OutlineOptionType.fromValue(generated.optionType()));
        option.setTitleCandidates(generated.titleCandidates());
        option.setChapterGoal(generated.chapterGoal());
        option.setStorySummary(generated.storySummary());
        option.setSceneOutline(generated.sceneOutline());
        option.setCharactersInvolved(generated.charactersInvolved());
        option.setConflict(generated.conflict());
        option.setHighlightMoment(generated.highlightMoment());
        option.setForeshadowActions(generated.foreshadowActions());
        option.setMemoryReferences(generated.memoryReferences());
        option.setWhyThisPlan(generated.whyThisPlan());
        option.setEndingHook(generated.endingHook());
        option.setRiskNotes(generated.riskNotes());
        option.setStatus(OutlineOptionStatus.GENERATED);
        return option;
    }

    public record GeneratedOutlineOptions(Chapter chapter, List<ChapterOutlineOption> options) {
    }
}
