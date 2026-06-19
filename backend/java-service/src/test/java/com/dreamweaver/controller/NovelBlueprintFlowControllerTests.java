package com.dreamweaver.controller;

import static org.hamcrest.Matchers.notNullValue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import com.dreamweaver.dto.AiBlueprintGenerateRequest;
import com.dreamweaver.dto.AiBlueprintGenerateResponse;
import com.dreamweaver.entity.NovelBlueprint;
import com.dreamweaver.entity.NovelBlueprintStatus;
import com.dreamweaver.entity.Story;
import com.dreamweaver.entity.StoryStatus;
import com.dreamweaver.repository.NovelBlueprintRepository;
import com.dreamweaver.repository.StoryRepository;
import com.dreamweaver.service.AiBlueprintClient;
import com.dreamweaver.service.NovelBlueprintService;

@WebMvcTest(NovelBlueprintController.class)
@Import(NovelBlueprintService.class)
class NovelBlueprintFlowControllerTests {

    private static final UUID STORY_ID = UUID.fromString("10000000-0000-0000-0000-000000000020");
    private static final UUID BLUEPRINT_ID = UUID.fromString("20000000-0000-0000-0000-000000000020");
    private static final String IDEA =
        "A cyberpunk detective discovers every unsolved case is a discarded chapter.";

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private StoryRepository storyRepository;

    @MockBean
    private NovelBlueprintRepository blueprintRepository;

    @MockBean
    private AiBlueprintClient aiBlueprintClient;

    private final Map<UUID, Story> stories = new LinkedHashMap<>();
    private final Map<UUID, NovelBlueprint> blueprints = new LinkedHashMap<>();

    @BeforeEach
    void setUp() {
        Story story = new Story();
        story.setId(STORY_ID);
        story.setUserId(UUID.fromString("00000000-0000-0000-0000-000000000001"));
        story.setTitle("Discarded Case Files");
        story.setStatus(StoryStatus.DRAFT);
        stories.put(STORY_ID, story);

        when(storyRepository.findById(STORY_ID))
            .thenAnswer(invocation -> Optional.ofNullable(stories.get(STORY_ID)));
        when(storyRepository.save(any(Story.class))).thenAnswer(invocation -> {
            Story saved = invocation.getArgument(0);
            stories.put(saved.getId(), saved);
            return saved;
        });
        when(aiBlueprintClient.generateBlueprint(eq(STORY_ID), any(AiBlueprintGenerateRequest.class)))
            .thenReturn(validAiBlueprint());
        when(blueprintRepository.save(any(NovelBlueprint.class))).thenAnswer(invocation -> {
            NovelBlueprint saved = invocation.getArgument(0);
            if (saved.getId() == null) {
                saved.setId(BLUEPRINT_ID);
            }
            blueprints.put(saved.getId(), saved);
            return saved;
        });
        when(blueprintRepository.findByIdAndStoryId(BLUEPRINT_ID, STORY_ID))
            .thenAnswer(invocation -> Optional.ofNullable(blueprints.get(BLUEPRINT_ID)));
        when(blueprintRepository.findFirstByStoryIdAndStatusOrderByCreatedAtDesc(
            STORY_ID,
            NovelBlueprintStatus.CONFIRMED
        )).thenAnswer(invocation -> blueprints.values().stream()
            .filter(blueprint -> blueprint.getStoryId().equals(STORY_ID))
            .filter(blueprint -> blueprint.getStatus() == NovelBlueprintStatus.CONFIRMED)
            .findFirst());
        when(blueprintRepository.findFirstByStoryIdAndStatusOrderByCreatedAtDesc(
            STORY_ID,
            NovelBlueprintStatus.GENERATED
        )).thenAnswer(invocation -> blueprints.values().stream()
            .filter(blueprint -> blueprint.getStoryId().equals(STORY_ID))
            .filter(blueprint -> blueprint.getStatus() == NovelBlueprintStatus.GENERATED)
            .findFirst());
        when(blueprintRepository.existsByStoryIdAndStatus(STORY_ID, NovelBlueprintStatus.CONFIRMED))
            .thenAnswer(invocation -> blueprints.values().stream()
                .anyMatch(blueprint -> blueprint.getStoryId().equals(STORY_ID)
                    && blueprint.getStatus() == NovelBlueprintStatus.CONFIRMED));
        when(blueprintRepository.saveAndFlush(any(NovelBlueprint.class))).thenAnswer(invocation -> {
            NovelBlueprint saved = invocation.getArgument(0);
            blueprints.put(saved.getId(), saved);
            return saved;
        });
    }

