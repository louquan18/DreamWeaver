package com.dreamweaver.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
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
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import com.dreamweaver.dto.ChapterOutlineConfirmRequest;
import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.ChapterOutline;
import com.dreamweaver.entity.ChapterOutlineStatus;
import com.dreamweaver.entity.ChapterWorkflowStage;
import com.dreamweaver.service.BadRequestException;
import com.dreamweaver.service.ChapterOutlineService;

@WebMvcTest(ChapterOutlineController.class)
class ChapterOutlineControllerTests {

    private static final UUID STORY_ID = UUID.fromString("10000000-0000-0000-0000-000000000040");
    private static final UUID CHAPTER_ID = UUID.fromString("20000000-0000-0000-0000-000000000040");
    private static final UUID OPTION_ID = UUID.fromString("30000000-0000-0000-0000-000000000040");
    private static final UUID OUTLINE_ID = UUID.fromString("40000000-0000-0000-0000-000000000040");

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private ChapterOutlineService outlineService;

    @Test
    void confirmOutlineReturnsChapterAndOutline() throws Exception {
        when(outlineService.confirm(
            eq(STORY_ID),
            eq(CHAPTER_ID),
            any(ChapterOutlineConfirmRequest.class)
        )).thenReturn(new ChapterOutlineService.ConfirmedOutline(chapter(), outline()));

        mockMvc.perform(post(
                    "/api/stories/{storyId}/chapters/{chapterId}/outlines/confirm",
                    STORY_ID,
                    CHAPTER_ID
                )
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "sourceOptionIds": ["30000000-0000-0000-0000-000000000040"],
                      "userFeedback": "Use A structure and C hook",
                      "finalOutline": {
                        "titleCandidates": ["Dream Fire Gate"],
                        "chapterGoal": "Trace the token",
                        "storySummary": "Lin Jin follows the token.",
                        "sceneOutline": [
                          {"order": 1, "summary": "A", "purpose": "Open", "outcome": "A"},
                          {"order": 2, "summary": "B", "purpose": "Pressure", "outcome": "B"},
                          {"order": 3, "summary": "C", "purpose": "Hook", "outcome": "C"}
                        ],
                        "charactersInvolved": [{"name": "Lin Jin", "motivation": "Trace clues"}],
                        "conflict": {"stakes": "Memory erasure"},
                        "highlightMoment": "The token burns.",
                        "foreshadowActions": [],
                        "memoryReferences": [],
                        "whyThisPlan": "It blends selected options.",
                        "endingHook": "A voice speaks an old name.",
                        "riskNotes": []
                      }
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.chapter.id").value(CHAPTER_ID.toString()))
            .andExpect(jsonPath("$.chapter.workflowStage").value("outline_confirmed"))
            .andExpect(jsonPath("$.outline.id").value(OUTLINE_ID.toString()))
            .andExpect(jsonPath("$.outline.status").value("confirmed"))
            .andExpect(jsonPath("$.outline.sourceOptionIds[0]").value(OPTION_ID.toString()))
            .andExpect(jsonPath("$.outline.finalOutline.chapterGoal").value("Trace the token"));
    }

    @Test
    void confirmOutlineMapsBusinessValidationErrors() throws Exception {
        when(outlineService.confirm(
            eq(STORY_ID),
            eq(CHAPTER_ID),
            any(ChapterOutlineConfirmRequest.class)
        )).thenThrow(new BadRequestException("outline_invalid", "finalOutline.sceneOutline is required"));

        mockMvc.perform(post(
                    "/api/stories/{storyId}/chapters/{chapterId}/outlines/confirm",
                    STORY_ID,
                    CHAPTER_ID
                )
                .contentType(MediaType.APPLICATION_JSON)
                .content("{}"))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.error").value("outline_invalid"));
    }

    private Chapter chapter() {
        Chapter chapter = new Chapter();
        chapter.setId(CHAPTER_ID);
        chapter.setStoryId(STORY_ID);
        chapter.setChapterNumber(1);
        chapter.setTitle("Dream Fire Gate");
        chapter.setWorkflowStage(ChapterWorkflowStage.OUTLINE_CONFIRMED);
        return chapter;
    }

    private ChapterOutline outline() {
        ChapterOutline outline = new ChapterOutline();
        outline.setId(OUTLINE_ID);
        outline.setStoryId(STORY_ID);
        outline.setChapterId(CHAPTER_ID);
        outline.setSourceOptionIds(List.of(OPTION_ID));
        outline.setUserFeedback("Use A structure and C hook");
        outline.setFinalOutline(Map.of("chapterGoal", "Trace the token"));
        outline.setStatus(ChapterOutlineStatus.CONFIRMED);
        outline.setConfirmedAt(OffsetDateTime.parse("2026-06-19T12:00:00Z"));
        return outline;
    }
}
