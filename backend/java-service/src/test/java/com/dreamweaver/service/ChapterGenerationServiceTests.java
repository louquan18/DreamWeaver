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
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.dreamweaver.dto.ChapterGenerationCreateRequest;
import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.ChapterGeneration;
import com.dreamweaver.entity.ChapterOutline;
import com.dreamweaver.entity.ChapterOutlineStatus;
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

    private ChapterGenerationService service() {
        return new ChapterGenerationService(
            generationRepository,
            new ChapterService(chapterRepository, null),
            storyRepository,
            blueprintRepository,
            outlineRepository,
            chapterRepository
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
