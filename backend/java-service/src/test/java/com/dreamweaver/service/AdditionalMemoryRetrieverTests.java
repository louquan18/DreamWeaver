package com.dreamweaver.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import com.dreamweaver.entity.ChapterMemorySummary;
import com.dreamweaver.entity.StoryMemorySnapshot;
import com.dreamweaver.dto.AiAdditionalMemoryRetrieveRequest;
import com.dreamweaver.dto.AiAdditionalMemoryRetrieveResponse;
import com.dreamweaver.repository.ChapterMemorySummaryRepository;
import com.dreamweaver.repository.StoryMemorySnapshotRepository;

@ExtendWith(MockitoExtension.class)
class AdditionalMemoryRetrieverTests {

    private static final UUID STORY_ID = UUID.fromString("10000000-0000-0000-0000-000000000090");
    private static final UUID CHAPTER_ID = UUID.fromString("20000000-0000-0000-0000-000000000090");

    @Mock
    private StoryMemorySnapshotRepository snapshotRepository;

    @Mock
    private ChapterMemorySummaryRepository summaryRepository;

    @Mock
    private AiMemoryRetrievalClient aiMemoryRetrievalClient;

    @Test
    void additionalMemoryUsesVectorResultsWhenAvailable() {
        when(aiMemoryRetrievalClient.retrieve(eq(STORY_ID), any(AiAdditionalMemoryRetrieveRequest.class)))
            .thenReturn(new AiAdditionalMemoryRetrieveResponse(
                STORY_ID.toString(),
                "vector",
                List.of(Map.of(
                    "id",
                    "am-vector-1",
                    "type",
                    "paragraph",
                    "content",
                    "A remote paragraph says the mirror oath has a hidden cost.",
                    "source",
                    Map.of("chapterNumber", 2, "paragraphIndex", 1),
                    "score",
                    0.91,
                    "retrievalMethod",
                    "vector"
                ))
            ));
        when(snapshotRepository.findByStoryId(STORY_ID)).thenReturn(Optional.empty());
        when(summaryRepository.findByStoryIdOrderByChapterNumberDesc(STORY_ID)).thenReturn(List.of());

        List<Map<String, Object>> result = service().retrieve(
            STORY_ID,
            Map.of("title", "Dream Fire"),
            Map.of("chapterNumber", 4),
            Map.of(),
            Map.of("finalOutline", Map.of("chapterGoal", "Reveal the mirror oath cost")),
            Map.of()
        );

        assertThat(result).hasSize(1);
        assertThat(result.getFirst())
            .containsEntry("type", "paragraph")
            .containsEntry("retrievalMethod", "vector");
    }

    @Test
    void additionalMemoryRuleRetrievalReturnsRelevantForeshadow() {
        StoryMemorySnapshot snapshot = snapshot();
        snapshot.setForeshadows(List.of(Map.of(
            "memoryId",
            "fs-mirror-token",
            "status",
            "triggered",
            "content",
            "The mirror token burns when Lin Jin approaches the sealed gate.",
            "needsAttention",
            true
        )));
        when(snapshotRepository.findByStoryId(STORY_ID)).thenReturn(Optional.of(snapshot));
        when(summaryRepository.findByStoryIdOrderByChapterNumberDesc(STORY_ID)).thenReturn(List.of());

        List<Map<String, Object>> result = service().retrieve(
            STORY_ID,
            Map.of("title", "Dream Fire"),
            Map.of("chapterNumber", 4, "title", "Mirror Gate"),
            Map.of("premise", "Lin Jin follows the mirror token"),
            Map.of("finalOutline", Map.of("endingHook", "The mirror token burns again")),
            Map.of()
        );

        assertThat(result).hasSize(1);
        assertThat(result.getFirst())
            .containsEntry("type", "foreshadow")
            .containsEntry("retrievalMethod", "rule");
        assertThat(result.getFirst().get("content").toString()).contains("mirror token burns");
        assertThat(result.getFirst().get("source")).isEqualTo(Map.of("memoryId", "fs-mirror-token"));
    }

