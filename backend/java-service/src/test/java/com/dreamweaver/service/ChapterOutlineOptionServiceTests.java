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
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.dreamweaver.dto.AiOutlineOptionResponse;
import com.dreamweaver.dto.AiOutlineOptionsGenerateRequest;
import com.dreamweaver.dto.AiOutlineOptionsGenerateResponse;
import com.dreamweaver.dto.ChapterOutlineOptionsGenerateRequest;
import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.ChapterOutlineOption;
import com.dreamweaver.entity.ChapterWorkflowStage;
import com.dreamweaver.entity.OutlineOptionCode;
import com.dreamweaver.entity.OutlineOptionStatus;
import com.dreamweaver.entity.Story;
import com.dreamweaver.entity.StoryStatus;
import com.dreamweaver.repository.ChapterOutlineOptionRepository;
import com.dreamweaver.repository.ChapterRepository;
import com.dreamweaver.repository.StoryRepository;

@ExtendWith(MockitoExtension.class)
class ChapterOutlineOptionServiceTests {

    private static final UUID STORY_ID = UUID.fromString("10000000-0000-0000-0000-000000000070");
    private static final UUID CHAPTER_ID = UUID.fromString("20000000-0000-0000-0000-000000000070");

    @Mock
    private StoryRepository storyRepository;

    @Mock
    private ChapterRepository chapterRepository;

    @Mock
    private ChapterOutlineOptionRepository optionRepository;

    @Mock
    private AiOutlineClient aiOutlineClient;

    private ChapterOutlineOptionService service;
    private Story story;
    private Chapter chapter;

    @BeforeEach
    void setUp() {
        service = new ChapterOutlineOptionService(
            storyRepository,
            chapterRepository,
            optionRepository,
            aiOutlineClient
        );
        story = story();
        chapter = chapter();
    }

    @Test
    void generateSavesThreeOptionsAndMarksChapterOutlineOptionsGenerated() {
        arrangeStoryAndChapter();
        when(aiOutlineClient.generateOutlineOptions(any(), any(), any(AiOutlineOptionsGenerateRequest.class)))
            .thenAnswer(invocation -> {
                AiOutlineOptionsGenerateRequest request = invocation.getArgument(2);
                return generated(CHAPTER_ID.toString(), request.optionGroupId());
            });
        when(optionRepository.saveAll(any())).thenAnswer(invocation -> invocation.getArgument(0));

        ChapterOutlineOptionService.GeneratedOutlineOptions result = service.generate(
            STORY_ID,
            CHAPTER_ID,
            new ChapterOutlineOptionsGenerateRequest(Map.of("goal", "open with pressure"))
        );

        assertThat(result.chapter().getWorkflowStage()).isEqualTo(ChapterWorkflowStage.OUTLINE_OPTIONS_GENERATED);
        assertThat(result.options()).hasSize(3);
        assertThat(result.options()).extracting(ChapterOutlineOption::getOptionCode)
            .containsExactly(OutlineOptionCode.A, OutlineOptionCode.B, OutlineOptionCode.C);
        assertThat(result.options()).allSatisfy(option -> {
            assertThat(option.getStoryId()).isEqualTo(STORY_ID);
            assertThat(option.getChapterId()).isEqualTo(CHAPTER_ID);
            assertThat(option.getOptionGroupId()).isNotNull();
            assertThat(option.getStatus()).isEqualTo(OutlineOptionStatus.GENERATED);
        });
        verify(chapterRepository).save(chapter);
    }

    @Test
    void generateRejectsAiOptionsForDifferentChapter() {
        arrangeStoryAndChapter();
        when(aiOutlineClient.generateOutlineOptions(any(), any(), any(AiOutlineOptionsGenerateRequest.class)))
            .thenAnswer(invocation -> {
                AiOutlineOptionsGenerateRequest request = invocation.getArgument(2);
                return generated("different-chapter", request.optionGroupId());
            });

        assertThatThrownBy(() -> service.generate(STORY_ID, CHAPTER_ID, null))
            .isInstanceOf(AiWorkerException.class)
            .hasMessageContaining("different chapter");

        verify(optionRepository, never()).saveAll(any());
        verify(chapterRepository, never()).save(any());
    }

    private void arrangeStoryAndChapter() {
        when(storyRepository.findById(STORY_ID)).thenReturn(Optional.of(story));
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
    }

    private AiOutlineOptionsGenerateResponse generated(String chapterId, String groupId) {
        return new AiOutlineOptionsGenerateResponse(
            STORY_ID.toString(),
            chapterId,
            groupId,
            List.of(
                option("A", "steady", groupId),
                option("B", "conflict", groupId),
                option("C", "foreshadow", groupId)
            )
        );
    }

    private AiOutlineOptionResponse option(String code, String type, String groupId) {
        return new AiOutlineOptionResponse(
            STORY_ID.toString(),
            CHAPTER_ID.toString(),
            groupId,
            code,
            type,
            List.of("The Envoy Arrives"),
            "Expose the hidden envoy",
            "The protagonist spots a false envoy entering the sect.",
            scenes(),
            List.of(Map.<String, Object>of("name", "Ming", "motivation", "protect the gate")),
            Map.<String, Object>of("stakes", "The gate falls"),
            "Ming notices the forged seal.",
            code.equals("C") ? List.of(Map.<String, Object>of("action", "plant", "description", "Seal reacts")) : List.of(),
            List.of(),
            "It moves the conspiracy into the open.",
            "The seal answers to Ming's blood.",
            List.of(),
            "generated"
        );
    }

    private List<Map<String, Object>> scenes() {
        return List.of(
            Map.<String, Object>of("order", 1, "summary", "Envoy reaches the gate", "purpose", "Open", "outcome", "Ming notices a seal"),
            Map.<String, Object>of("order", 2, "summary", "Ming delays the envoy", "purpose", "Pressure", "outcome", "The seal cracks"),
            Map.<String, Object>of("order", 3, "summary", "The gate answers", "purpose", "Hook", "outcome", "Blood wakes the seal")
        );
    }

    private Story story() {
        Story story = new Story();
        story.setId(STORY_ID);
        story.setUserId(UUID.fromString("00000000-0000-0000-0000-000000000001"));
        story.setTitle("Test Story");
        story.setStatus(StoryStatus.WRITING);
        return story;
    }

    private Chapter chapter() {
        Chapter chapter = new Chapter();
        chapter.setId(CHAPTER_ID);
        chapter.setStoryId(STORY_ID);
        chapter.setChapterNumber(1);
        chapter.setWorkflowStage(ChapterWorkflowStage.OUTLINE_OPTIONS_GENERATING);
        return chapter;
    }
}
