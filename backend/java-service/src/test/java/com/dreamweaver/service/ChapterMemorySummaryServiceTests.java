package com.dreamweaver.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

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
import com.dreamweaver.entity.ChapterMemorySummary;
import com.dreamweaver.entity.MemoryChangeSet;
import com.dreamweaver.repository.ChapterMemorySummaryRepository;

@ExtendWith(MockitoExtension.class)
class ChapterMemorySummaryServiceTests {

    private static final UUID STORY_ID = UUID.fromString("10000000-0000-0000-0000-000000000092");
    private static final UUID CHAPTER_1_ID = UUID.fromString("20000000-0000-0000-0000-000000000091");
    private static final UUID CHAPTER_2_ID = UUID.fromString("20000000-0000-0000-0000-000000000092");
    private static final UUID CHAPTER_3_ID = UUID.fromString("20000000-0000-0000-0000-000000000093");
    private static final UUID GENERATION_ID = UUID.fromString("30000000-0000-0000-0000-000000000092");

    @Mock
    private ChapterMemorySummaryRepository summaryRepository;

    @Test
    void saveFromChangeSetPersistsExtractionSummary() {
        MemoryChangeSet changeSet = changeSet("Lin Jin marked the mirror gate.");
        Chapter chapter = chapter(CHAPTER_2_ID, 2, "Mirror Gate", "chapter 2 text");
        when(summaryRepository.findByStoryIdAndChapterId(STORY_ID, CHAPTER_2_ID)).thenReturn(Optional.empty());
        when(summaryRepository.save(any(ChapterMemorySummary.class))).thenAnswer(invocation -> invocation.getArgument(0));
        ArgumentCaptor<ChapterMemorySummary> summaryCaptor = ArgumentCaptor.forClass(ChapterMemorySummary.class);

        Optional<ChapterMemorySummary> result = service().saveFromChangeSet(changeSet, chapter);

        assertThat(result).isPresent();
        verify(summaryRepository).save(summaryCaptor.capture());
        ChapterMemorySummary saved = summaryCaptor.getValue();
        assertThat(saved.getStoryId()).isEqualTo(STORY_ID);
        assertThat(saved.getChapterId()).isEqualTo(CHAPTER_2_ID);
        assertThat(saved.getChapterNumber()).isEqualTo(2);
        assertThat(saved.getSummary()).isEqualTo("Lin Jin marked the mirror gate.");
        assertThat(saved.getSourceDraftHash()).isEqualTo("draft-hash");
        assertThat(saved.getSourceGenerationId()).isEqualTo(GENERATION_ID);
        assertThat(saved.getExtractorVersion()).isEqualTo("memory-extractor-v1");
    }

    @Test
    void saveFromChangeSetSkipsMissingSummary() {
        MemoryChangeSet changeSet = changeSet(" ");

        Optional<ChapterMemorySummary> result = service().saveFromChangeSet(
            changeSet,
            chapter(CHAPTER_2_ID, 2, "Mirror Gate", "chapter 2 text")
        );

        assertThat(result).isEmpty();
        verify(summaryRepository, never()).save(any());
    }

    @Test
    void recentChapterContextsKeepsOnlyLatestFullTextAndOlderSummaries() {
        Chapter chapter1 = chapter(CHAPTER_1_ID, 1, "Ash Road", "chapter one full text");
        Chapter chapter2 = chapter(CHAPTER_2_ID, 2, "Mirror Gate", "chapter two full text");
        Chapter current = chapter(CHAPTER_3_ID, 3, "Next", null);
        when(summaryRepository.findByStoryIdAndChapterIdIn(STORY_ID, List.of(CHAPTER_2_ID, CHAPTER_1_ID)))
            .thenReturn(List.of(
                summary(CHAPTER_1_ID, 1, "Chapter one summary."),
                summary(CHAPTER_2_ID, 2, "Chapter two summary.")
            ));

        List<Map<String, Object>> contexts = service().recentChapterContexts(
            STORY_ID,
            current,
            List.of(chapter1, chapter2, current)
        );

        assertThat(contexts).hasSize(2);
        assertThat(contexts.get(0))
            .containsEntry("chapterNumber", 2)
            .containsEntry("contextRole", "recent_full_text")
            .containsEntry("content", "chapter two full text")
            .containsEntry("summary", "Chapter two summary.");
        assertThat(contexts.get(1))
            .containsEntry("chapterNumber", 1)
            .containsEntry("contextRole", "recent_summary")
            .containsEntry("summary", "Chapter one summary.");
        assertThat(contexts.get(1)).doesNotContainKey("content");
    }

    @Test
    void recentChapterContextsDoesNotInventMissingOlderSummary() {
        Chapter chapter1 = chapter(CHAPTER_1_ID, 1, "Ash Road", "chapter one full text");
        Chapter chapter2 = chapter(CHAPTER_2_ID, 2, "Mirror Gate", "chapter two full text");
        Chapter current = chapter(CHAPTER_3_ID, 3, "Next", null);
        when(summaryRepository.findByStoryIdAndChapterIdIn(STORY_ID, List.of(CHAPTER_2_ID, CHAPTER_1_ID)))
            .thenReturn(List.of(summary(CHAPTER_2_ID, 2, "Chapter two summary.")));

        List<Map<String, Object>> contexts = service().recentChapterContexts(
            STORY_ID,
            current,
            List.of(chapter1, chapter2, current)
        );

        assertThat(contexts).hasSize(1);
        assertThat(contexts.getFirst()).containsEntry("chapterNumber", 2);
    }

    private ChapterMemorySummaryService service() {
        return new ChapterMemorySummaryService(summaryRepository);
    }

    private MemoryChangeSet changeSet(String summary) {
        MemoryChangeSet changeSet = new MemoryChangeSet();
        changeSet.setStoryId(STORY_ID);
        changeSet.setChapterId(CHAPTER_2_ID);
        changeSet.setSourceGenerationId(GENERATION_ID);
        changeSet.setSourceDraftHash("draft-hash");
        changeSet.setExtractionMetadata(Map.of(
            "summary",
            summary,
            "extractorVersion",
            "memory-extractor-v1"
        ));
        return changeSet;
    }

    private Chapter chapter(UUID id, int number, String title, String content) {
        Chapter chapter = new Chapter();
        chapter.setId(id);
        chapter.setStoryId(STORY_ID);
        chapter.setChapterNumber(number);
        chapter.setTitle(title);
        chapter.setContent(content);
        chapter.setWordCount(content == null ? null : content.length());
        return chapter;
    }

    private ChapterMemorySummary summary(UUID chapterId, int number, String text) {
        ChapterMemorySummary summary = new ChapterMemorySummary();
        summary.setStoryId(STORY_ID);
        summary.setChapterId(chapterId);
        summary.setChapterNumber(number);
        summary.setSummary(text);
        summary.setSourceDraftHash("hash-" + number);
        return summary;
    }
}
