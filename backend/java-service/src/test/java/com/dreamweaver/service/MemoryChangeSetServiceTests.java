package com.dreamweaver.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicReference;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.dreamweaver.dto.AiMemoryExtractionRequest;
import com.dreamweaver.dto.AiMemoryExtractionResponse;
import com.dreamweaver.dto.MemoryChangeSetConfirmRequest;
import com.dreamweaver.dto.MemoryChangeSetExtractRequest;
import com.dreamweaver.dto.MemoryChangeSetUpdateRequest;
import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.ChapterStatus;
import com.dreamweaver.entity.ChapterGeneration;
import com.dreamweaver.entity.ChapterWorkflowStage;
import com.dreamweaver.entity.GenerationStatus;
import com.dreamweaver.entity.MemoryChangeSet;
import com.dreamweaver.entity.MemoryChangeSetStatus;
import com.dreamweaver.repository.ChapterGenerationRepository;
import com.dreamweaver.repository.ChapterRepository;
import com.dreamweaver.repository.MemoryChangeSetRepository;

@ExtendWith(MockitoExtension.class)
class MemoryChangeSetServiceTests {

    private static final UUID STORY_ID = UUID.fromString("10000000-0000-0000-0000-000000000080");
    private static final UUID CHAPTER_ID = UUID.fromString("20000000-0000-0000-0000-000000000080");
    private static final UUID GENERATION_ID = UUID.fromString("30000000-0000-0000-0000-000000000080");
    private static final UUID CHANGE_SET_ID = UUID.fromString("40000000-0000-0000-0000-000000000080");
    private static final UUID USER_ID = UUID.fromString("50000000-0000-0000-0000-000000000080");
    private static final String CONFIRMED_DRAFT = "The dream fire marked Lin Jin's palm.";

    @Mock
    private MemoryChangeSetRepository changeSetRepository;

    @Mock
    private ChapterRepository chapterRepository;

    @Mock
    private ChapterGenerationRepository generationRepository;

    @Mock
    private AiMemoryClient aiMemoryClient;

