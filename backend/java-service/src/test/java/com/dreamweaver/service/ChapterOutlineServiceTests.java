package com.dreamweaver.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.dreamweaver.dto.ChapterOutlineConfirmRequest;
import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.ChapterOutline;
import com.dreamweaver.entity.ChapterOutlineStatus;
import com.dreamweaver.entity.ChapterWorkflowStage;
import com.dreamweaver.entity.OutlineOptionCode;
import com.dreamweaver.entity.ChapterOutlineOption;
import com.dreamweaver.entity.OutlineOptionStatus;
import com.dreamweaver.entity.OutlineOptionType;
import com.dreamweaver.entity.Story;
import com.dreamweaver.entity.StoryStatus;
import com.dreamweaver.repository.ChapterOutlineOptionRepository;
import com.dreamweaver.repository.ChapterOutlineRepository;
import com.dreamweaver.repository.ChapterRepository;
import com.dreamweaver.repository.StoryRepository;

@ExtendWith(MockitoExtension.class)
class ChapterOutlineServiceTests {

    private static final UUID STORY_ID = UUID.fromString("10000000-0000-0000-0000-000000000001");
    private static final UUID CHAPTER_ID = UUID.fromString("20000000-0000-0000-0000-000000000001");
    private static final UUID OPTION_A_ID = UUID.fromString("30000000-0000-0000-0000-000000000001");
    private static final UUID OPTION_B_ID = UUID.fromString("30000000-0000-0000-0000-000000000002");

    @Mock
    private StoryRepository storyRepository;

    @Mock
    private ChapterRepository chapterRepository;

    @Mock
    private ChapterOutlineRepository outlineRepository;

    @Mock
    private ChapterOutlineOptionRepository optionRepository;

    private ChapterOutlineService service;
    private Story story;
    private Chapter chapter;
    private ChapterOutlineOption optionA;
    private ChapterOutlineOption optionB;

    @BeforeEach
    void setUp() {
        service = new ChapterOutlineService(
            storyRepository,
            chapterRepository,
            outlineRepository,
            optionRepository
        );
        story = validStory();
        chapter = validChapter();
        optionA = validOption(OPTION_A_ID, OutlineOptionCode.A, OutlineOptionType.STEADY);
        optionB = validOption(OPTION_B_ID, OutlineOptionCode.B, OutlineOptionType.CONFLICT);
    }

    @Test
    void confirmDerivesFinalOutlineFromSingleSourceOption() {
        arrangeStoryAndChapter();
        when(outlineRepository.existsByStoryIdAndChapterIdAndStatus(
            STORY_ID,
            CHAPTER_ID,
            ChapterOutlineStatus.CONFIRMED
        )).thenReturn(false);
        when(optionRepository.findByIdAndStoryIdAndChapterId(OPTION_A_ID, STORY_ID, CHAPTER_ID))
            .thenReturn(Optional.of(optionA));
        when(outlineRepository.saveAndFlush(any(ChapterOutline.class)))
            .thenAnswer(invocation -> invocation.getArgument(0));

        ChapterOutlineService.ConfirmedOutline result = service.confirm(
            STORY_ID,
            CHAPTER_ID,
            new ChapterOutlineConfirmRequest(List.of(OPTION_A_ID), null, null)
        );

        assertThat(result.chapter().getWorkflowStage()).isEqualTo(ChapterWorkflowStage.OUTLINE_CONFIRMED);
        assertThat(result.outline().getStatus()).isEqualTo(ChapterOutlineStatus.CONFIRMED);
        assertThat(result.outline().getConfirmedAt()).isNotNull();
        assertThat(result.outline().getSourceOptionIds()).containsExactly(OPTION_A_ID);
        assertThat(result.outline().getFinalOutline())
            .containsEntry("chapterGoal", "Expose the hidden envoy");
        assertThat(optionA.getStatus()).isEqualTo(OutlineOptionStatus.SELECTED);
        verify(optionRepository).saveAll(List.of(optionA));
        verify(chapterRepository).save(chapter);
        verify(outlineRepository).saveAndFlush(any(ChapterOutline.class));
    }

