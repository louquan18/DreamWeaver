package com.dreamweaver.service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.dreamweaver.dto.AiAdditionalMemoryRetrieveRequest;
import com.dreamweaver.dto.AiAdditionalMemoryRetrieveResponse;
import com.dreamweaver.entity.ChapterMemorySummary;
import com.dreamweaver.entity.StoryMemorySnapshot;
import com.dreamweaver.repository.ChapterMemorySummaryRepository;
import com.dreamweaver.repository.StoryMemorySnapshotRepository;

@Service
public class AdditionalMemoryRetriever {

    private static final double RULE_BASE_SCORE = 0.45;

    private final StoryMemorySnapshotRepository snapshotRepository;
    private final ChapterMemorySummaryRepository summaryRepository;
    private final AiMemoryRetrievalClient aiMemoryRetrievalClient;

    public AdditionalMemoryRetriever(
        StoryMemorySnapshotRepository snapshotRepository,
        ChapterMemorySummaryRepository summaryRepository,
        AiMemoryRetrievalClient aiMemoryRetrievalClient
    ) {
        this.snapshotRepository = snapshotRepository;
        this.summaryRepository = summaryRepository;
        this.aiMemoryRetrievalClient = aiMemoryRetrievalClient;
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> retrieve(
        UUID storyId,
        Map<String, Object> story,
        Map<String, Object> chapter,
        Map<String, Object> blueprint,
        Map<String, Object> confirmedOutline,
        Map<String, Object> authorIntent
    ) {
        String query = queryText(story, chapter, blueprint, confirmedOutline, authorIntent);
        Integer currentChapterNumber = intValue(chapter.get("chapterNumber"));

        List<Candidate> candidates = new ArrayList<>();
        addVectorCandidates(candidates, storyId, query, currentChapterNumber);
        snapshotRepository.findByStoryId(storyId)
            .ifPresent(snapshot -> addSnapshotCandidates(candidates, snapshot, query));
        addSummaryCandidates(candidates, storyId, query, currentChapterNumber);

        return candidates.stream()
            .filter(candidate -> !candidate.content().isBlank())
            .sorted(Comparator
                .comparingDouble(Candidate::score).reversed()
                .thenComparingInt(candidate -> -intValue(candidate.payload().get("chapterNumber"), 0)))
            .collect(
                LinkedHashMap<String, Candidate>::new,
                (deduped, candidate) -> deduped.putIfAbsent(candidate.identity(), candidate),
                LinkedHashMap::putAll
            )
            .values()
            .stream()
            .limit(StoryMemoryService.ADDITIONAL_MEMORY_LIMIT)
            .map(Candidate::payload)
            .toList();
    }

    private void addVectorCandidates(
        List<Candidate> candidates,
        UUID storyId,
        String query,
        Integer currentChapterNumber
    ) {
        if (query.isBlank()) {
            return;
        }
        List<Integer> chapterRange = currentChapterNumber == null || currentChapterNumber <= 0
            ? null
            : List.of(0, currentChapterNumber - 1);
        try {
            AiAdditionalMemoryRetrieveResponse response = aiMemoryRetrievalClient.retrieve(
                storyId,
                new AiAdditionalMemoryRetrieveRequest(
                    query,
                    StoryMemoryService.ADDITIONAL_MEMORY_LIMIT,
                    chapterRange
                )
            );
            if (response == null || response.additionalMemory() == null) {
                return;
            }
            for (Map<String, Object> item : response.additionalMemory()) {
                Candidate candidate = vectorCandidate(item);
                if (candidate != null) {
                    candidates.add(candidate);
                }
            }
        } catch (RuntimeException ignored) {
            // Vector retrieval is optional; rule-based retrieval below is the guaranteed fallback.
        }
    }

    private void addSnapshotCandidates(List<Candidate> candidates, StoryMemorySnapshot snapshot, String query) {
        for (Map<String, Object> item : nullToList(snapshot.getForeshadows())) {
            String content = firstText(item, "content", "summary", "event", "description").orElse("");
            String status = text(item.get("status"));
            boolean needsAttention = Boolean.TRUE.equals(item.get("needsAttention"));
            double score = score(query, content + " " + status);
            if (needsAttention || Set.of("triggered", "revealed", "planned", "planted", "reinforced").contains(status) || score > 0) {
                candidates.add(candidate("foreshadow", content, item, "与当前章节目标或开放伏笔相关", score + (needsAttention ? 0.25 : 0.12)));
            }
        }

        for (Map<String, Object> item : nullToList(snapshot.getTimeline())) {
            String content = firstText(item, "event", "summary", "description").orElse("");
            boolean permanent = Boolean.TRUE.equals(item.get("isPermanent")) || Boolean.TRUE.equals(item.get("is_permanent"));
            boolean high = "high".equals(text(item.get("importance")));
            double score = score(query, content);
            if (permanent || high || score > 0) {
                candidates.add(candidate("timeline", content, item, "与当前章节目标相关的历史事件", score + (permanent ? 0.18 : high ? 0.12 : 0.0)));
            }
        }

        for (Map<String, Object> item : nullToList(snapshot.getCharacters())) {
            String name = firstText(item, "name", "characterName").orElse("");
            String content = firstText(item, "summary", "state", "after", "motivation", "impact")
                .map(value -> name.isBlank() ? value : name + ": " + value)
                .orElse(name);
            double score = score(query, content + " " + name);
            if (!name.isBlank() && query.toLowerCase(Locale.ROOT).contains(name.toLowerCase(Locale.ROOT)) || score > 0) {
                candidates.add(candidate("character", content, item, "与当前章节人物状态相关", score + 0.08));
            }
        }

        for (Map<String, Object> item : nullToList(snapshot.getWorld())) {
            String content = firstText(item, "description", "summary", "rule", "subject").orElse("");
            boolean locked = Boolean.TRUE.equals(item.get("locked"));
            double score = score(query, content + " " + firstText(item, "subject").orElse(""));
            if (locked || score > 0) {
                candidates.add(candidate("world", content, item, "与当前章节世界规则相关", score + (locked ? 0.1 : 0.0)));
            }
        }
    }

    private void addSummaryCandidates(
        List<Candidate> candidates,
        UUID storyId,
        String query,
        Integer currentChapterNumber
    ) {
        for (ChapterMemorySummary summary : summaryRepository.findByStoryIdOrderByChapterNumberDesc(storyId)) {
            if (currentChapterNumber != null && summary.getChapterNumber() >= currentChapterNumber) {
                continue;
            }
            String content = summary.getSummary();
            double score = score(query, summary.getTitle() + " " + content);
            if (score <= 0 && candidates.size() >= StoryMemoryService.ADDITIONAL_MEMORY_LIMIT) {
                continue;
            }
            Map<String, Object> source = new LinkedHashMap<>();
            source.put("chapterId", summary.getChapterId().toString());
            putIfPresent(source, "sourceGenerationId", stringOrNull(summary.getSourceGenerationId()));

            Map<String, Object> payload = basePayload(
                "chapter_summary",
                content,
                "与当前章节目标相近的历史章节摘要",
                Math.max(score, 0.05),
                source
            );
            payload.put("chapterNumber", summary.getChapterNumber());
            putIfPresent(payload, "title", summary.getTitle());
            candidates.add(new Candidate("chapter_summary:" + summary.getChapterId(), content, payload));
        }
    }

    private Candidate candidate(
        String type,
        String content,
        Map<String, Object> item,
        String reason,
        double score
    ) {
        Map<String, Object> source = new LinkedHashMap<>();
        String memoryId = firstText(item, "memoryId", "foreshadowId", "id", "changeId")
            .orElse(type + ":" + Integer.toHexString(item.hashCode()));
        source.put("memoryId", memoryId);
        putIfPresent(source, "chapterId", textOrNull(item.get("chapterId")));

        Map<String, Object> payload = basePayload(type, content, reason, Math.max(score, 0.01), source);
        int chapterNumber = intValue(item.get("chapterNumber"), -1);
        if (chapterNumber >= 0) {
            payload.put("chapterNumber", chapterNumber);
        }
        return new Candidate(type + ":" + memoryId, content, payload);
    }

    private Candidate vectorCandidate(Map<String, Object> item) {
        String content = text(item.get("content"));
        if (content.isBlank()) {
            return null;
        }
        Map<String, Object> payload = new LinkedHashMap<>(item);
        payload.putIfAbsent("retrievalMethod", "vector");
        payload.putIfAbsent("source", Map.of("retrievalMethod", "vector"));
        payload.putIfAbsent("score", 0.5);
        payload.putIfAbsent("id", "am-vector-" + Integer.toHexString(item.hashCode()));
        String type = text(payload.get("type"));
        if (type.isBlank()) {
            payload.put("type", "paragraph");
            type = "paragraph";
        }
        return new Candidate(type + ":" + sourceIdentity(payload), content, payload);
    }

    private String sourceIdentity(Map<String, Object> payload) {
        Object source = payload.get("source");
        if (source instanceof Map<?, ?> sourceMap) {
            String memoryId = text(sourceMap.get("memoryId"));
            if (!memoryId.isBlank()) {
                return memoryId;
            }
            String chapterId = text(sourceMap.get("chapterId"));
            String paragraphIndex = text(sourceMap.get("paragraphIndex"));
            if (!chapterId.isBlank() || !paragraphIndex.isBlank()) {
                return chapterId + ":" + paragraphIndex;
            }
            String chapterNumber = text(sourceMap.get("chapterNumber"));
            if (!chapterNumber.isBlank()) {
                return chapterNumber;
            }
        }
        return text(payload.get("id"));
    }

    private Map<String, Object> basePayload(
        String type,
        String content,
        String reason,
        double score,
        Map<String, Object> source
    ) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("id", "am-" + Integer.toHexString((type + content + source).hashCode()));
        payload.put("type", type);
        payload.put("content", content);
        payload.put("reason", reason);
        payload.put("source", source);
        payload.put("score", Math.min(0.99, RULE_BASE_SCORE + score));
        payload.put("retrievalMethod", "rule");
        return payload;
    }

