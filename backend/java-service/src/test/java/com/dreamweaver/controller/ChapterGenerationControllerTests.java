package com.dreamweaver.controller;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import com.dreamweaver.entity.ChapterGeneration;
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
