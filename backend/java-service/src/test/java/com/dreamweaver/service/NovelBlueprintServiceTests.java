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

import com.dreamweaver.dto.AiBlueprintGenerateResponse;
import com.dreamweaver.dto.NovelBlueprintConfirmRequest;
import com.dreamweaver.dto.NovelBlueprintGenerateRequest;
import com.dreamweaver.dto.NovelBlueprintUpdateRequest;
import com.dreamweaver.entity.NovelBlueprint;
import com.dreamweaver.entity.NovelBlueprintStatus;
import com.dreamweaver.entity.Story;
import com.dreamweaver.entity.StoryStatus;
import com.dreamweaver.repository.NovelBlueprintRepository;
import com.dreamweaver.repository.StoryRepository;

@ExtendWith(MockitoExtension.class)
class NovelBlueprintServiceTests {

    private static final UUID STORY_ID = UUID.fromString("10000000-0000-0000-0000-000000000001");
    private static final UUID BLUEPRINT_ID = UUID.fromString("20000000-0000-0000-0000-000000000001");

    @Mock
    private NovelBlueprintRepository blueprintRepository;

    @Mock
    private StoryRepository storyRepository;

    @Mock
    private AiBlueprintClient aiBlueprintClient;

    private NovelBlueprintService service;
    private Story story;
    private NovelBlueprint blueprint;

    @BeforeEach
    void setUp() {
        service = new NovelBlueprintService(blueprintRepository, storyRepository, aiBlueprintClient);
        story = validStory();
        blueprint = validBlueprint();
    }

    @Test
    void generateStoresAiBlueprintDraft() {
        when(storyRepository.findById(STORY_ID)).thenReturn(Optional.of(story));
        when(aiBlueprintClient.generateBlueprint(any(), any()))
            .thenReturn(validAiBlueprint());
        when(blueprintRepository.save(any(NovelBlueprint.class)))
            .thenAnswer(invocation -> {
                NovelBlueprint saved = invocation.getArgument(0);
                saved.setId(BLUEPRINT_ID);
                return saved;
            });

        NovelBlueprintService.GeneratedBlueprint result =
            service.generate(STORY_ID, generateRequest());

        assertThat(result.story()).isSameAs(story);
        assertThat(result.blueprint().getStoryId()).isEqualTo(STORY_ID);
        assertThat(result.blueprint().getStatus()).isEqualTo(NovelBlueprintStatus.GENERATED);
        assertThat(result.blueprint().getPremise()).isEqualTo("A betrayed apprentice seeks the truth.");
        assertThat(result.blueprint().getProtagonist()).containsEntry("name", "Ming");
        verify(aiBlueprintClient).generateBlueprint(any(), any());
        verify(blueprintRepository).save(any(NovelBlueprint.class));
    }

    @Test
    void generateRejectsMissingStoryBeforeCallingAi() {
        when(storyRepository.findById(STORY_ID)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.generate(STORY_ID, generateRequest()))
            .isInstanceOf(ResourceNotFoundException.class)
            .hasMessageContaining("Story not found");

        verify(aiBlueprintClient, never()).generateBlueprint(any(), any());
        verify(blueprintRepository, never()).save(any(NovelBlueprint.class));
    }

    @Test
    void generateDoesNotSaveWhenAiWorkerFails() {
        when(storyRepository.findById(STORY_ID)).thenReturn(Optional.of(story));
        when(aiBlueprintClient.generateBlueprint(any(), any()))
            .thenThrow(new AiWorkerException("ai_worker_error", "AI worker unavailable"));

        assertThatThrownBy(() -> service.generate(STORY_ID, generateRequest()))
            .isInstanceOf(AiWorkerException.class)
            .hasMessageContaining("AI worker unavailable");

        verify(blueprintRepository, never()).save(any(NovelBlueprint.class));
    }

