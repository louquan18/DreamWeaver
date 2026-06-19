package com.dreamweaver.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import com.dreamweaver.entity.NovelBlueprint;
import com.dreamweaver.entity.NovelBlueprintStatus;
import com.dreamweaver.entity.Story;
import com.dreamweaver.entity.StoryStatus;
import com.dreamweaver.service.AiWorkerException;
import com.dreamweaver.service.NovelBlueprintService;

@WebMvcTest(NovelBlueprintController.class)
class NovelBlueprintControllerTests {

    private static final UUID STORY_ID = UUID.fromString("10000000-0000-0000-0000-000000000001");
    private static final UUID BLUEPRINT_ID = UUID.fromString("20000000-0000-0000-0000-000000000001");

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private NovelBlueprintService blueprintService;

    @Test
    void generateReturnsStoryAndBlueprint() throws Exception {
        when(blueprintService.generate(eq(STORY_ID), any()))
            .thenReturn(new NovelBlueprintService.GeneratedBlueprint(validStory(), validBlueprint()));

        mockMvc.perform(post("/api/stories/{storyId}/blueprints/generate", STORY_ID)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "sourcePrompt": "A betrayed apprentice seeks the truth.",
                      "genre": "xianxia",
                      "tone": "tense",
                      "targetWords": 120000,
                      "preferences": {}
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.story.id").value(STORY_ID.toString()))
            .andExpect(jsonPath("$.blueprint.id").value(BLUEPRINT_ID.toString()))
            .andExpect(jsonPath("$.blueprint.storyId").value(STORY_ID.toString()))
            .andExpect(jsonPath("$.blueprint.status").value("generated"));
    }

    @Test
    void generateMapsAiWorkerFailureToBadGateway() throws Exception {
        when(blueprintService.generate(eq(STORY_ID), any()))
            .thenThrow(new AiWorkerException("ai_worker_error", "AI worker unavailable"));

        mockMvc.perform(post("/api/stories/{storyId}/blueprints/generate", STORY_ID)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "sourcePrompt": "A betrayed apprentice seeks the truth."
                    }
                    """))
            .andExpect(status().isBadGateway())
            .andExpect(jsonPath("$.error").value("ai_worker_error"))
            .andExpect(jsonPath("$.message").value("AI worker unavailable"));
    }

    @Test
    void updateAcceptsFrontendBlueprintEdits() throws Exception {
        NovelBlueprint edited = validBlueprint();
        edited.setPremise("A revised premise after frontend review.");
        edited.setTone("urgent");

        when(blueprintService.update(eq(STORY_ID), eq(BLUEPRINT_ID), any()))
            .thenReturn(edited);

        mockMvc.perform(patch("/api/stories/{storyId}/blueprints/{blueprintId}", STORY_ID, BLUEPRINT_ID)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "premise": "A revised premise after frontend review.",
                      "tone": "urgent",
                      "protagonist": {
                        "name": "Ming",
                        "identity": "exiled archivist"
                      }
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.id").value(BLUEPRINT_ID.toString()))
            .andExpect(jsonPath("$.storyId").value(STORY_ID.toString()))
            .andExpect(jsonPath("$.premise").value("A revised premise after frontend review."))
            .andExpect(jsonPath("$.tone").value("urgent"))
            .andExpect(jsonPath("$.status").value("generated"));
    }

    @Test
    void confirmReturnsWritingStoryAndConfirmedBlueprint() throws Exception {
        Story story = validStory();
        story.setStatus(StoryStatus.WRITING);
        NovelBlueprint confirmed = validBlueprint();
        confirmed.setStatus(NovelBlueprintStatus.CONFIRMED);

        when(blueprintService.confirm(eq(STORY_ID), eq(BLUEPRINT_ID), any()))
            .thenReturn(new NovelBlueprintService.ConfirmedBlueprint(story, confirmed));

        mockMvc.perform(post("/api/stories/{storyId}/blueprints/{blueprintId}/confirm", STORY_ID, BLUEPRINT_ID)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "editedBlueprint": {
                        "tone": "urgent",
                        "lockedFacts": [
                          { "text": "No flight before foundation" }
                        ]
                      }
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.story.id").value(STORY_ID.toString()))
            .andExpect(jsonPath("$.story.status").value("writing"))
            .andExpect(jsonPath("$.blueprint.id").value(BLUEPRINT_ID.toString()))
            .andExpect(jsonPath("$.blueprint.status").value("confirmed"));
    }

    private Story validStory() {
        Story story = new Story();
        story.setId(STORY_ID);
        story.setUserId(UUID.fromString("00000000-0000-0000-0000-000000000001"));
        story.setTitle("Test Story");
        story.setStatus(StoryStatus.DRAFT);
        return story;
    }

    private NovelBlueprint validBlueprint() {
        NovelBlueprint blueprint = new NovelBlueprint();
        blueprint.setId(BLUEPRINT_ID);
        blueprint.setStoryId(STORY_ID);
        blueprint.setPremise("A betrayed apprentice seeks the truth.");
        blueprint.setGenre("xianxia");
        blueprint.setTone("tense");
        blueprint.setProtagonist(Map.<String, Object>of("name", "Ming"));
        blueprint.setMainThread(Map.<String, Object>of("goal", "Expose the sect conspiracy"));
        blueprint.setCoreConflict(Map.<String, Object>of("external", "Sect hunters"));
        blueprint.setWorldSeed(Map.<String, Object>of("rules", List.of()));
        blueprint.setWritingPreferences(Map.<String, Object>of("pacing", "fast"));
        blueprint.setLockedFacts(List.of(Map.<String, Object>of("text", "No flight before foundation")));
        blueprint.setStatus(NovelBlueprintStatus.GENERATED);
        return blueprint;
    }
}