    private String queryText(Object... values) {
        StringBuilder builder = new StringBuilder();
        for (Object value : values) {
            appendText(builder, value);
        }
        return builder.toString();
    }

    private void appendText(StringBuilder builder, Object value) {
        if (value == null) {
            return;
        }
        if (value instanceof Map<?, ?> map) {
            map.values().forEach(item -> appendText(builder, item));
            return;
        }
        if (value instanceof Iterable<?> iterable) {
            iterable.forEach(item -> appendText(builder, item));
            return;
        }
        builder.append(' ').append(value);
    }

    private double score(String query, String content) {
        Set<String> queryTokens = tokens(query);
        if (queryTokens.isEmpty() || content == null || content.isBlank()) {
            return 0.0;
        }
        String normalizedContent = content.toLowerCase(Locale.ROOT);
        long matches = queryTokens.stream().filter(normalizedContent::contains).count();
        return matches == 0 ? 0.0 : Math.min(0.45, matches / 20.0);
    }

    private Set<String> tokens(String value) {
        Set<String> tokens = new LinkedHashSet<>();
        for (String token : text(value).toLowerCase(Locale.ROOT).split("[^\\p{L}\\p{N}]+")) {
            if (token.length() >= 2) {
                tokens.add(token);
            }
        }
        return tokens;
    }

    private Optional<String> firstText(Map<String, Object> value, String... keys) {
        for (String key : keys) {
            String text = text(value.get(key));
            if (!text.isBlank()) {
                return Optional.of(text);
            }
        }
        return Optional.empty();
    }

    private List<Map<String, Object>> nullToList(List<Map<String, Object>> value) {
        return value == null ? List.of() : value;
    }

    private int intValue(Object value) {
        return intValue(value, 0);
    }

    private int intValue(Object value, int fallback) {
        if (value instanceof Number number) {
            return number.intValue();
        }
        try {
            return Integer.parseInt(text(value));
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private String text(Object value) {
        return value == null ? "" : value.toString().trim();
    }

    private String textOrNull(Object value) {
        String text = text(value);
        return text.isBlank() ? null : text;
    }

    private String stringOrNull(UUID value) {
        return value == null ? null : value.toString();
    }

    private void putIfPresent(Map<String, Object> target, String key, Object value) {
        if (value != null && !value.toString().isBlank()) {
            target.put(key, value);
        }
    }

    private record Candidate(
        String identity,
        String content,
        Map<String, Object> payload
    ) {
        double score() {
            Object score = payload.get("score");
            return score instanceof Number number ? number.doubleValue() : 0.0;
        }
    }
}
