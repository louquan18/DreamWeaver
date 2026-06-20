package com.dreamweaver.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import com.dreamweaver.dto.MemoryChangeSetConfirmRequest;
import com.dreamweaver.dto.MemoryChangeSetExtractRequest;
import com.dreamweaver.dto.MemoryChangeSetUpdateRequest;
import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.ChapterStatus;
import com.dreamweaver.entity.ChapterWorkflowStage;
import com.dreamweaver.entity.MemoryChangeSet;
import com.dreamweaver.entity.MemoryChangeSetStatus;
import com.dreamweaver.service.ConflictException;
import com.dreamweaver.service.MemoryChangeSetService;
import com.fasterxml.jackson.databind.ObjectMapper;

class MemoryChangeSetControllerTests {

    private static final UUID STORY_ID = UUID.fromString("10000000-0000-0000-0000-000000000090");
    private static final UUID CHAPTER_ID = UUID.fromString("20000000-0000-0000-0000-000000000090");
    private static final UUID GENERATION_ID = UUID.fromString("30000000-0000-0000-0000-000000000090");
    private static final UUID CHANGE_SET_ID = UUID.fromString("40000000-0000-0000-0000-000000000090");
    private static final UUID USER_ID = UUID.fromString("50000000-0000-0000-0000-000000000090");

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Test
    void extractReturnsPendingMemoryChangeSetJson() throws Exception {
        MemoryChangeSetService service = Mockito.mock(MemoryChangeSetService.class);
        when(service.extract(eq(STORY_ID), eq(CHAPTER_ID), any(MemoryChangeSetExtractRequest.class)))
            .thenReturn(changeSet(MemoryChangeSetStatus.PENDING));

        mockMvc(service).perform(post(
                    "/api/stories/{storyId}/chapters/{chapterId}/memory-change-sets/extract",
                    STORY_ID,
                    CHAPTER_ID
                )
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(objectMapper.writeValueAsString(Map.of("userId", USER_ID))))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.id").value(CHANGE_SET_ID.toString()))
            .andExpect(jsonPath("$.status").value("pending"))
            .andExpect(jsonPath("$.sourceGenerationId").value(GENERATION_ID.toString()))
            .andExpect(jsonPath("$.timelineChanges[0].changeId").value("timeline-1"))
            .andExpect(jsonPath("$.conflicts[0].message").value("needs review"));
    }

    @Test
    void listGetPatchAndConfirmExposeMemoryChangeSetJsonShape() throws Exception {
        MemoryChangeSetService service = Mockito.mock(MemoryChangeSetService.class);
        when(service.list(STORY_ID, CHAPTER_ID)).thenReturn(List.of(changeSet(MemoryChangeSetStatus.PENDING)));
        when(service.get(STORY_ID, CHAPTER_ID, CHANGE_SET_ID)).thenReturn(changeSet(MemoryChangeSetStatus.PENDING));
        when(service.update(
            eq(STORY_ID),
            eq(CHAPTER_ID),
            eq(CHANGE_SET_ID),
            any(MemoryChangeSetUpdateRequest.class)
        )).thenReturn(changeSet(MemoryChangeSetStatus.PENDING));
        when(service.confirm(
            eq(STORY_ID),
            eq(CHAPTER_ID),
            eq(CHANGE_SET_ID),
            any(MemoryChangeSetConfirmRequest.class)
        )).thenReturn(changeSet(MemoryChangeSetStatus.CONFIRMED));

        MockMvc mockMvc = mockMvc(service);

        mockMvc.perform(get(
                    "/api/stories/{storyId}/chapters/{chapterId}/memory-change-sets",
                    STORY_ID,
                    CHAPTER_ID
                ))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$[0].id").value(CHANGE_SET_ID.toString()));

        mockMvc.perform(get(
                    "/api/stories/{storyId}/chapters/{chapterId}/memory-change-sets/{changeSetId}",
                    STORY_ID,
                    CHAPTER_ID,
                    CHANGE_SET_ID
                ))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.id").value(CHANGE_SET_ID.toString()));

        mockMvc.perform(patch(
                    "/api/stories/{storyId}/chapters/{chapterId}/memory-change-sets/{changeSetId}",
                    STORY_ID,
                    CHAPTER_ID,
                    CHANGE_SET_ID
                )
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(objectMapper.writeValueAsString(Map.of(
                        "timelineChanges",
                        List.of(Map.of("changeId", "timeline-edited"))
                    ))))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("pending"));

