package com.dreamweaver.controller;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

import com.dreamweaver.entity.ChapterOutlineOption;
import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.ChapterWorkflowStage;
import com.dreamweaver.entity.OutlineOptionCode;
import com.dreamweaver.entity.OutlineOptionStatus;
import com.dreamweaver.entity.OutlineOptionType;
import com.dreamweaver.repository.ChapterOutlineOptionRepository;
import com.dreamweaver.service.ChapterOutlineOptionService;

@WebMvcTest(ChapterOutlineOptionController.class)
class ChapterOutlineOptionControllerTests {

    private static final UUID STORY_ID = UUID.fromString("10000000-0000-0000-0000-000000000060");
    private static final UUID CHAPTER_ID = UUID.fromString("20000000-0000-0000-0000-000000000060");
    private static final UUID GROUP_ID = UUID.fromString("30000000-0000-0000-0000-000000000060");
    private static final UUID OPTION_A_ID = UUID.fromString("40000000-0000-0000-0000-000000000061");
    private static final UUID OPTION_B_ID = UUID.fromString("40000000-0000-0000-0000-000000000062");

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ChapterOutlineOptionRepository optionRepository;

    @MockBean
    private ChapterOutlineOptionService optionService;

    @Test
    void listReturnsOutlineOptionsForChapter() throws Exception {
        when(optionRepository.findByStoryIdAndChapterIdOrderByCreatedAtDesc(STORY_ID, CHAPTER_ID))
            .thenReturn(List.of(
                option(OPTION_A_ID, OutlineOptionCode.A, OutlineOptionType.STEADY),
                option(OPTION_B_ID, OutlineOptionCode.B, OutlineOptionType.CONFLICT)
            ));

        mockMvc.perform(get(
                    "/api/stories/{storyId}/chapters/{chapterId}/outline-options",
                    STORY_ID,
                    CHAPTER_ID
                ))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$[0].id").value(OPTION_A_ID.toString()))
            .andExpect(jsonPath("$[0].optionCode").value("A"))
            .andExpect(jsonPath("$[0].optionType").value("steady"))
            .andExpect(jsonPath("$[0].sceneOutline[0].summary").value("Envoy reaches the gate"))
            .andExpect(jsonPath("$[1].id").value(OPTION_B_ID.toString()));
    }

    @Test
    void listCanFilterByOptionGroup() throws Exception {
        when(optionRepository.findByStoryIdAndChapterIdAndOptionGroupIdOrderByOptionCodeAsc(
            STORY_ID,
            CHAPTER_ID,
            GROUP_ID
        )).thenReturn(List.of(option(OPTION_A_ID, OutlineOptionCode.A, OutlineOptionType.STEADY)));

        mockMvc.perform(get(
                    "/api/stories/{storyId}/chapters/{chapterId}/outline-options?groupId={groupId}",
                    STORY_ID,
                    CHAPTER_ID,
                    GROUP_ID
                ))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$[0].optionGroupId").value(GROUP_ID.toString()))
            .andExpect(jsonPath("$[0].optionCode").value("A"));
    }

    @Test
    void generateReturnsSavedOutlineOptionsAndUpdatedChapter() throws Exception {
        Chapter chapter = chapter();
        ChapterOutlineOption optionA = option(OPTION_A_ID, OutlineOptionCode.A, OutlineOptionType.STEADY);
        when(optionService.generate(STORY_ID, CHAPTER_ID, null))
            .thenReturn(new ChapterOutlineOptionService.GeneratedOutlineOptions(chapter, List.of(optionA)));

        mockMvc.perform(post(
                    "/api/stories/{storyId}/chapters/{chapterId}/outline-options/generate",
                    STORY_ID,
                    CHAPTER_ID
                ))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.chapter.workflowStage").value("outline_options_generated"))
            .andExpect(jsonPath("$.options[0].id").value(OPTION_A_ID.toString()))
            .andExpect(jsonPath("$.options[0].optionCode").value("A"));
    }

    private ChapterOutlineOption option(UUID id, OutlineOptionCode code, OutlineOptionType type) {
        ChapterOutlineOption option = new ChapterOutlineOption();
        option.setId(id);
        option.setStoryId(STORY_ID);
        option.setChapterId(CHAPTER_ID);
        option.setOptionGroupId(GROUP_ID);
        option.setOptionCode(code);
        option.setOptionType(type);
        option.setTitleCandidates(List.of("The Envoy Arrives"));
        option.setChapterGoal("Expose the hidden envoy");
        option.setStorySummary("The protagonist spots a false envoy entering the sect.");
        option.setSceneOutline(List.of(
            Map.<String, Object>of("order", 1, "summary", "Envoy reaches the gate"),
            Map.<String, Object>of("order", 2, "summary", "Ming delays the envoy"),
            Map.<String, Object>of("order", 3, "summary", "The gate answers")
        ));
        option.setCharactersInvolved(List.of(Map.<String, Object>of("name", "Ming")));
        option.setConflict(Map.<String, Object>of("external", "A disguised envoy tests the gate"));
        option.setHighlightMoment("Ming notices the forged seal.");
        option.setForeshadowActions(List.of());
        option.setMemoryReferences(List.of());
        option.setWhyThisPlan("It moves the conspiracy into the open.");
        option.setEndingHook("The seal answers to Ming's blood.");
        option.setRiskNotes(List.of());
        option.setStatus(OutlineOptionStatus.GENERATED);
        option.setCreatedAt(OffsetDateTime.parse("2026-06-19T12:00:00Z"));
        option.setUpdatedAt(OffsetDateTime.parse("2026-06-19T12:00:00Z"));
        return option;
    }

    private Chapter chapter() {
        Chapter chapter = new Chapter();
        chapter.setId(CHAPTER_ID);
        chapter.setStoryId(STORY_ID);
        chapter.setChapterNumber(1);
        chapter.setTitle("The Envoy");
        chapter.setWorkflowStage(ChapterWorkflowStage.OUTLINE_OPTIONS_GENERATED);
        chapter.setCreatedAt(OffsetDateTime.parse("2026-06-19T12:00:00Z"));
        chapter.setUpdatedAt(OffsetDateTime.parse("2026-06-19T12:00:00Z"));
        return chapter;
    }
}