    @Test
    void generateRejectsIncompleteAiBlueprint() {
        when(storyRepository.findById(STORY_ID)).thenReturn(Optional.of(story));
        when(aiBlueprintClient.generateBlueprint(any(), any()))
            .thenReturn(new AiBlueprintGenerateResponse(
                STORY_ID.toString(),
                "source",
                null,
                null,
                null,
                Map.of(),
                Map.of(),
                Map.of(),
                Map.of(),
                Map.of(),
                List.of(),
                List.of(),
                "generated"
            ));

        assertThatThrownBy(() -> service.generate(STORY_ID, generateRequest()))
            .isInstanceOf(AiWorkerException.class)
            .hasMessageContaining("without premise");

        verify(blueprintRepository, never()).save(any(NovelBlueprint.class));
    }

    @Test
    void updateAllowsGeneratedBlueprint() {
        when(storyRepository.findById(STORY_ID)).thenReturn(Optional.of(story));
        when(blueprintRepository.findByIdAndStoryId(BLUEPRINT_ID, STORY_ID))
            .thenReturn(Optional.of(blueprint));
        when(blueprintRepository.save(any(NovelBlueprint.class)))
            .thenAnswer(invocation -> invocation.getArgument(0));

        NovelBlueprintUpdateRequest request = new NovelBlueprintUpdateRequest(
            null,
            "A revised premise",
            null,
            "fast",
            Map.<String, Object>of("name", "Ming", "initialGoal", "survive"),
            null,
            null,
            null,
            null,
            null
        );

        NovelBlueprint updated = service.update(STORY_ID, BLUEPRINT_ID, request);

        assertThat(updated.getPremise()).isEqualTo("A revised premise");
        assertThat(updated.getTone()).isEqualTo("fast");
        assertThat(updated.getProtagonist()).containsEntry("name", "Ming");
        verify(blueprintRepository).save(blueprint);
    }

    @Test
    void updateRejectsConfirmedBlueprint() {
        blueprint.setStatus(NovelBlueprintStatus.CONFIRMED);
        when(storyRepository.findById(STORY_ID)).thenReturn(Optional.of(story));
        when(blueprintRepository.findByIdAndStoryId(BLUEPRINT_ID, STORY_ID))
            .thenReturn(Optional.of(blueprint));

        assertThatThrownBy(() -> service.update(
            STORY_ID,
            BLUEPRINT_ID,
            new NovelBlueprintUpdateRequest(null, "New premise", null, null, null, null, null, null, null, null)
        ))
            .isInstanceOf(ConflictException.class)
            .hasMessageContaining("Only generated blueprints can be edited");

        verify(blueprintRepository, never()).save(any(NovelBlueprint.class));
    }