        mockMvc.perform(post(
                    "/api/stories/{storyId}/chapters/{chapterId}/memory-change-sets/{changeSetId}/confirm",
                    STORY_ID,
                    CHAPTER_ID,
                    CHANGE_SET_ID
                )
                    .contentType(MediaType.APPLICATION_JSON)
                    .content(objectMapper.writeValueAsString(Map.of("userId", USER_ID))))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("confirmed"));
    }

    @Test
    void freezeReturnsChapterAndMemoryChangeSetJsonShape() throws Exception {
        MemoryChangeSetService service = Mockito.mock(MemoryChangeSetService.class);
        MemoryChangeSet frozenChangeSet = changeSet(MemoryChangeSetStatus.CONFIRMED);
        frozenChangeSet.setApplyResult(Map.of(
            "status",
            "applied",
            "counts",
            Map.of("timeline", 1, "character", 0, "world", 0, "foreshadow", 0)
        ));
        when(service.freeze(STORY_ID, CHAPTER_ID, CHANGE_SET_ID))
            .thenReturn(new MemoryChangeSetService.FreezeResult(frozenChapter(), frozenChangeSet));

        mockMvc(service).perform(post(
                    "/api/stories/{storyId}/chapters/{chapterId}/memory-change-sets/{changeSetId}/freeze",
                    STORY_ID,
                    CHAPTER_ID,
                    CHANGE_SET_ID
                ))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.chapter.id").value(CHAPTER_ID.toString()))
            .andExpect(jsonPath("$.chapter.status").value("approved"))
            .andExpect(jsonPath("$.chapter.workflowStage").value("chapter_confirmed"))
            .andExpect(jsonPath("$.memoryChangeSet.id").value(CHANGE_SET_ID.toString()))
            .andExpect(jsonPath("$.memoryChangeSet.status").value("confirmed"))
            .andExpect(jsonPath("$.memoryChangeSet.applyResult.status").value("applied"))
            .andExpect(jsonPath("$.memoryChangeSet.applyResult.counts.timeline").value(1));
    }

    @Test
    void freezeErrorsUseApiErrorShape() throws Exception {
        MemoryChangeSetService service = Mockito.mock(MemoryChangeSetService.class);
        when(service.freeze(STORY_ID, CHAPTER_ID, CHANGE_SET_ID)).thenThrow(new ConflictException(
            "memory_change_set_not_confirmed",
            "Only confirmed memory change set can be frozen"
        ));

        mockMvc(service).perform(post(
                    "/api/stories/{storyId}/chapters/{chapterId}/memory-change-sets/{changeSetId}/freeze",
                    STORY_ID,
                    CHAPTER_ID,
                    CHANGE_SET_ID
                ))
            .andExpect(status().isConflict())
            .andExpect(jsonPath("$.error").value("memory_change_set_not_confirmed"))
            .andExpect(jsonPath("$.message").value("Only confirmed memory change set can be frozen"));
    }

    private MockMvc mockMvc(MemoryChangeSetService service) {
        MemoryChangeSetController controller = new MemoryChangeSetController(service);
        return MockMvcBuilders.standaloneSetup(controller)
            .setControllerAdvice(new GlobalExceptionHandler())
            .build();
    }

    private MemoryChangeSet changeSet(MemoryChangeSetStatus status) {
        MemoryChangeSet changeSet = new MemoryChangeSet();
        changeSet.setId(CHANGE_SET_ID);
        changeSet.setStoryId(STORY_ID);
        changeSet.setChapterId(CHAPTER_ID);
        changeSet.setSourceGenerationId(GENERATION_ID);
        changeSet.setStatus(status);
        changeSet.setSchemaVersion(1);
        changeSet.setTimelineChanges(List.of(Map.of("changeId", "timeline-1", "memoryType", "timeline")));
        changeSet.setCharacterChanges(List.of());
        changeSet.setWorldChanges(List.of());
        changeSet.setForeshadowChanges(List.of());
        changeSet.setConflicts(List.of(Map.of("message", "needs review")));
        changeSet.setBaseMemoryFingerprint(Map.of("existingMemoryHash", "hash"));
        changeSet.setSourceDraftHash("draft-hash");
        changeSet.setExtractionMetadata(Map.of("summary", "One memory change."));
        return changeSet;
    }

    private Chapter frozenChapter() {
        Chapter chapter = new Chapter();
        chapter.setId(CHAPTER_ID);
        chapter.setStoryId(STORY_ID);
        chapter.setChapterNumber(2);
        chapter.setStatus(ChapterStatus.APPROVED);
        chapter.setWorkflowStage(ChapterWorkflowStage.CHAPTER_CONFIRMED);
        chapter.setLastGenerationId(GENERATION_ID);
        return chapter;
    }
}
