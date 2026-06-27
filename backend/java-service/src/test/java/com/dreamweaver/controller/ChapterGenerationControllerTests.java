package com.dreamweaver.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.ChapterGeneration;
import com.dreamweaver.entity.ChapterStatus;
import com.dreamweaver.entity.ChapterWorkflowStage;
import com.dreamweaver.service.BadRequestException;
import com.dreamweaver.service.ChapterGenerationService;
import com.dreamweaver.service.ChapterService;
import com.fasterxml.jackson.databind.ObjectMapper;

class ChapterGenerationControllerTests {

    private static final UUID STORY_ID = UUID.fromString("10000000-0000-0000-0000-000000000070");
    private static final UUID CHAPTER_ID = UUID.fromString("20000000-0000-0000-0000-000000000070");
    private static final UUID GENERATION_ID = UUID.fromString("30000000-0000-0000-0000-000000000070");
    private static final UUID USER_ID = UUID.fromString("40000000-0000-0000-0000-000000000070");

    @Test
    void pythonDraftRequestCarriesConfirmedWritingContext() {
        ChapterGenerationController controller = new ChapterGenerationController(
            Mockito.mock(ChapterGenerationService.class),
            Mockito.mock(ChapterService.class),
            new ObjectMapper(),
            "http://python-ai:8000"
        );

        Map<String, Object> payload = controller.pythonDraftRequest(generation());

        assertThat(payload).containsEntry("generationId", GENERATION_ID.toString());
        assertThat(payload).containsEntry("targetWords", 2000);
        assertThat(payload).containsEntry("modelProfile", "writing");
        assertThat(payload).containsEntry("extraPrompt", "Keep the ending ominous.");
        assertThat(payload.get("blueprint"))
            .isEqualTo(Map.of("premise", "A betrayed disciple follows dream fire."));
        assertThat(payload.get("confirmedOutline"))
            .isEqualTo(Map.of("finalOutline", Map.of("endingHook", "The mirror speaks.")));
        assertThat(payload.get("recentChapters")).asList().hasSize(1);
        assertThat(payload.get("timeline")).isEqualTo(List.of(Map.of("id", "tl-1")));
        assertThat(payload.get("characters")).isEqualTo(List.of(Map.of("name", "Lin Jin")));
        assertThat(payload.get("world")).isEqualTo(List.of(Map.of("subject", "Mirror fire")));
        assertThat(payload.get("foreshadows")).isEqualTo(List.of(Map.of("id", "fs-1", "status", "triggered")));
        assertThat(payload.get("additionalMemory")).isEqualTo(List.of());
        assertThat(payload.get("contextMetadata")).isEqualTo(Map.of("policy", "structured-memory-v1"));
    }

    @Test
    void pythonDraftRequestDefaultsStructuredMemoryForOldGenerationSnapshots() {
        ChapterGenerationController controller = new ChapterGenerationController(
            Mockito.mock(ChapterGenerationService.class),
            Mockito.mock(ChapterService.class),
            new ObjectMapper(),
            "http://python-ai:8000"
        );

        Map<String, Object> payload = controller.pythonDraftRequest(oldGenerationSnapshot());

        assertThat(payload.get("timeline")).isEqualTo(List.of());
        assertThat(payload.get("characters")).isEqualTo(List.of());
        assertThat(payload.get("world")).isEqualTo(List.of());
        assertThat(payload.get("foreshadows")).isEqualTo(List.of());
        assertThat(payload.get("additionalMemory")).isEqualTo(List.of());
        assertThat(payload.get("contextMetadata")).isEqualTo(Map.of());
    }

    @Test
    void confirmDraftReturnsDraftConfirmedChapter() throws Exception {
        ChapterGenerationService generationService = Mockito.mock(ChapterGenerationService.class);
        MockMvc mockMvc = mockMvc(generationService);
        when(generationService.confirmDraft(eq(STORY_ID), eq(CHAPTER_ID), eq(GENERATION_ID)))
            .thenReturn(confirmedChapter());

        mockMvc.perform(post(
                    "/api/stories/{storyId}/chapters/{chapterId}/generations/{generationId}/confirm",
                    STORY_ID,
                    CHAPTER_ID,
                    GENERATION_ID
                ))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.id").value(CHAPTER_ID.toString()))
            .andExpect(jsonPath("$.status").value("approved"))
            .andExpect(jsonPath("$.workflowStage").value("draft_confirmed"))
            .andExpect(jsonPath("$.lastGenerationId").value(GENERATION_ID.toString()));
    }