    @Test
    void extractSavesPendingChangeSetGroupedByMemoryType() {
        Chapter chapter = confirmedDraftChapter();
        ChapterGeneration generation = generation();
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        when(changeSetRepository.findByStoryIdAndChapterIdAndSourceGenerationId(
            STORY_ID,
            CHAPTER_ID,
            GENERATION_ID
        )).thenReturn(Optional.empty());
        when(generationRepository.findByIdAndStoryIdAndChapterId(
            GENERATION_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(generation));
        when(aiMemoryClient.extractMemoryChanges(any(), any(), any())).thenReturn(aiResponse());
        when(changeSetRepository.save(any(MemoryChangeSet.class))).thenAnswer(invocation -> {
            MemoryChangeSet changeSet = invocation.getArgument(0);
            changeSet.setId(CHANGE_SET_ID);
            return changeSet;
        });
        when(chapterRepository.save(any(Chapter.class))).thenAnswer(invocation -> invocation.getArgument(0));

        MemoryChangeSet saved = service().extract(
            STORY_ID,
            CHAPTER_ID,
            new MemoryChangeSetExtractRequest(USER_ID, Map.of())
        );

        assertThat(saved.getStatus()).isEqualTo(MemoryChangeSetStatus.PENDING);
        assertThat(saved.getTimelineChanges()).hasSize(1);
        assertThat(saved.getCharacterChanges()).hasSize(1);
        assertThat(saved.getWorldChanges()).hasSize(1);
        assertThat(saved.getForeshadowChanges()).hasSize(1);
        assertThat(saved.getConflicts()).hasSize(2);
        assertThat(saved.getSourceDraftHash()).isEqualTo(sha256(CONFIRMED_DRAFT));
        assertThat(saved.getSchemaVersion()).isEqualTo(1);
        assertThat(saved.getBaseMemoryFingerprint()).containsEntry("existingMemoryHash", sha256("{}"));
        assertThat(saved.getExtractionMetadata())
            .containsEntry("source", "python-ai")
            .containsEntry("summary", "Four pending memory changes.");
        assertThat(chapter.getWorkflowStage()).isEqualTo(ChapterWorkflowStage.MEMORY_PENDING_CONFIRMATION);

        ArgumentCaptor<AiMemoryExtractionRequest> requestCaptor =
            ArgumentCaptor.forClass(AiMemoryExtractionRequest.class);
        verify(aiMemoryClient).extractMemoryChanges(eq(STORY_ID), eq(CHAPTER_ID), requestCaptor.capture());
        AiMemoryExtractionRequest aiRequest = requestCaptor.getValue();
        assertThat(aiRequest.confirmedDraft()).isEqualTo(CONFIRMED_DRAFT);
        assertThat(aiRequest.story()).containsEntry("title", "Dream Fire");
        assertThat(aiRequest.blueprint()).containsKey("lockedFacts");
        assertThat(aiRequest.confirmedOutline()).containsEntry("chapterGoal", "Awaken the mark");
        assertThat(aiRequest.existingMemory()).isEmpty();
    }

    @Test
    void extractReturnsExistingChangeSetForSameSourceGeneration() {
        Chapter chapter = confirmedDraftChapter();
        MemoryChangeSet existing = pendingChangeSet();
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        when(changeSetRepository.findByStoryIdAndChapterIdAndSourceGenerationId(
            STORY_ID,
            CHAPTER_ID,
            GENERATION_ID
        )).thenReturn(Optional.of(existing));

        MemoryChangeSet result = service().extract(
            STORY_ID,
            CHAPTER_ID,
            new MemoryChangeSetExtractRequest(USER_ID, Map.of())
        );

        assertThat(result).isSameAs(existing);
        verify(aiMemoryClient, never()).extractMemoryChanges(any(), any(), any());
        verify(changeSetRepository, never()).save(any(MemoryChangeSet.class));
    }

    @Test
    void updateReplacesEditablePendingJsonFields() {
        MemoryChangeSet pending = pendingChangeSet();
        when(changeSetRepository.findForUpdateByIdAndStoryIdAndChapterId(
            CHANGE_SET_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(pending));
        when(changeSetRepository.save(any(MemoryChangeSet.class))).thenAnswer(invocation -> invocation.getArgument(0));

        MemoryChangeSet updated = service().update(
            STORY_ID,
            CHAPTER_ID,
            CHANGE_SET_ID,
            new MemoryChangeSetUpdateRequest(
                List.of(Map.of("changeId", "timeline-edited", "memoryType", "timeline")),
                List.of(),
                List.of(Map.of("changeId", "world-edited", "memoryType", "world")),
                List.of(),
                List.of(Map.of("message", "needs review")),
                Map.of("editorNote", "trimmed")
            )
        );

        assertThat(updated.getTimelineChanges().getFirst()).containsEntry("changeId", "timeline-edited");
        assertThat(updated.getWorldChanges().getFirst()).containsEntry("changeId", "world-edited");
        assertThat(updated.getConflicts().getFirst()).containsEntry("message", "needs review");
        assertThat(updated.getExtractionMetadata()).containsEntry("editorNote", "trimmed");
    }

    @Test
    void memoryChangeSetCanMoveThroughExtractEditConfirmAndFreeze() {
        Chapter chapter = confirmedDraftChapter();
        ChapterGeneration generation = generation();
        AtomicReference<MemoryChangeSet> storedChangeSet = new AtomicReference<>();

        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        when(changeSetRepository.findByStoryIdAndChapterIdAndSourceGenerationId(
            STORY_ID,
            CHAPTER_ID,
            GENERATION_ID
        )).thenReturn(Optional.empty());
        when(generationRepository.findByIdAndStoryIdAndChapterId(
            GENERATION_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(generation));
        when(aiMemoryClient.extractMemoryChanges(any(), any(), any())).thenReturn(aiResponse());
        when(changeSetRepository.findForUpdateByIdAndStoryIdAndChapterId(
            CHANGE_SET_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenAnswer(invocation -> Optional.ofNullable(storedChangeSet.get()));
        when(changeSetRepository.save(any(MemoryChangeSet.class))).thenAnswer(invocation -> {
            MemoryChangeSet changeSet = invocation.getArgument(0);
            if (changeSet.getId() == null) {
                changeSet.setId(CHANGE_SET_ID);
            }
            storedChangeSet.set(changeSet);
            return changeSet;
        });
        when(chapterRepository.save(any(Chapter.class))).thenAnswer(invocation -> invocation.getArgument(0));

        MemoryChangeSet extracted = service().extract(
            STORY_ID,
            CHAPTER_ID,
            new MemoryChangeSetExtractRequest(USER_ID, Map.of("trigger", "test-loop"))
        );

        assertThat(extracted.getStatus()).isEqualTo(MemoryChangeSetStatus.PENDING);
        assertThat(extracted.getTimelineChanges()).hasSize(1);
        assertThat(chapter.getWorkflowStage()).isEqualTo(ChapterWorkflowStage.MEMORY_PENDING_CONFIRMATION);

        MemoryChangeSet edited = service().update(
            STORY_ID,
            CHAPTER_ID,
            CHANGE_SET_ID,
            new MemoryChangeSetUpdateRequest(
                List.of(
                    Map.of("changeId", "timeline-edited-1", "memoryType", "timeline"),
                    Map.of("changeId", "timeline-edited-2", "memoryType", "timeline")
                ),
                List.of(Map.of("changeId", "character-edited", "memoryType", "character")),
                List.of(),
                List.of(Map.of("changeId", "foreshadow-edited", "memoryType", "foreshadow")),
                List.of(Map.of("message", "reviewed conflict")),
                Map.of("editorNote", "approved after manual trim")
            )
        );

        assertThat(edited.getStatus()).isEqualTo(MemoryChangeSetStatus.PENDING);
        assertThat(edited.getTimelineChanges()).hasSize(2);
        assertThat(edited.getWorldChanges()).isEmpty();
        assertThat(edited.getExtractionMetadata()).containsEntry("editorNote", "approved after manual trim");

        MemoryChangeSet confirmed = service().confirm(
            STORY_ID,
            CHAPTER_ID,
            CHANGE_SET_ID,
            new MemoryChangeSetConfirmRequest(USER_ID)
        );

        assertThat(confirmed.getStatus()).isEqualTo(MemoryChangeSetStatus.CONFIRMED);
        assertThat(confirmed.getConfirmedBy()).isEqualTo(USER_ID);
        assertThat(chapter.getWorkflowStage()).isEqualTo(ChapterWorkflowStage.MEMORY_CONFIRMED);

        MemoryChangeSetService.FreezeResult frozen = service().freeze(STORY_ID, CHAPTER_ID, CHANGE_SET_ID);

        assertThat(frozen.chapter()).isSameAs(chapter);
        assertThat(frozen.memoryChangeSet()).isSameAs(confirmed);
        assertThat(chapter.getStatus()).isEqualTo(ChapterStatus.APPROVED);
        assertThat(chapter.getWorkflowStage()).isEqualTo(ChapterWorkflowStage.CHAPTER_CONFIRMED);
        assertThat(chapter.getConfirmedAt()).isNotNull();
        assertThat(confirmed.getApplyResult()).containsEntry("status", "applied");
        assertThat(confirmed.getApplyResult()).extracting("counts")
            .isEqualTo(Map.of(
                "timeline", 2,
                "character", 1,
                "world", 0,
                "foreshadow", 1
            ));

        verify(aiMemoryClient).extractMemoryChanges(eq(STORY_ID), eq(CHAPTER_ID), any());
    }

    @Test
    void confirmPendingChangeSetMarksMemoryConfirmedOnChapter() {
        MemoryChangeSet pending = pendingChangeSet();
        Chapter chapter = confirmedDraftChapter();
        chapter.setWorkflowStage(ChapterWorkflowStage.MEMORY_PENDING_CONFIRMATION);
        when(changeSetRepository.findForUpdateByIdAndStoryIdAndChapterId(
            CHANGE_SET_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(pending));
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        when(changeSetRepository.save(any(MemoryChangeSet.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(chapterRepository.save(any(Chapter.class))).thenAnswer(invocation -> invocation.getArgument(0));

        MemoryChangeSet confirmed = service().confirm(
            STORY_ID,
            CHAPTER_ID,
            CHANGE_SET_ID,
            new MemoryChangeSetConfirmRequest(USER_ID)
        );

        assertThat(confirmed.getStatus()).isEqualTo(MemoryChangeSetStatus.CONFIRMED);
        assertThat(confirmed.getConfirmedBy()).isEqualTo(USER_ID);
        assertThat(confirmed.getConfirmedAt()).isNotNull();
        assertThat(chapter.getWorkflowStage()).isEqualTo(ChapterWorkflowStage.MEMORY_CONFIRMED);
    }

    @Test
    void freezeConfirmedChangeSetApprovesChapterAndRecordsApplyResult() {
        MemoryChangeSet confirmed = confirmedChangeSet();
        Chapter chapter = confirmedDraftChapter();
        chapter.setWorkflowStage(ChapterWorkflowStage.MEMORY_CONFIRMED);
        when(changeSetRepository.findForUpdateByIdAndStoryIdAndChapterId(
            CHANGE_SET_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(confirmed));
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        when(changeSetRepository.save(any(MemoryChangeSet.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(chapterRepository.save(any(Chapter.class))).thenAnswer(invocation -> invocation.getArgument(0));

        MemoryChangeSetService.FreezeResult result = service().freeze(STORY_ID, CHAPTER_ID, CHANGE_SET_ID);

        assertThat(result.chapter()).isSameAs(chapter);
        assertThat(result.memoryChangeSet()).isSameAs(confirmed);
        assertThat(chapter.getStatus()).isEqualTo(ChapterStatus.APPROVED);
        assertThat(chapter.getWorkflowStage()).isEqualTo(ChapterWorkflowStage.CHAPTER_CONFIRMED);
        assertThat(chapter.getConfirmedAt()).isNotNull();
        assertThat(confirmed.getApplyResult())
            .containsEntry("status", "applied")
            .containsEntry("chapterId", CHAPTER_ID.toString())
            .containsEntry("sourceGenerationId", GENERATION_ID.toString());
        assertThat(confirmed.getApplyResult()).containsKey("appliedAt");
        assertThat(confirmed.getApplyResult()).containsEntry(
            "note",
            "current version records confirmed memory changes for later long-term memory application"
        );
        assertThat(confirmed.getApplyResult()).extracting("counts")
            .isEqualTo(Map.of(
                "timeline", 1,
                "character", 1,
                "world", 1,
                "foreshadow", 1
            ));
    }

    @Test
    void pendingChangeSetCannotBeFrozen() {
        MemoryChangeSet pending = pendingChangeSet();
        when(changeSetRepository.findForUpdateByIdAndStoryIdAndChapterId(
            CHANGE_SET_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(pending));

        assertThatThrownBy(() -> service().freeze(STORY_ID, CHAPTER_ID, CHANGE_SET_ID))
            .isInstanceOf(ConflictException.class)
            .hasMessageContaining("Only confirmed memory change set can be frozen");

        verify(chapterRepository, never()).save(any(Chapter.class));
        verify(changeSetRepository, never()).save(any(MemoryChangeSet.class));
    }

    @Test
    void chapterMustBeMemoryConfirmedBeforeFreeze() {
        MemoryChangeSet confirmed = confirmedChangeSet();
        Chapter chapter = confirmedDraftChapter();
        chapter.setWorkflowStage(ChapterWorkflowStage.MEMORY_PENDING_CONFIRMATION);
        when(changeSetRepository.findForUpdateByIdAndStoryIdAndChapterId(
            CHANGE_SET_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(confirmed));
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));

        assertThatThrownBy(() -> service().freeze(STORY_ID, CHAPTER_ID, CHANGE_SET_ID))
            .isInstanceOf(ConflictException.class)
            .hasMessageContaining("Chapter memory must be confirmed before chapter freeze");

        verify(chapterRepository, never()).save(any(Chapter.class));
        verify(changeSetRepository, never()).save(any(MemoryChangeSet.class));
    }

    @Test
    void alreadyFrozenChapterWithSameConfirmedChangeSetIsIdempotent() {
        MemoryChangeSet confirmed = confirmedChangeSet();
        Map<String, Object> existingApplyResult = Map.of("status", "applied", "appliedAt", "2026-06-20T01:00:00Z");
        confirmed.setApplyResult(existingApplyResult);
        Chapter chapter = confirmedDraftChapter();
        chapter.setStatus(ChapterStatus.APPROVED);
        chapter.setWorkflowStage(ChapterWorkflowStage.CHAPTER_CONFIRMED);
        when(changeSetRepository.findForUpdateByIdAndStoryIdAndChapterId(
            CHANGE_SET_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(confirmed));
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));

        MemoryChangeSetService.FreezeResult result = service().freeze(STORY_ID, CHAPTER_ID, CHANGE_SET_ID);

        assertThat(result.chapter()).isSameAs(chapter);
        assertThat(result.memoryChangeSet()).isSameAs(confirmed);
        assertThat(confirmed.getApplyResult()).isSameAs(existingApplyResult);
        verify(chapterRepository, never()).save(any(Chapter.class));
        verify(changeSetRepository, never()).save(any(MemoryChangeSet.class));
    }

    @Test
    void nonPendingChangeSetCannotBeEditedOrConfirmedAgain() {
        MemoryChangeSet confirmed = pendingChangeSet();
        confirmed.setStatus(MemoryChangeSetStatus.CONFIRMED);
        when(changeSetRepository.findForUpdateByIdAndStoryIdAndChapterId(
            CHANGE_SET_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(confirmed));

        assertThatThrownBy(() -> service().update(
            STORY_ID,
            CHAPTER_ID,
            CHANGE_SET_ID,
            new MemoryChangeSetUpdateRequest(List.of(), List.of(), List.of(), List.of(), List.of(), Map.of())
        ))
            .isInstanceOf(ConflictException.class)
            .hasMessageContaining("Only pending memory change set can be edited");

        assertThatThrownBy(() -> service().confirm(
            STORY_ID,
            CHAPTER_ID,
            CHANGE_SET_ID,
            new MemoryChangeSetConfirmRequest(USER_ID)
        ))
            .isInstanceOf(ConflictException.class)
            .hasMessageContaining("Only pending memory change set can be confirmed");
    }

    @Test
    void extractRejectsMismatchedAiResponseBeforeSaving() {
        Chapter chapter = confirmedDraftChapter();
        ChapterGeneration generation = generation();
        when(chapterRepository.findByIdAndStoryId(CHAPTER_ID, STORY_ID)).thenReturn(Optional.of(chapter));
        when(changeSetRepository.findByStoryIdAndChapterIdAndSourceGenerationId(
            STORY_ID,
            CHAPTER_ID,
            GENERATION_ID
        )).thenReturn(Optional.empty());
        when(generationRepository.findByIdAndStoryIdAndChapterId(
            GENERATION_ID,
            STORY_ID,
            CHAPTER_ID
        )).thenReturn(Optional.of(generation));
        when(aiMemoryClient.extractMemoryChanges(any(), any(), any())).thenReturn(new AiMemoryExtractionResponse(
            STORY_ID.toString(),
            UUID.fromString("20000000-0000-0000-0000-000000000081").toString(),
            GENERATION_ID.toString(),
            1,
            "memory-extractor-v1",
            "extracted",
            "Wrong chapter.",
            List.of(),
            List.of()
        ));

        assertThatThrownBy(() -> service().extract(
            STORY_ID,
            CHAPTER_ID,
            new MemoryChangeSetExtractRequest(USER_ID, Map.of())
        ))
            .isInstanceOf(AiWorkerException.class)
            .hasMessageContaining("mismatched request fields: chapterId");

        verify(changeSetRepository, never()).save(any(MemoryChangeSet.class));
        verify(chapterRepository, never()).save(any(Chapter.class));
    }

    private MemoryChangeSetService service() {
        return new MemoryChangeSetService(
            changeSetRepository,
            new ChapterService(chapterRepository, null),
            generationRepository,
            aiMemoryClient
        );
    }

    private Chapter confirmedDraftChapter() {
        Chapter chapter = new Chapter();
        chapter.setId(CHAPTER_ID);
        chapter.setStoryId(STORY_ID);
        chapter.setChapterNumber(2);
        chapter.setContent(CONFIRMED_DRAFT);
        chapter.setLastGenerationId(GENERATION_ID);
        chapter.setWorkflowStage(ChapterWorkflowStage.DRAFT_CONFIRMED);
        return chapter;
    }

    private ChapterGeneration generation() {
        ChapterGeneration generation = new ChapterGeneration();
        generation.setId(GENERATION_ID);
        generation.setStoryId(STORY_ID);
        generation.setChapterId(CHAPTER_ID);
        generation.setStatus(GenerationStatus.SUCCEEDED);
        generation.setRequest(Map.of(
            "writing_context",
            Map.of(
                "story", Map.of("title", "Dream Fire"),
                "chapter", Map.of("chapterNumber", 2),
                "blueprint", Map.of("lockedFacts", List.of()),
                "confirmedOutline", Map.of("chapterGoal", "Awaken the mark"),
                "recentChapters", List.of()
            )
        ));
        generation.setExecutionHistory(List.of(Map.of("node", "writer")));
        generation.setReviewReport(Map.of("score", 8));
        generation.setConsistencyReport(Map.of("issues", List.of()));
        return generation;
    }

    private MemoryChangeSet pendingChangeSet() {
        MemoryChangeSet changeSet = new MemoryChangeSet();
        changeSet.setId(CHANGE_SET_ID);
        changeSet.setStoryId(STORY_ID);
        changeSet.setChapterId(CHAPTER_ID);
        changeSet.setSourceGenerationId(GENERATION_ID);
        changeSet.setStatus(MemoryChangeSetStatus.PENDING);
        changeSet.setSourceDraftHash(sha256(CONFIRMED_DRAFT));
        changeSet.setSchemaVersion(1);
        changeSet.setBaseMemoryFingerprint(Map.of("existingMemoryHash", sha256("{}")));
        changeSet.setExtractionMetadata(Map.of("summary", "existing"));
        return changeSet;
    }

    private MemoryChangeSet confirmedChangeSet() {
        MemoryChangeSet changeSet = pendingChangeSet();
        changeSet.setStatus(MemoryChangeSetStatus.CONFIRMED);
        changeSet.setTimelineChanges(List.of(Map.of("changeId", "timeline-1", "memoryType", "timeline")));
        changeSet.setCharacterChanges(List.of(Map.of("changeId", "character-1", "memoryType", "character")));
        changeSet.setWorldChanges(List.of(Map.of("changeId", "world-1", "memoryType", "world")));
        changeSet.setForeshadowChanges(List.of(Map.of("changeId", "foreshadow-1", "memoryType", "foreshadow")));
        return changeSet;
    }

    private AiMemoryExtractionResponse aiResponse() {
        return new AiMemoryExtractionResponse(
            STORY_ID.toString(),
            CHAPTER_ID.toString(),
            GENERATION_ID.toString(),
            1,
            "memory-extractor-v1",
            "extracted",
            "Four pending memory changes.",
            List.of(
                Map.of(
                    "changeId",
                    "timeline-1",
                    "memoryType",
                    "timeline",
                    "event",
                    "Dream fire marks Lin Jin",
                    "conflictHints",
                    List.of()
                ),
                Map.of("changeId", "character-1", "memoryType", "character", "conflictHints", List.of()),
                Map.of("changeId", "world-1", "memoryType", "world", "conflictHints", List.of()),
                Map.of(
                    "changeId",
                    "foreshadow-1",
                    "memoryType",
                    "foreshadow",
                    "conflictHints",
                    List.of(Map.of(
                        "target",
                        "mirror",
                        "message",
                        "Possible duplicate of existing foreshadow memory: mirror.",
                        "severity",
                        "warning"
                    ))
                )
            ),
            List.of(Map.of(
                "code",
                "conflict",
                "message",
                "Possible duplicate of existing foreshadow memory: mirror.",
                "changeIds",
                List.of("foreshadow-1")
            ))
        );
    }

    private String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(bytes);
        } catch (Exception ex) {
            throw new IllegalStateException(ex);
        }
    }
}
