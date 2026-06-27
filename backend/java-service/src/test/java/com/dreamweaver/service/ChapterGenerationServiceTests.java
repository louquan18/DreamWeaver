package com.dreamweaver.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

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
import com.dreamweaver.entity.StoryStatus;
import com.dreamweaver.repository.ChapterGenerationRepository;
import com.dreamweaver.repository.ChapterOutlineRepository;
import com.dreamweaver.repository.ChapterRepository;
import com.dreamweaver.repository.NovelBlueprintRepository;
import com.dreamweaver.repository.StoryRepository;

@ExtendWith(MockitoExtension.class)
class ChapterGenerationServiceTests {

    private static final UUID STORY_ID = UUID.fromString("10000000-0000-0000-0000-000000000050");
    private static final UUID CHAPTER_ID = UUID.fromString("20000000-0000-0000-0000-000000000050");
    private static final UUID GENERATION_ID = UUID.fromString("30000000-0000-0000-0000-000000000050");

    @Mock
    private ChapterGenerationRepository generationRepository;

    @Mock
    private ChapterRepository chapterRepository;

    @Mock
    private StoryRepository storyRepository;

    @Mock
    private NovelBlueprintRepository blueprintRepository;

    @Mock
    private ChapterOutlineRepository outlineRepository;

    @Mock
    private ChapterMemorySummaryService chapterMemorySummaryService;

    @Mock
    private StoryMemoryService storyMemoryService;

    @Mock
    private AdditionalMemoryRetriever additionalMemoryRetriever;