    @Test
    void confirmAcceptsMixedSourcesWhenFinalOutlineProvided() {
        arrangeStoryAndChapter();
        when(outlineRepository.existsByStoryIdAndChapterIdAndStatus(
            STORY_ID,
            CHAPTER_ID,
            ChapterOutlineStatus.CONFIRMED
        )).thenReturn(false);
        when(optionRepository.findByIdAndStoryIdAndChapterId(OPTION_A_ID, STORY_ID, CHAPTER_ID))
            .thenReturn(Optional.of(optionA));
        when(optionRepository.findByIdAndStoryIdAndChapterId(OPTION_B_ID, STORY_ID, CHAPTER_ID))
            .thenReturn(Optional.of(optionB));
        when(outlineRepository.saveAndFlush(any(ChapterOutline.class)))
            .thenAnswer(invocation -> invocation.getArgument(0));

        Map<String, Object> finalOutline = validFinalOutline("Keep B conflict and C-style ending hook");

        ChapterOutlineService.ConfirmedOutline result = service.confirm(
            STORY_ID,
            CHAPTER_ID,
            new ChapterOutlineConfirmRequest(
                List.of(OPTION_A_ID, OPTION_B_ID),
                "Use A pacing with B conflict.",
                finalOutline
            )
        );

        assertThat(result.outline().getFinalOutline()).containsEntry(
            "chapterGoal",
            "Keep B conflict and C-style ending hook"
        );
        assertThat(result.outline().getUserFeedback()).isEqualTo("Use A pacing with B conflict.");
        assertThat(optionA.getStatus()).isEqualTo(OutlineOptionStatus.SELECTED);
        assertThat(optionB.getStatus()).isEqualTo(OutlineOptionStatus.SELECTED);
        verify(optionRepository).saveAll(List.of(optionA, optionB));
    }

    @Test
    void confirmRejectsMultipleSourcesWithoutFinalOutline() {
        arrangeStoryAndChapter();
        when(outlineRepository.existsByStoryIdAndChapterIdAndStatus(
            STORY_ID,
            CHAPTER_ID,
            ChapterOutlineStatus.CONFIRMED
        )).thenReturn(false);
        when(optionRepository.findByIdAndStoryIdAndChapterId(OPTION_A_ID, STORY_ID, CHAPTER_ID))
            .thenReturn(Optional.of(optionA));
        when(optionRepository.findByIdAndStoryIdAndChapterId(OPTION_B_ID, STORY_ID, CHAPTER_ID))
            .thenReturn(Optional.of(optionB));

        assertThatThrownBy(() -> service.confirm(
            STORY_ID,
            CHAPTER_ID,
            new ChapterOutlineConfirmRequest(List.of(OPTION_A_ID, OPTION_B_ID), null, null)
        ))
            .isInstanceOf(BadRequestException.class)
            .hasMessageContaining("finalOutline is required");

        verify(outlineRepository, never()).saveAndFlush(any(ChapterOutline.class));
    }

    @Test
    void confirmRejectsAlreadyConfirmedChapterOutline() {
        arrangeStoryAndChapter();
        when(outlineRepository.existsByStoryIdAndChapterIdAndStatus(
            STORY_ID,
            CHAPTER_ID,
            ChapterOutlineStatus.CONFIRMED
        )).thenReturn(true);

        assertThatThrownBy(() -> service.confirm(
            STORY_ID,
            CHAPTER_ID,
            new ChapterOutlineConfirmRequest(List.of(OPTION_A_ID), null, null)
        ))
            .isInstanceOf(ConflictException.class)
            .hasMessageContaining("Chapter already has a confirmed outline");

        verify(optionRepository, never()).findByIdAndStoryIdAndChapterId(any(), any(), any());
        verify(outlineRepository, never()).saveAndFlush(any(ChapterOutline.class));
    }

    @Test
    void confirmRejectsIncompleteFinalOutline() {
        arrangeStoryAndChapter();
        when(outlineRepository.existsByStoryIdAndChapterIdAndStatus(
            STORY_ID,
            CHAPTER_ID,
            ChapterOutlineStatus.CONFIRMED
        )).thenReturn(false);
        when(optionRepository.findByIdAndStoryIdAndChapterId(OPTION_A_ID, STORY_ID, CHAPTER_ID))
            .thenReturn(Optional.of(optionA));

        Map<String, Object> incomplete = validFinalOutline("Goal");
        incomplete.remove("endingHook");

        assertThatThrownBy(() -> service.confirm(
            STORY_ID,
            CHAPTER_ID,
            new ChapterOutlineConfirmRequest(List.of(OPTION_A_ID), null, incomplete)
        ))
            .isInstanceOf(BadRequestException.class)
            .hasMessageContaining("finalOutline.endingHook is required");

        verify(outlineRepository, never()).saveAndFlush(any(ChapterOutline.class));
    }