    @Test
    void additionalMemoryDeduplicatesMemoryIds() {
        StoryMemorySnapshot snapshot = snapshot();
        snapshot.setForeshadows(List.of(
            Map.of("memoryId", "fs-1", "status", "triggered", "content", "Mirror debt is due."),
            Map.of("memoryId", "fs-1", "status", "revealed", "content", "Mirror debt is due again.")
        ));
        when(snapshotRepository.findByStoryId(STORY_ID)).thenReturn(Optional.of(snapshot));
        when(summaryRepository.findByStoryIdOrderByChapterNumberDesc(STORY_ID)).thenReturn(List.of());

        List<Map<String, Object>> result = service().retrieve(
            STORY_ID,
            Map.of("title", "Dream Fire"),
            Map.of("chapterNumber", 4),
            Map.of(),
            Map.of("finalOutline", Map.of("chapterGoal", "Resolve the mirror debt")),
            Map.of()
        );

        assertThat(result).hasSize(1);
        assertThat(result.getFirst().get("source")).isEqualTo(Map.of("memoryId", "fs-1"));
    }

    @Test
    void additionalMemoryLimitsToConfiguredMax() {
        StoryMemorySnapshot snapshot = snapshot();
        List<Map<String, Object>> timeline = new ArrayList<>();
        for (int i = 0; i < 20; i++) {
            timeline.add(Map.of(
                "memoryId",
                "tl-" + i,
                "event",
                "Mirror gate event " + i,
                "importance",
                "high",
                "chapterNumber",
                i
            ));
        }
        snapshot.setTimeline(timeline);
        when(snapshotRepository.findByStoryId(STORY_ID)).thenReturn(Optional.of(snapshot));
        when(summaryRepository.findByStoryIdOrderByChapterNumberDesc(STORY_ID)).thenReturn(List.of());

        List<Map<String, Object>> result = service().retrieve(
            STORY_ID,
            Map.of("title", "Dream Fire"),
            Map.of("chapterNumber", 21),
            Map.of(),
            Map.of("finalOutline", Map.of("chapterGoal", "Return to the mirror gate")),
            Map.of()
        );

        assertThat(result).hasSize(StoryMemoryService.ADDITIONAL_MEMORY_LIMIT);
    }

    @Test
    void additionalMemoryFallsBackToChapterSummariesWithoutVectorStore() {
        when(aiMemoryRetrievalClient.retrieve(eq(STORY_ID), any(AiAdditionalMemoryRetrieveRequest.class)))
            .thenThrow(new AiWorkerException("ai_worker_error", "Chroma unavailable"));
        when(snapshotRepository.findByStoryId(STORY_ID)).thenReturn(Optional.empty());
        when(summaryRepository.findByStoryIdOrderByChapterNumberDesc(STORY_ID)).thenReturn(List.of(
            summary(2, "Old Mirror Oath", "Lin Jin promised not to use mirror fire in the market."),
            summary(1, "Outer Sect", "Lin Jin fled the outer sect.")
        ));

        List<Map<String, Object>> result = service().retrieve(
            STORY_ID,
            Map.of("title", "Dream Fire"),
            Map.of("chapterNumber", 4),
            Map.of(),
            Map.of("finalOutline", Map.of("chapterGoal", "Test the mirror fire oath")),
            Map.of()
        );

        assertThat(result).isNotEmpty();
        assertThat(result.getFirst())
            .containsEntry("type", "chapter_summary")
            .containsEntry("retrievalMethod", "rule");
        assertThat(result.getFirst().get("source").toString()).contains(CHAPTER_ID.toString());
    }

    private AdditionalMemoryRetriever service() {
        return new AdditionalMemoryRetriever(snapshotRepository, summaryRepository, aiMemoryRetrievalClient);
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

    private ChapterMemorySummary summary(int chapterNumber, String title, String text) {
        ChapterMemorySummary summary = new ChapterMemorySummary();
        summary.setStoryId(STORY_ID);
        summary.setChapterId(CHAPTER_ID);
        summary.setChapterNumber(chapterNumber);
        summary.setTitle(title);
        summary.setSummary(text);
        summary.setSourceDraftHash("hash-" + chapterNumber);
        summary.setExtractionMetadata(Map.of());
        return summary;
    }
}
