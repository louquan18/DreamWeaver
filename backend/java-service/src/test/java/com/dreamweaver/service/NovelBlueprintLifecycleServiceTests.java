package com.dreamweaver.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.when;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.dreamweaver.dto.AiBlueprintGenerateRequest;
import com.dreamweaver.dto.AiBlueprintGenerateResponse;
import com.dreamweaver.dto.NovelBlueprintConfirmRequest;
import com.dreamweaver.dto.NovelBlueprintGenerateRequest;
import com.dreamweaver.dto.NovelBlueprintUpdateRequest;
import com.dreamweaver.dto.StoryCreateRequest;
import com.dreamweaver.entity.NovelBlueprint;
import com.dreamweaver.entity.NovelBlueprintStatus;
import com.dreamweaver.entity.Story;
import com.dreamweaver.entity.StoryStatus;
import com.dreamweaver.repository.NovelBlueprintRepository;
import com.dreamweaver.repository.StoryRepository;

@ExtendWith(MockitoExtension.class)
class NovelBlueprintLifecycleServiceTests {

    private static final UUID STORY_ID = UUID.fromString("10000000-0000-0000-0000-000000000010");
    private static final UUID BLUEPRINT_ID = UUID.fromString("20000000-0000-0000-0000-000000000010");
    private static final String IDEA =
        "A cyberpunk detective discovers every unsolved case is a discarded chapter.";

    @Mock
    private StoryRepository storyRepository;

    @Mock
    private NovelBlueprintRepository blueprintRepository;

    @Mock
    private AiBlueprintClient aiBlueprintClient;

    @Test
    void ideaToConfirmedBlueprintLifecycleUsesJavaServicesAndPersistsEachStep() {
        Map<UUID, Story> stories = new LinkedHashMap<>();
        Map<UUID, NovelBlueprint> blueprints = new LinkedHashMap<>();
        StoryService storyService = new StoryService(storyRepository);
        NovelBlueprintService blueprintService = new NovelBlueprintService(
            blueprintRepository,
            storyRepository,
            aiBlueprintClient
        );

        when(storyRepository.save(any(Story.class))).thenAnswer(invocation -> {
            Story saved = invocation.getArgument(0);
            if (saved.getId() == null) {
                saved.setId(STORY_ID);
            }
            stories.put(saved.getId(), saved);
            return saved;
        });
        when(storyRepository.findById(STORY_ID))
            .thenAnswer(invocation -> Optional.ofNullable(stories.get(STORY_ID)));
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
        when(blueprintRepository.existsByStoryIdAndStatus(STORY_ID, NovelBlueprintStatus.CONFIRMED))
            .thenReturn(false);
        when(blueprintRepository.saveAndFlush(any(NovelBlueprint.class))).thenAnswer(invocation -> {
            NovelBlueprint saved = invocation.getArgument(0);
            blueprints.put(saved.getId(), saved);
            return saved;
        });

        Story story = storyService.create(new StoryCreateRequest(
            "Discarded Case Files",
            IDEA,
            "cyberpunk mystery",
            150000
        ));
        NovelBlueprintService.GeneratedBlueprint generated = blueprintService.generate(
            story.getId(),
            new NovelBlueprintGenerateRequest(IDEA, "cyberpunk mystery", "noir", 150000, Map.of())
        );
        assertThat(generated.blueprint().getStatus()).isEqualTo(NovelBlueprintStatus.GENERATED);

        NovelBlueprint edited = blueprintService.update(
            story.getId(),
            generated.blueprint().getId(),
            new NovelBlueprintUpdateRequest(
                null,
                "A detective hunts the author erasing people from reality.",
                null,
                "urgent noir",
                Map.<String, Object>of("name", "Rin Vale", "identity", "cold case detective"),
                null,
                null,
                null,
                null,
                null
            )
        );
        NovelBlueprintService.ConfirmedBlueprint confirmed = blueprintService.confirm(
            story.getId(),
            edited.getId(),
            new NovelBlueprintConfirmRequest(new NovelBlueprintUpdateRequest(
                null,
                null,
                null,
                "cinematic noir",
                null,
                null,
                null,
                null,
                null,
                null
            ))
        );

        assertThat(story.getStatus()).isEqualTo(StoryStatus.WRITING);
        assertThat(generated.blueprint().getStatus()).isEqualTo(NovelBlueprintStatus.CONFIRMED);
        assertThat(confirmed.blueprint().getStatus()).isEqualTo(NovelBlueprintStatus.CONFIRMED);
        assertThat(confirmed.blueprint().getConfirmedAt()).isNotNull();
        assertThat(confirmed.blueprint().getPremise())
            .isEqualTo("A detective hunts the author erasing people from reality.");
        assertThat(confirmed.blueprint().getTone()).isEqualTo("cinematic noir");
        assertThat(confirmed.blueprint().getProtagonist()).containsEntry("name", "Rin Vale");
        assertThat(confirmed.story()).isSameAs(story);

        ArgumentCaptor<AiBlueprintGenerateRequest> aiRequest =
            ArgumentCaptor.forClass(AiBlueprintGenerateRequest.class);
        verify(aiBlueprintClient).generateBlueprint(eq(STORY_ID), aiRequest.capture());
        assertThat(aiRequest.getValue().sourcePrompt()).isEqualTo(IDEA);
        verify(blueprintRepository, times(2)).save(any(NovelBlueprint.class));
        verify(blueprintRepository).saveAndFlush(confirmed.blueprint());
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