    @Test
    void confirmMarksBlueprintConfirmedAndStoryWriting() {
        when(storyRepository.findById(STORY_ID)).thenReturn(Optional.of(story));
        when(blueprintRepository.findByIdAndStoryId(BLUEPRINT_ID, STORY_ID))
            .thenReturn(Optional.of(blueprint));
        when(blueprintRepository.existsByStoryIdAndStatus(STORY_ID, NovelBlueprintStatus.CONFIRMED))
            .thenReturn(false);
        when(storyRepository.save(any(Story.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(blueprintRepository.saveAndFlush(any(NovelBlueprint.class)))
            .thenAnswer(invocation -> invocation.getArgument(0));

        NovelBlueprintService.ConfirmedBlueprint result =
            service.confirm(STORY_ID, BLUEPRINT_ID, null);

        assertThat(result.blueprint().getStatus()).isEqualTo(NovelBlueprintStatus.CONFIRMED);
        assertThat(result.blueprint().getConfirmedAt()).isNotNull();
        assertThat(result.story().getStatus()).isEqualTo(StoryStatus.WRITING);
        verify(storyRepository).save(story);
        verify(blueprintRepository).saveAndFlush(blueprint);
    }

    @Test
    void confirmAppliesFinalEditBeforeValidation() {
        blueprint.setProtagonist(Map.of());
        when(storyRepository.findById(STORY_ID)).thenReturn(Optional.of(story));
        when(blueprintRepository.findByIdAndStoryId(BLUEPRINT_ID, STORY_ID))
            .thenReturn(Optional.of(blueprint));
        when(blueprintRepository.existsByStoryIdAndStatus(STORY_ID, NovelBlueprintStatus.CONFIRMED))
            .thenReturn(false);
        when(storyRepository.save(any(Story.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(blueprintRepository.saveAndFlush(any(NovelBlueprint.class)))
            .thenAnswer(invocation -> invocation.getArgument(0));

        NovelBlueprintUpdateRequest edit = new NovelBlueprintUpdateRequest(
            null,
            null,
            null,
            null,
            Map.<String, Object>of("name", "Ming", "initialGoal", "survive"),
            null,
            null,
            null,
            null,
            null
        );

        NovelBlueprintService.ConfirmedBlueprint result =
            service.confirm(STORY_ID, BLUEPRINT_ID, new NovelBlueprintConfirmRequest(edit));

        assertThat(result.blueprint().getProtagonist()).containsEntry("name", "Ming");
        assertThat(result.blueprint().getStatus()).isEqualTo(NovelBlueprintStatus.CONFIRMED);
    }

    @Test
    void confirmRejectsStoryWithExistingConfirmedBlueprint() {
        when(storyRepository.findById(STORY_ID)).thenReturn(Optional.of(story));
        when(blueprintRepository.findByIdAndStoryId(BLUEPRINT_ID, STORY_ID))
            .thenReturn(Optional.of(blueprint));
        when(blueprintRepository.existsByStoryIdAndStatus(STORY_ID, NovelBlueprintStatus.CONFIRMED))
            .thenReturn(true);

        assertThatThrownBy(() -> service.confirm(STORY_ID, BLUEPRINT_ID, null))
            .isInstanceOf(ConflictException.class)
            .hasMessageContaining("Story already has a confirmed blueprint");

        assertThat(blueprint.getStatus()).isEqualTo(NovelBlueprintStatus.GENERATED);
        assertThat(story.getStatus()).isEqualTo(StoryStatus.DRAFT);
        verify(storyRepository, never()).save(any(Story.class));
        verify(blueprintRepository, never()).saveAndFlush(any(NovelBlueprint.class));
    }

    private Story validStory() {
        Story validStory = new Story();
        validStory.setId(STORY_ID);
        validStory.setUserId(UUID.fromString("00000000-0000-0000-0000-000000000001"));
        validStory.setTitle("Test Story");
        validStory.setStatus(StoryStatus.DRAFT);
        return validStory;
    }

    private NovelBlueprintGenerateRequest generateRequest() {
        return new NovelBlueprintGenerateRequest(
            "A betrayed apprentice seeks the truth.",
            "xianxia",
            "tense",
            120000,
            Map.of()
        );
    }

    private AiBlueprintGenerateResponse validAiBlueprint() {
        return new AiBlueprintGenerateResponse(
            STORY_ID.toString(),
            "A betrayed apprentice seeks the truth.",
            "A betrayed apprentice seeks the truth.",
            "xianxia",
            "tense",
            Map.<String, Object>of("name", "Ming", "initialGoal", "survive"),
            Map.<String, Object>of("goal", "Expose the sect conspiracy"),
            Map.<String, Object>of("external", "Sect hunters"),
            Map.<String, Object>of(
                "rules",
                List.of(Map.<String, Object>of("description", "No flight before foundation"))
            ),
            Map.<String, Object>of("pacing", "fast"),
            List.of(Map.<String, Object>of("text", "No flight before foundation")),
            List.of(),
            "generated"
        );
    }

    private NovelBlueprint validBlueprint() {
        NovelBlueprint validBlueprint = new NovelBlueprint();
        validBlueprint.setId(BLUEPRINT_ID);
        validBlueprint.setStoryId(STORY_ID);
        validBlueprint.setPremise("A betrayed apprentice seeks the truth.");
        validBlueprint.setProtagonist(Map.<String, Object>of("name", "Ming", "initialGoal", "survive"));
        validBlueprint.setMainThread(Map.<String, Object>of("goal", "Expose the sect conspiracy"));
        validBlueprint.setCoreConflict(Map.<String, Object>of("external", "Sect hunters"));
        validBlueprint.setWorldSeed(Map.<String, Object>of(
            "rules",
            List.of(Map.<String, Object>of("description", "No flight before foundation"))
        ));
        validBlueprint.setLockedFacts(List.of(Map.<String, Object>of("text", "No flight before foundation")));
        validBlueprint.setStatus(NovelBlueprintStatus.GENERATED);
        return validBlueprint;
    }
}
