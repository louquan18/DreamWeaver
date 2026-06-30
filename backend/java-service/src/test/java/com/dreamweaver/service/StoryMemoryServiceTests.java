package com.dreamweaver.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.MemoryChangeSet;
import com.dreamweaver.entity.MemoryChangeSetStatus;
import com.dreamweaver.entity.StoryMemorySnapshot;
import com.dreamweaver.repository.MemoryChangeSetRepository;
import com.dreamweaver.repository.StoryMemorySnapshotRepository;

@ExtendWith(MockitoExtension.class)
class StoryMemoryServiceTests {

    private static final UUID STORY_ID = UUID.fromString("10000000-0000-0000-0000-000000000091");
    private static final UUID CHAPTER_ID = UUID.fromString("20000000-0000-0000-0000-000000000091");
    private static final UUID GENERATION_ID = UUID.fromString("30000000-0000-0000-0000-000000000091");

    @Mock
    private StoryMemorySnapshotRepository snapshotRepository;

    @Mock
    private MemoryChangeSetRepository changeSetRepository;

    @Test
    void applyChangeSetCreatesOfficialMemorySnapshot() {
        when(snapshotRepository.findForUpdateByStoryId(STORY_ID)).thenReturn(Optional.empty());
        when(snapshotRepository.save(any(StoryMemorySnapshot.class))).thenAnswer(invocation -> invocation.getArgument(0));
        ArgumentCaptor<StoryMemorySnapshot> snapshotCaptor = ArgumentCaptor.forClass(StoryMemorySnapshot.class);

        Map<String, Object> result = service().applyChangeSet(changeSet(), chapter());

        assertThat(result).containsEntry("status", "applied");
        assertThat(result).containsKey("fingerprint");
        org.mockito.Mockito.verify(snapshotRepository).save(snapshotCaptor.capture());
        StoryMemorySnapshot saved = snapshotCaptor.getValue();
        assertThat(saved.getStoryId()).isEqualTo(STORY_ID);
        assertThat(saved.getTimeline()).hasSize(1);
        assertThat(saved.getTimeline().getFirst())
            .containsEntry("event", "Lin Jin wakes the mirror fire")
            .containsEntry("chapterNumber", 2);
        assertThat(saved.getCharacters()).hasSize(1);
        assertThat(saved.getCharacters().getFirst()).containsEntry("name", "Lin Jin");
        assertThat(saved.getWorld()).hasSize(1);
        assertThat(saved.getForeshadows()).hasSize(1);
        assertThat(saved.getFingerprintHash()).isNotBlank();
    }

    @Test
    void applyCharacterChangeMergesWithoutClearingExistingState() {
        StoryMemorySnapshot snapshot = snapshot();
        snapshot.setCharacters(new ArrayList<>(List.of(Map.of(
            "id",
            "character:Lin Jin",
            "name",
            "Lin Jin",
            "currentState",
            Map.of("cultivationLevel", "Qi 3")
        ))));
        when(snapshotRepository.findForUpdateByStoryId(STORY_ID)).thenReturn(Optional.of(snapshot));
        when(snapshotRepository.save(any(StoryMemorySnapshot.class))).thenAnswer(invocation -> invocation.getArgument(0));

        service().applyChangeSet(characterOnlyChangeSet(), chapter());

        assertThat(snapshot.getCharacters()).hasSize(1);
        Map<String, Object> character = snapshot.getCharacters().getFirst();
        assertThat(character).containsEntry("name", "Lin Jin");
        assertThat(character.get("currentState")).isInstanceOf(Map.class);
        @SuppressWarnings("unchecked")
        Map<String, Object> currentState = (Map<String, Object>) character.get("currentState");
        assertThat(currentState).containsEntry("cultivationLevel", "Qi 3");
        assertThat(currentState).containsEntry("state", "guarding the mirror gate");
    }

    @Test
    void buildOutlineMemoryContextFiltersClosedForeshadows() {
        StoryMemorySnapshot snapshot = snapshot();
        snapshot.setTimeline(List.of(Map.of("id", "tl-1", "event", "permanent", "isPermanent", true)));
        snapshot.setCharacters(List.of(Map.of("name", "Lin Jin")));
        snapshot.setWorld(List.of(Map.of("subject", "Mirror fire")));
        snapshot.setForeshadows(List.of(
            Map.of("id", "fs-open", "status", "planted", "importance", "high"),
            Map.of("id", "fs-resolved", "status", "resolved", "importance", "high")
        ));
        when(snapshotRepository.findByStoryId(STORY_ID)).thenReturn(Optional.of(snapshot));

        StoryMemoryService.MemoryContext context = service().buildOutlineMemoryContext(STORY_ID);

        assertThat(context.timeline()).hasSize(1);
        assertThat(context.characters()).hasSize(1);
        assertThat(context.world()).hasSize(1);
        assertThat(context.foreshadows()).extracting(item -> item.get("id")).containsExactly("fs-open");
        assertThat(context.additionalMemory()).isEmpty();
    }

