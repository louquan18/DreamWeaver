package com.dreamweaver.service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.function.Function;
import java.util.stream.Collectors;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.ChapterMemorySummary;
import com.dreamweaver.entity.MemoryChangeSet;
import com.dreamweaver.repository.ChapterMemorySummaryRepository;

@Service
public class ChapterMemorySummaryService {

    public static final int RECENT_FULL_TEXT_CHAPTERS = 1;
    public static final int RECENT_SUMMARY_CHAPTERS = 5;

    private final ChapterMemorySummaryRepository summaryRepository;

    public ChapterMemorySummaryService(ChapterMemorySummaryRepository summaryRepository) {
        this.summaryRepository = summaryRepository;
    }

    @Transactional
    public Optional<ChapterMemorySummary> saveFromChangeSet(MemoryChangeSet changeSet, Chapter chapter) {
        String summary = summaryText(changeSet);
        if (summary.isBlank()) {
            return Optional.empty();
        }

        ChapterMemorySummary record = summaryRepository
            .findByStoryIdAndChapterId(changeSet.getStoryId(), changeSet.getChapterId())
            .orElseGet(ChapterMemorySummary::new);
        record.setStoryId(changeSet.getStoryId());
        record.setChapterId(changeSet.getChapterId());
        record.setChapterNumber(chapter.getChapterNumber());
        record.setTitle(chapter.getTitle());
        record.setSummary(summary);
        record.setSourceDraftHash(changeSet.getSourceDraftHash());
        record.setSourceGenerationId(changeSet.getSourceGenerationId());
        record.setExtractorVersion(text(changeSet.getExtractionMetadata(), "extractorVersion"));
        record.setExtractionMetadata(copyMap(changeSet.getExtractionMetadata()));
        return Optional.of(summaryRepository.save(record));
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> recentChapterContexts(
        UUID storyId,
        Chapter currentChapter,
        List<Chapter> orderedChapters
    ) {
        List<Chapter> previous = orderedChapters.stream()
            .filter(chapter -> chapter.getChapterNumber() != null)
            .filter(chapter -> currentChapter.getChapterNumber() != null)
            .filter(chapter -> chapter.getChapterNumber() < currentChapter.getChapterNumber())
            .sorted(Comparator.comparing(Chapter::getChapterNumber).reversed())
            .limit(RECENT_SUMMARY_CHAPTERS)
            .toList();

        Map<UUID, ChapterMemorySummary> summaries = previous.isEmpty()
            ? Map.of()
            : summaryRepository
                .findByStoryIdAndChapterIdIn(storyId, previous.stream().map(Chapter::getId).toList())
                .stream()
                .collect(Collectors.toMap(ChapterMemorySummary::getChapterId, Function.identity()));

        List<Map<String, Object>> contexts = new ArrayList<>();
        for (int index = 0; index < previous.size(); index++) {
            Chapter chapter = previous.get(index);
            ChapterMemorySummary summary = summaries.get(chapter.getId());
            boolean includeContent = index < RECENT_FULL_TEXT_CHAPTERS
                && chapter.getContent() != null
                && !chapter.getContent().isBlank();
            Map<String, Object> item = recentChapterContext(chapter, summary, includeContent);
            if (includeContent || item.containsKey("summary")) {
                contexts.add(item);
            }
        }
        return contexts;
    }

    private Map<String, Object> recentChapterContext(
        Chapter chapter,
        ChapterMemorySummary summary,
        boolean includeContent
    ) {
        Map<String, Object> values = new LinkedHashMap<>();
        values.put("id", chapter.getId());
        values.put("chapterNumber", chapter.getChapterNumber());
        values.put("title", chapter.getTitle());
        values.put("wordCount", chapter.getWordCount());
        if (summary != null && summary.getSummary() != null && !summary.getSummary().isBlank()) {
            values.put("summary", summary.getSummary());
            values.put("summaryStatus", "available");
            values.put("summarySourceGenerationId", summary.getSourceGenerationId());
        } else {
            values.put("summaryStatus", "missing");
        }
        if (includeContent) {
            values.put("content", chapter.getContent());
            values.put("contextRole", "recent_full_text");
        } else {
            values.put("contextRole", "recent_summary");
        }
        return values;
    }

    private String summaryText(MemoryChangeSet changeSet) {
        return text(changeSet.getExtractionMetadata(), "summary");
    }

    private String text(Map<String, Object> value, String key) {
        if (value == null || value.get(key) == null) {
            return "";
        }
        return value.get(key).toString().trim();
    }

    private Map<String, Object> copyMap(Map<String, Object> value) {
        return new HashMap<>(value == null ? Map.of() : value);
    }
}