    @Test
    void createRejectsDraftGenerationBeforeOutlineConfirmed() {
        Chapter chapter = chapter(ChapterWorkflowStage.OUTLINE_OPTIONS_GENERATED);
        ChapterGenerationService service = service();
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));

        assertThatThrownBy(() -> service.create(STORY_ID, CHAPTER_ID, request()))
            .isInstanceOf(BadRequestException.class)
            .hasMessageContaining("outline must be confirmed");

        verify(generationRepository, never()).save(any(ChapterGeneration.class));
    }

    @Test
    void createQueuesDraftGenerationAfterOutlineConfirmed() {
        Chapter chapter = chapter(ChapterWorkflowStage.OUTLINE_CONFIRMED);
        ChapterGenerationService service = service();
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        arrangeConfirmedWritingContext(chapter);
        when(generationRepository.save(any(ChapterGeneration.class))).thenAnswer(invocation -> invocation.getArgument(0));

        ChapterGeneration generation = service.create(STORY_ID, CHAPTER_ID, request());

        assertThat(generation.getStatus()).isEqualTo(GenerationStatus.QUEUED);
        assertThat(generation.getStoryId()).isEqualTo(STORY_ID);
        assertThat(generation.getChapterId()).isEqualTo(CHAPTER_ID);
        assertThat(generation.getRequest()).containsKey("writing_context");
        Map<String, Object> writingContext = mapValue(generation.getRequest().get("writing_context"));
        assertThat(mapValue(writingContext.get("blueprint"))).containsEntry("premise", "A betrayed disciple uses dream visions.");
        assertThat(mapValue(writingContext.get("confirmedOutline"))).containsKey("finalOutline");
        assertThat(writingContext.get("recentChapters")).asList().hasSize(1);
        assertThat(writingContext.get("timeline")).isEqualTo(java.util.List.of(Map.of("id", "tl-1", "event", "Ming sealed the gate")));
        assertThat(writingContext.get("characters")).isEqualTo(java.util.List.of(Map.of("name", "Ming")));
        assertThat(writingContext.get("world")).isEqualTo(java.util.List.of(Map.of("subject", "Mirror fire", "locked", true)));
        assertThat(writingContext.get("foreshadows")).isEqualTo(java.util.List.of(Map.of("id", "fs-1", "status", "triggered")));
        assertThat(writingContext.get("additionalMemory")).isEqualTo(java.util.List.of(Map.of(
            "type",
            "foreshadow",
            "content",
            "The mirror token is burning."
        )));
        assertThat(mapValue(writingContext.get("contextMetadata")))
            .containsEntry("policy", "structured-memory-v1")
            .containsKey("limits");
    }

    @Test
    void createRejectsDraftGenerationWithoutConfirmedBlueprint() {
        Chapter chapter = chapter(ChapterWorkflowStage.OUTLINE_CONFIRMED);
        ChapterGenerationService service = service();
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        when(storyRepository.findById(STORY_ID)).thenReturn(Optional.of(story()));
        when(blueprintRepository.findFirstByStoryIdAndStatusOrderByCreatedAtDesc(
            STORY_ID,
            NovelBlueprintStatus.CONFIRMED
        )).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.create(STORY_ID, CHAPTER_ID, request()))
            .isInstanceOf(BadRequestException.class)
            .hasMessageContaining("blueprint must be confirmed");

        verify(generationRepository, never()).save(any(ChapterGeneration.class));
    }

    @Test
    void createRejectsDraftGenerationAfterChapterConfirmed() {
        Chapter chapter = chapter(ChapterWorkflowStage.CHAPTER_CONFIRMED);
        ChapterGenerationService service = service();
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));

        assertThatThrownBy(() -> service.create(STORY_ID, CHAPTER_ID, request()))
            .isInstanceOf(ConflictException.class)
            .hasMessageContaining("already been confirmed and frozen");

        verify(generationRepository, never()).save(any(ChapterGeneration.class));
    }

    @Test
    void confirmDraftStoresSucceededGenerationAndMarksDraftConfirmed() {
        Chapter chapter = chapter(ChapterWorkflowStage.DRAFT_READY_FOR_CONFIRMATION);
        ChapterGeneration generation = succeededGeneration(GENERATION_ID, "The dream fire answered.");
        ChapterGenerationService service = service();
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        when(generationRepository.findByIdAndStoryIdAndChapterId(
            GENERATION_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(generation));
        when(chapterRepository.save(any(Chapter.class))).thenAnswer(invocation -> invocation.getArgument(0));

        Chapter confirmed = service.confirmDraft(STORY_ID, CHAPTER_ID, GENERATION_ID);

        assertThat(confirmed.getContent()).isEqualTo("The dream fire answered.");
        assertThat(confirmed.getWordCount()).isEqualTo(2400);
        assertThat(confirmed.getLastGenerationId()).isEqualTo(GENERATION_ID);
        assertThat(confirmed.getStatus()).isEqualTo(ChapterStatus.APPROVED);
        assertThat(confirmed.getWorkflowStage()).isEqualTo(ChapterWorkflowStage.DRAFT_CONFIRMED);
    }

    @Test
    void confirmDraftRejectsNonSucceededGeneration() {
        Chapter chapter = chapter(ChapterWorkflowStage.DRAFT_READY_FOR_CONFIRMATION);
        ChapterGeneration generation = generation(GENERATION_ID, GenerationStatus.RUNNING, "still streaming");
        ChapterGenerationService service = service();
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        when(generationRepository.findByIdAndStoryIdAndChapterId(
            GENERATION_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(generation));

        assertThatThrownBy(() -> service.confirmDraft(STORY_ID, CHAPTER_ID, GENERATION_ID))
            .isInstanceOf(BadRequestException.class)
            .hasMessageContaining("succeeded generation");

        verify(chapterRepository, never()).save(any(Chapter.class));
    }

    @Test
    void confirmDraftRejectsEmptyDraft() {
        Chapter chapter = chapter(ChapterWorkflowStage.DRAFT_READY_FOR_CONFIRMATION);
        ChapterGeneration generation = succeededGeneration(GENERATION_ID, " ");
        ChapterGenerationService service = service();
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        when(generationRepository.findByIdAndStoryIdAndChapterId(
            GENERATION_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(generation));

        assertThatThrownBy(() -> service.confirmDraft(STORY_ID, CHAPTER_ID, GENERATION_ID))
            .isInstanceOf(BadRequestException.class)
            .hasMessageContaining("no draft content");

        verify(chapterRepository, never()).save(any(Chapter.class));
    }

    @Test
    void confirmDraftIsIdempotentForSameConfirmedGeneration() {
        Chapter chapter = chapter(ChapterWorkflowStage.DRAFT_CONFIRMED);
        chapter.setLastGenerationId(GENERATION_ID);
        chapter.setContent("Already confirmed.");
        chapter.setStatus(ChapterStatus.APPROVED);
        ChapterGeneration generation = succeededGeneration(GENERATION_ID, "Already confirmed.");
        ChapterGenerationService service = service();
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        when(generationRepository.findByIdAndStoryIdAndChapterId(
            GENERATION_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(generation));

        Chapter confirmed = service.confirmDraft(STORY_ID, CHAPTER_ID, GENERATION_ID);

        assertThat(confirmed).isSameAs(chapter);
        verify(chapterRepository, never()).save(any(Chapter.class));
    }

    @Test
    void confirmDraftRejectsDifferentGenerationAfterDraftConfirmed() {
        UUID otherGenerationId = UUID.fromString("30000000-0000-0000-0000-000000000051");
        Chapter chapter = chapter(ChapterWorkflowStage.DRAFT_CONFIRMED);
        chapter.setLastGenerationId(GENERATION_ID);
        ChapterGeneration generation = succeededGeneration(otherGenerationId, "A different draft.");
        ChapterGenerationService service = service();
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        when(generationRepository.findByIdAndStoryIdAndChapterId(
            otherGenerationId,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(generation));

        assertThatThrownBy(() -> service.confirmDraft(STORY_ID, CHAPTER_ID, otherGenerationId))
            .isInstanceOf(ConflictException.class)
            .hasMessageContaining("already been confirmed");

        verify(chapterRepository, never()).save(any(Chapter.class));
    }

    @Test
    void confirmDraftRejectsDifferentGenerationAfterMemoryStarted() {
        UUID otherGenerationId = UUID.fromString("30000000-0000-0000-0000-000000000051");
        Chapter chapter = chapter(ChapterWorkflowStage.MEMORY_PENDING_CONFIRMATION);
        chapter.setLastGenerationId(GENERATION_ID);
        ChapterGeneration generation = succeededGeneration(otherGenerationId, "A different draft.");
        ChapterGenerationService service = service();
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        when(generationRepository.findByIdAndStoryIdAndChapterId(
            otherGenerationId,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(generation));

        assertThatThrownBy(() -> service.confirmDraft(STORY_ID, CHAPTER_ID, otherGenerationId))
            .isInstanceOf(ConflictException.class)
            .hasMessageContaining("already been confirmed");

        verify(chapterRepository, never()).save(any(Chapter.class));
    }

    @Test
    void markRunningMovesChapterToDraftGenerating() {
        Chapter chapter = chapter(ChapterWorkflowStage.OUTLINE_CONFIRMED);
        ChapterGeneration generation = generation(GENERATION_ID, GenerationStatus.QUEUED, null);
        ChapterGenerationService service = service();
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        when(generationRepository.findByIdAndStoryIdAndChapterId(
            GENERATION_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(generation));
        when(generationRepository.save(any(ChapterGeneration.class))).thenAnswer(invocation -> invocation.getArgument(0));

        service.markRunning(STORY_ID, CHAPTER_ID, GENERATION_ID);

        assertThat(chapter.getStatus()).isEqualTo(ChapterStatus.GENERATING);
        assertThat(chapter.getWorkflowStage()).isEqualTo(ChapterWorkflowStage.DRAFT_GENERATING);
    }

    @Test
    void markRunningDoesNotRegressConfirmedDraftWorkflowStage() {
        Chapter chapter = chapter(ChapterWorkflowStage.DRAFT_CONFIRMED);
        chapter.setLastGenerationId(GENERATION_ID);
        chapter.setStatus(ChapterStatus.APPROVED);
        ChapterGeneration generation = generation(GENERATION_ID, GenerationStatus.QUEUED, null);
        ChapterGenerationService service = service();
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        when(generationRepository.findByIdAndStoryIdAndChapterId(
            GENERATION_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(generation));
        when(generationRepository.save(any(ChapterGeneration.class))).thenAnswer(invocation -> invocation.getArgument(0));

        service.markRunning(STORY_ID, CHAPTER_ID, GENERATION_ID);

        assertThat(chapter.getStatus()).isEqualTo(ChapterStatus.APPROVED);
        assertThat(chapter.getWorkflowStage()).isEqualTo(ChapterWorkflowStage.DRAFT_CONFIRMED);
    }

    @ParameterizedTest
    @EnumSource(
        value = ChapterWorkflowStage.class,
        names = {
            "MEMORY_EXTRACTING",
            "MEMORY_PENDING_CONFIRMATION",
            "MEMORY_CONFIRMED",
            "CHAPTER_CONFIRMED"
        }
    )
    void markRunningDoesNotRegressMemoryOrFrozenWorkflowStages(ChapterWorkflowStage lockedStage) {
        Chapter chapter = chapter(lockedStage);
        chapter.setLastGenerationId(GENERATION_ID);
        chapter.setStatus(ChapterStatus.APPROVED);
        ChapterGeneration generation = generation(GENERATION_ID, GenerationStatus.QUEUED, null);
        ChapterGenerationService service = service();
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        when(generationRepository.findByIdAndStoryIdAndChapterId(
            GENERATION_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(generation));
        when(generationRepository.save(any(ChapterGeneration.class))).thenAnswer(invocation -> invocation.getArgument(0));

        service.markRunning(STORY_ID, CHAPTER_ID, GENERATION_ID);

        assertThat(chapter.getStatus()).isEqualTo(ChapterStatus.APPROVED);
        assertThat(chapter.getWorkflowStage()).isEqualTo(lockedStage);
        verify(chapterRepository, never()).save(any(Chapter.class));
    }

    @Test
    void completeFromStreamMovesChapterToDraftReadyForConfirmation() {
        Chapter chapter = chapter(ChapterWorkflowStage.DRAFT_GENERATING);
        ChapterGeneration generation = generation(GENERATION_ID, GenerationStatus.RUNNING, null);
        generation.setRequest(Map.of("auto_adopt", true));
        ChapterGenerationService service = service();
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        when(generationRepository.findByIdAndStoryIdAndChapterId(
            GENERATION_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(generation));
        when(generationRepository.save(any(ChapterGeneration.class))).thenAnswer(invocation -> invocation.getArgument(0));

        service.completeFromStream(
            STORY_ID,
            CHAPTER_ID,
            GENERATION_ID,
            "The completed draft.",
            1800,
            java.util.List.of()
        );

        assertThat(chapter.getStatus()).isEqualTo(ChapterStatus.GENERATED);
        assertThat(chapter.getWorkflowStage()).isEqualTo(ChapterWorkflowStage.DRAFT_READY_FOR_CONFIRMATION);
    }

    @Test
    void completeFromStreamDoesNotRegressConfirmedDraftWorkflowStage() {
        Chapter chapter = chapter(ChapterWorkflowStage.DRAFT_CONFIRMED);
        chapter.setLastGenerationId(GENERATION_ID);
        chapter.setStatus(ChapterStatus.APPROVED);
        chapter.setContent("Confirmed draft.");
        ChapterGeneration generation = generation(GENERATION_ID, GenerationStatus.RUNNING, null);
        generation.setRequest(Map.of("auto_adopt", true));
        ChapterGenerationService service = service();
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        when(generationRepository.findByIdAndStoryIdAndChapterId(
            GENERATION_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(generation));
        when(generationRepository.save(any(ChapterGeneration.class))).thenAnswer(invocation -> invocation.getArgument(0));

        service.completeFromStream(
            STORY_ID,
            CHAPTER_ID,
            GENERATION_ID,
            "Late stream result.",
            1800,
            java.util.List.of()
        );

        assertThat(chapter.getContent()).isEqualTo("Confirmed draft.");
        assertThat(chapter.getStatus()).isEqualTo(ChapterStatus.APPROVED);
        assertThat(chapter.getWorkflowStage()).isEqualTo(ChapterWorkflowStage.DRAFT_CONFIRMED);
    }

    @ParameterizedTest
    @EnumSource(
        value = ChapterWorkflowStage.class,
        names = {
            "MEMORY_EXTRACTING",
            "MEMORY_PENDING_CONFIRMATION",
            "MEMORY_CONFIRMED",
            "CHAPTER_CONFIRMED"
        }
    )
    void completeFromStreamDoesNotRegressMemoryOrFrozenWorkflowStages(ChapterWorkflowStage lockedStage) {
        Chapter chapter = chapter(lockedStage);
        chapter.setLastGenerationId(GENERATION_ID);
        chapter.setStatus(ChapterStatus.APPROVED);
        chapter.setContent("Confirmed draft.");
        ChapterGeneration generation = generation(GENERATION_ID, GenerationStatus.RUNNING, null);
        generation.setRequest(Map.of("auto_adopt", true));
        ChapterGenerationService service = service();
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        when(generationRepository.findByIdAndStoryIdAndChapterId(
            GENERATION_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(generation));
        when(generationRepository.save(any(ChapterGeneration.class))).thenAnswer(invocation -> invocation.getArgument(0));

        service.completeFromStream(
            STORY_ID,
            CHAPTER_ID,
            GENERATION_ID,
            "Late stream result.",
            1800,
            java.util.List.of()
        );

        assertThat(chapter.getContent()).isEqualTo("Confirmed draft.");
        assertThat(chapter.getStatus()).isEqualTo(ChapterStatus.APPROVED);
        assertThat(chapter.getWorkflowStage()).isEqualTo(lockedStage);
        verify(chapterRepository, never()).save(any(Chapter.class));
    }

    private ChapterGenerationService service() {
        return new ChapterGenerationService(
            generationRepository,
            new ChapterService(chapterRepository, null),
            storyRepository,
            blueprintRepository,
            outlineRepository,
            chapterRepository,
            chapterMemorySummaryService,
            storyMemoryService,
            additionalMemoryRetriever
        );
    }

    private void arrangeConfirmedWritingContext(Chapter chapter) {
        when(storyRepository.findById(STORY_ID)).thenReturn(Optional.of(story()));
        when(blueprintRepository.findFirstByStoryIdAndStatusOrderByCreatedAtDesc(
            STORY_ID,
            NovelBlueprintStatus.CONFIRMED
        )).thenReturn(Optional.of(blueprint()));
        when(outlineRepository.findFirstByStoryIdAndChapterIdAndStatusOrderByCreatedAtDesc(
            STORY_ID,
            CHAPTER_ID,
            ChapterOutlineStatus.CONFIRMED
        )).thenReturn(Optional.of(outline()));
        when(chapterRepository.findByStoryIdOrderByChapterNumberAsc(STORY_ID))
            .thenReturn(java.util.List.of(previousChapter(), chapter));
        when(chapterMemorySummaryService.recentChapterContexts(any(), any(), any())).thenReturn(java.util.List.of(Map.of(
            "title",
            "Previous",
            "content",
            "Lin Jin escaped the outer sect with the dream token.",
            "contextRole",
            "recent_full_text"
        )));
        when(storyMemoryService.buildOutlineMemoryContext(STORY_ID)).thenReturn(new StoryMemoryService.MemoryContext(
            java.util.List.of(Map.of("id", "tl-1", "event", "Ming sealed the gate")),
            java.util.List.of(Map.of("name", "Ming")),
            java.util.List.of(Map.of("subject", "Mirror fire", "locked", true)),
            java.util.List.of(Map.of("id", "fs-1", "status", "triggered")),
            java.util.List.of()
        ));
        when(additionalMemoryRetriever.retrieve(any(), any(), any(), any(), any(), any())).thenReturn(java.util.List.of(Map.of(
            "type",
            "foreshadow",
            "content",
            "The mirror token is burning."
        )));
    }

    private Chapter chapter(ChapterWorkflowStage stage) {
        Chapter chapter = new Chapter();
        chapter.setId(CHAPTER_ID);
        chapter.setStoryId(STORY_ID);
        chapter.setChapterNumber(1);
        chapter.setWorkflowStage(stage);
        return chapter;
    }

    private Chapter previousChapter() {
        Chapter chapter = new Chapter();
        chapter.setId(UUID.fromString("20000000-0000-0000-0000-000000000049"));
        chapter.setStoryId(STORY_ID);
        chapter.setChapterNumber(0);
        chapter.setTitle("Previous");
        chapter.setContent("Lin Jin escaped the outer sect with the dream token.");
        chapter.setWordCount(42);
        return chapter;
    }

    private Story story() {
        Story story = new Story();
        story.setId(STORY_ID);
        story.setUserId(UUID.fromString("00000000-0000-0000-0000-000000000001"));
        story.setTitle("Dream Fire");
        story.setStatus(StoryStatus.WRITING);
        return story;
    }

    private NovelBlueprint blueprint() {
        NovelBlueprint blueprint = new NovelBlueprint();
        blueprint.setId(UUID.fromString("30000000-0000-0000-0000-000000000050"));
        blueprint.setStoryId(STORY_ID);
        blueprint.setPremise("A betrayed disciple uses dream visions.");
        blueprint.setProtagonist(Map.of("name", "Lin Jin"));
        blueprint.setMainThread(Map.of("goal", "Reveal the dream mirror source"));
        blueprint.setCoreConflict(Map.of("external", "Sect pursuit"));
        blueprint.setWorldSeed(Map.of("rules", java.util.List.of("Dream visions are fragmented")));
        blueprint.setWritingPreferences(Map.of("style", "tense"));
        blueprint.setLockedFacts(java.util.List.of(Map.of("text", "Dream fire cannot show complete futures")));
        blueprint.setStatus(NovelBlueprintStatus.CONFIRMED);
        return blueprint;
    }

    private ChapterOutline outline() {
        ChapterOutline outline = new ChapterOutline();
        outline.setId(UUID.fromString("40000000-0000-0000-0000-000000000050"));
        outline.setStoryId(STORY_ID);
        outline.setChapterId(CHAPTER_ID);
        outline.setFinalOutline(Map.of(
            "chapterGoal", "Trace the token",
            "sceneOutline", java.util.List.of(Map.of("summary", "The token burns"))
        ));
        outline.setStatus(ChapterOutlineStatus.CONFIRMED);
        return outline;
    }

    private ChapterGeneration succeededGeneration(UUID generationId, String draft) {
        ChapterGeneration generation = generation(generationId, GenerationStatus.SUCCEEDED, draft);
        generation.setWordCount(2400);
        return generation;
    }

    private ChapterGeneration generation(UUID generationId, GenerationStatus status, String draft) {
        ChapterGeneration generation = new ChapterGeneration();
        generation.setId(generationId);
        generation.setStoryId(STORY_ID);
        generation.setChapterId(CHAPTER_ID);
        generation.setUserId(UUID.fromString("00000000-0000-0000-0000-000000000001"));
        generation.setStatus(status);
        generation.setDraft(draft);
        generation.setRequest(Map.of());
        return generation;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        return (Map<String, Object>) value;
    }

    private ChapterGenerationCreateRequest request() {
        return new ChapterGenerationCreateRequest(
            null,
            2000,
            "keep the confirmed outline",
            "writing",
            true,
            Map.of()
        );
    }
}