    @Test
    void ideaToGeneratedEditedAndConfirmedBlueprintStaysBehindJavaApi() throws Exception {
        mockMvc.perform(post("/api/stories/{storyId}/blueprints/generate", STORY_ID)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "sourcePrompt": "A cyberpunk detective discovers every unsolved case is a discarded chapter.",
                      "genre": "cyberpunk mystery",
                      "tone": "noir",
                      "targetWords": 150000,
                      "preferences": {}
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.story.id").value(STORY_ID.toString()))
            .andExpect(jsonPath("$.story.status").value("draft"))
            .andExpect(jsonPath("$.blueprint.id").value(BLUEPRINT_ID.toString()))
            .andExpect(jsonPath("$.blueprint.status").value("generated"));

        mockMvc.perform(get("/api/stories/{storyId}/blueprints/current", STORY_ID))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.id").value(BLUEPRINT_ID.toString()))
            .andExpect(jsonPath("$.status").value("generated"));

        mockMvc.perform(patch("/api/stories/{storyId}/blueprints/{blueprintId}", STORY_ID, BLUEPRINT_ID)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "premise": "A detective hunts the author erasing people from reality.",
                      "tone": "urgent noir",
                      "protagonist": {
                        "name": "Rin Vale",
                        "identity": "cold case detective"
                      },
                      "lockedFacts": [
                        { "text": "Case files cannot be destroyed, only revised" }
                      ]
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.premise").value("A detective hunts the author erasing people from reality."))
            .andExpect(jsonPath("$.tone").value("urgent noir"))
            .andExpect(jsonPath("$.protagonist.name").value("Rin Vale"));

        mockMvc.perform(post("/api/stories/{storyId}/blueprints/{blueprintId}/confirm", STORY_ID, BLUEPRINT_ID)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "editedBlueprint": {
                        "tone": "cinematic noir",
                        "mainThread": {
                          "goal": "Find the author behind the erased cases"
                        },
                        "coreConflict": {
                          "external": "A publisher syndicate rewriting evidence"
                        },
                        "worldSeed": {
                          "setting": "Rainbound megacity",
                          "rules": [
                            { "description": "Edited cases rewrite public memory" }
                          ]
                        },
                        "lockedFacts": [
                          { "text": "Case files cannot be destroyed, only revised" }
                        ]
                      }
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.story.status").value("writing"))
            .andExpect(jsonPath("$.blueprint.status").value("confirmed"))
            .andExpect(jsonPath("$.blueprint.confirmedAt", notNullValue()))
            .andExpect(jsonPath("$.blueprint.tone").value("cinematic noir"));
    }

    private AiBlueprintGenerateResponse validAiBlueprint() {
        return new AiBlueprintGenerateResponse(
            STORY_ID.toString(),
            IDEA,
            "A detective finds that cold cases are missing chapters in a living manuscript.",
            "cyberpunk mystery",
            "noir",
            Map.<String, Object>of("name", "Rin", "identity", "detective"),
            Map.<String, Object>of("goal", "Find the author behind the erased cases"),
            Map.<String, Object>of("external", "A publisher syndicate rewriting evidence"),
            Map.<String, Object>of(
                "setting",
                "Rainbound megacity",
                "rules",
                List.of(Map.<String, Object>of("description", "Edited cases rewrite public memory"))
            ),
            Map.<String, Object>of("pace", "investigative"),
            List.of(Map.<String, Object>of("text", "Case files cannot be destroyed, only revised")),
            List.of(),
            "generated"
        );
    }
}