    @ParameterizedTest
    @EnumSource(
        value = ChapterWorkflowStage.class,
        names = {
            "DRAFT_GENERATING",
            "DRAFT_READY_FOR_CONFIRMATION",
            "DRAFT_CONFIRMED",
            "MEMORY_PENDING_CONFIRMATION",
            "MEMORY_CONFIRMED",
            "CHAPTER_CONFIRMED"
        }
    )
    void confirmRejectsLaterWorkflowStagesWithoutRegressingChapter(ChapterWorkflowStage laterStage) {
        chapter.setWorkflowStage(laterStage);
        arrangeStoryAndChapter();

        assertThatThrownBy(() -> service.confirm(
            STORY_ID,
            CHAPTER_ID,
            new ChapterOutlineConfirmRequest(List.of(OPTION_A_ID), null, null)
        ))
            .isInstanceOf(ConflictException.class)
            .hasMessageContaining("outline");

        assertThat(chapter.getWorkflowStage()).isEqualTo(laterStage);
        verify(optionRepository, never()).findByIdAndStoryIdAndChapterId(any(), any(), any());
        verify(outlineRepository, never()).saveAndFlush(any(ChapterOutline.class));
        verify(chapterRepository, never()).save(any(Chapter.class));
    }

    private void arrangeStoryAndChapter() {
        when(storyRepository.findById(STORY_ID)).thenReturn(Optional.of(story));
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
    }

    private Story validStory() {
        Story validStory = new Story();
        validStory.setId(STORY_ID);
        validStory.setUserId(UUID.fromString("00000000-0000-0000-0000-000000000001"));
        validStory.setTitle("Test Story");
        validStory.setStatus(StoryStatus.WRITING);
        return validStory;
    }

    private Chapter validChapter() {
        Chapter validChapter = new Chapter();
        validChapter.setId(CHAPTER_ID);
        validChapter.setStoryId(STORY_ID);
        validChapter.setChapterNumber(1);
        validChapter.setTitle("The Envoy");
        validChapter.setWorkflowStage(ChapterWorkflowStage.OUTLINE_OPTIONS_GENERATED);
        return validChapter;
    }

    private ChapterOutlineOption validOption(
        UUID id,
        OutlineOptionCode code,
        OutlineOptionType type
    ) {
        ChapterOutlineOption option = new ChapterOutlineOption();
        option.setId(id);
        option.setStoryId(STORY_ID);
        option.setChapterId(CHAPTER_ID);
        option.setOptionGroupId(UUID.fromString("40000000-0000-0000-0000-000000000001"));
        option.setOptionCode(code);
        option.setOptionType(type);
        option.setTitleCandidates(List.of("The Envoy Arrives"));
        option.setChapterGoal("Expose the hidden envoy");
        option.setStorySummary("The protagonist spots a false envoy entering the sect.");
        option.setSceneOutline(scenes());
        option.setCharactersInvolved(List.of(Map.<String, Object>of("name", "Ming")));
        option.setConflict(Map.<String, Object>of("external", "A disguised envoy tests the gate"));
        option.setHighlightMoment("Ming notices the forged seal.");
        option.setForeshadowActions(List.of());
        option.setMemoryReferences(List.of());
        option.setWhyThisPlan("It moves the conspiracy into the open.");
        option.setEndingHook("The seal answers to Ming's blood.");
        option.setRiskNotes(List.of());
        option.setStatus(OutlineOptionStatus.GENERATED);
        return option;
    }

    private Map<String, Object> validFinalOutline(String chapterGoal) {
        return new java.util.LinkedHashMap<>(Map.<String, Object>ofEntries(
            Map.entry("titleCandidates", List.of("The Envoy Arrives")),
            Map.entry("chapterGoal", chapterGoal),
            Map.entry("storySummary", "The protagonist catches a false envoy before the gate closes."),
            Map.entry("sceneOutline", scenes()),
            Map.entry("charactersInvolved", List.of(Map.<String, Object>of("name", "Ming"))),
            Map.entry("conflict", Map.<String, Object>of("external", "A disguised envoy tests the gate")),
            Map.entry("highlightMoment", "Ming notices the forged seal."),
            Map.entry("whyThisPlan", "It moves the conspiracy into the open."),
            Map.entry("endingHook", "The seal answers to Ming's blood."),
            Map.entry("foreshadowActions", List.of()),
            Map.entry("memoryReferences", List.of()),
            Map.entry("riskNotes", List.of())
        ));
    }

    private List<Map<String, Object>> scenes() {
        return List.of(
            Map.<String, Object>of("order", 1, "summary", "Envoy reaches the gate", "purpose", "Open", "outcome", "Ming notices a seal"),
            Map.<String, Object>of("order", 2, "summary", "Ming delays the envoy", "purpose", "Pressure", "outcome", "The seal cracks"),
            Map.<String, Object>of("order", 3, "summary", "The gate answers", "purpose", "Hook", "outcome", "Blood wakes the seal")
        );
    }
}