    @Test
    void buildExistingMemoryIncludesStableFingerprint() {
        StoryMemorySnapshot snapshot = snapshot();
        snapshot.setTimeline(List.of(Map.of("id", "tl-1", "event", "Lin Jin wakes the mirror fire")));
        when(snapshotRepository.findByStoryId(STORY_ID)).thenReturn(Optional.of(snapshot));

        Map<String, Object> memory = service().buildExistingMemory(STORY_ID);

        assertThat(memory).containsKey("timeline");
        assertThat(memory.get("fingerprint")).isInstanceOf(Map.class);
        @SuppressWarnings("unchecked")
        Map<String, Object> fingerprint = (Map<String, Object>) memory.get("fingerprint");
        assertThat(fingerprint).containsEntry("algorithm", "sha-256");
        assertThat(fingerprint.get("hash")).isInstanceOf(String.class);
    }

    @Test
    void libraryReturnsRequestedMemoryTypeWithFingerprint() {
        StoryMemorySnapshot snapshot = snapshot();
        snapshot.setCharacters(List.of(Map.of("id", "character:Lin Jin", "name", "Lin Jin")));
        when(snapshotRepository.findByStoryId(STORY_ID)).thenReturn(Optional.of(snapshot));

        StoryMemoryService.MemoryLibrary library = service().library(STORY_ID, "characters");

        assertThat(library.type()).isEqualTo("characters");
        assertThat(library.items()).hasSize(1);
        assertThat(library.items().getFirst()).containsEntry("name", "Lin Jin");
        assertThat(library.fingerprint()).containsEntry("algorithm", "sha-256");
    }

    @Test
    void libraryFallsBackToConfirmedChangeSetsWhenSnapshotIsMissing() {
        when(snapshotRepository.findByStoryId(STORY_ID)).thenReturn(Optional.empty());
        when(changeSetRepository.findByStoryIdAndStatusOrderByCreatedAtAsc(
            STORY_ID,
            MemoryChangeSetStatus.CONFIRMED
        )).thenReturn(List.of(changeSet()));

        StoryMemoryService.MemoryLibrary library = service().library(STORY_ID, "timeline");

        assertThat(library.type()).isEqualTo("timeline");
        assertThat(library.items()).hasSize(1);
        assertThat(library.items().getFirst())
            .containsEntry("event", "Lin Jin wakes the mirror fire")
            .containsEntry("storyId", STORY_ID.toString())
            .containsEntry("chapterId", CHAPTER_ID.toString())
            .containsEntry("sourceGenerationId", GENERATION_ID.toString());
        assertThat(library.fingerprint()).containsEntry("algorithm", "sha-256");
    }

    private StoryMemoryService service() {
        return new StoryMemoryService(snapshotRepository, changeSetRepository);
    }

    private StoryMemorySnapshot snapshot() {
        StoryMemorySnapshot snapshot = new StoryMemorySnapshot();
        snapshot.setStoryId(STORY_ID);
        snapshot.setTimeline(new ArrayList<>());
        snapshot.setCharacters(new ArrayList<>());
        snapshot.setWorld(new ArrayList<>());
        snapshot.setForeshadows(new ArrayList<>());
        return snapshot;
    }

    private Chapter chapter() {
        Chapter chapter = new Chapter();
        chapter.setId(CHAPTER_ID);
        chapter.setStoryId(STORY_ID);
        chapter.setChapterNumber(2);
        return chapter;
    }

    private MemoryChangeSet changeSet() {
        MemoryChangeSet changeSet = characterOnlyChangeSet();
        changeSet.setTimelineChanges(List.of(Map.of(
            "changeId",
            "tl-1",
            "memoryType",
            "timeline",
            "operation",
            "add",
            "event",
            "Lin Jin wakes the mirror fire",
            "importance",
            "high",
            "isPermanent",
            true
        )));
        changeSet.setWorldChanges(List.of(Map.of(
            "changeId",
            "world-1",
            "memoryType",
            "world",
            "operation",
            "add",
            "subjectType",
            "rule",
            "subject",
            "Mirror fire",
            "description",
            "Mirror fire burns memory first"
        )));
        changeSet.setForeshadowChanges(List.of(Map.of(
            "changeId",
            "fs-1",
            "memoryType",
            "foreshadow",
            "operation",
            "add",
            "lifecycle",
            "planted",
            "content",
            "The mirror gate still remembers a name"
        )));
        return changeSet;
    }

    private MemoryChangeSet characterOnlyChangeSet() {
        MemoryChangeSet changeSet = new MemoryChangeSet();
        changeSet.setStoryId(STORY_ID);
        changeSet.setChapterId(CHAPTER_ID);
        changeSet.setSourceGenerationId(GENERATION_ID);
        changeSet.setStatus(MemoryChangeSetStatus.CONFIRMED);
        changeSet.setCharacterChanges(List.of(Map.of(
            "changeId",
            "char-1",
            "memoryType",
            "character",
            "operation",
            "update",
            "character",
            Map.of("name", "Lin Jin"),
            "changeKind",
            "state",
            "after",
            "guarding the mirror gate",
            "impact",
            "He must stay near the gate"
        )));
        return changeSet;
    }
}