    @Test
    void confirmDraftMapsBusinessValidationErrors() throws Exception {
        ChapterGenerationService generationService = Mockito.mock(ChapterGenerationService.class);
        MockMvc mockMvc = mockMvc(generationService);
        when(generationService.confirmDraft(eq(STORY_ID), eq(CHAPTER_ID), eq(GENERATION_ID)))
            .thenThrow(new BadRequestException("generation_not_succeeded", "Only succeeded generation can be confirmed"));

        mockMvc.perform(post(
                    "/api/stories/{storyId}/chapters/{chapterId}/generations/{generationId}/confirm",
                    STORY_ID,
                    CHAPTER_ID,
                    GENERATION_ID
                ))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.error").value("generation_not_succeeded"));
    }

    private MockMvc mockMvc(ChapterGenerationService generationService) {
        ChapterGenerationController controller = new ChapterGenerationController(
            generationService,
            Mockito.mock(ChapterService.class),
            new ObjectMapper(),
            "http://python-ai:8000"
        );
        return MockMvcBuilders.standaloneSetup(controller)
            .setControllerAdvice(new GlobalExceptionHandler())
            .build();
    }

    private Chapter confirmedChapter() {
        Chapter chapter = new Chapter();
        chapter.setId(CHAPTER_ID);
        chapter.setStoryId(STORY_ID);
        chapter.setChapterNumber(3);
        chapter.setTitle("Dream Fire Gate");
        chapter.setContent("The dream fire answered.");
        chapter.setWordCount(2400);
        chapter.setStatus(ChapterStatus.APPROVED);
        chapter.setWorkflowStage(ChapterWorkflowStage.DRAFT_CONFIRMED);
        chapter.setLastGenerationId(GENERATION_ID);
        return chapter;
    }

    private ChapterGeneration generation() {
        ChapterGeneration generation = new ChapterGeneration();
        generation.setId(GENERATION_ID);
        generation.setStoryId(STORY_ID);
        generation.setChapterId(CHAPTER_ID);
        generation.setUserId(USER_ID);
        generation.setRequest(Map.of(
            "extra_prompt", "Keep the ending ominous.",
            "target_words", 2000,
            "model_profile", "writing",
            "writing_context", Map.ofEntries(
                Map.entry("story", Map.of("title", "Dream Fire")),
                Map.entry("chapter", Map.of("chapterNumber", 3)),
                Map.entry("blueprint", Map.of("premise", "A betrayed disciple follows dream fire.")),
                Map.entry("confirmedOutline", Map.of(
                    "finalOutline",
                    Map.of("endingHook", "The mirror speaks.")
                )),
                Map.entry("recentChapters", List.of(Map.of("title", "Ash Road"))),
                Map.entry("timeline", List.of(Map.of("id", "tl-1"))),
                Map.entry("characters", List.of(Map.of("name", "Lin Jin"))),
                Map.entry("world", List.of(Map.of("subject", "Mirror fire"))),
                Map.entry("foreshadows", List.of(Map.of("id", "fs-1", "status", "triggered"))),
                Map.entry("additionalMemory", List.of()),
                Map.entry("contextMetadata", Map.of("policy", "structured-memory-v1"))
            )
        ));
        return generation;
    }

    private ChapterGeneration oldGenerationSnapshot() {
        ChapterGeneration generation = new ChapterGeneration();
        generation.setId(GENERATION_ID);
        generation.setStoryId(STORY_ID);
        generation.setChapterId(CHAPTER_ID);
        generation.setUserId(USER_ID);
        generation.setRequest(Map.of(
            "extra_prompt", "Keep the ending ominous.",
            "target_words", 2000,
            "model_profile", "writing",
            "writing_context", Map.of(
                "story", Map.of("title", "Dream Fire"),
                "chapter", Map.of("chapterNumber", 3),
                "blueprint", Map.of("premise", "A betrayed disciple follows dream fire."),
                "confirmedOutline", Map.of(
                    "finalOutline",
                    Map.of("endingHook", "The mirror speaks.")
                ),
                "recentChapters", List.of(Map.of("title", "Ash Road"))
            )
        ));
        return generation;
    }
}
