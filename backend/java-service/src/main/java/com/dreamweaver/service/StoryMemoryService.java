package com.dreamweaver.service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.MemoryChangeSet;
import com.dreamweaver.entity.StoryMemorySnapshot;
import com.dreamweaver.repository.StoryMemorySnapshotRepository;
import com.fasterxml.jackson.databind.MapperFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;

@Service
public class StoryMemoryService {

    public static final int TIMELINE_LIMIT = 20;
    public static final int CHARACTER_LIMIT = 12;
    public static final int WORLD_LIMIT = 20;
    public static final int FORESHADOW_LIMIT = 10;
    public static final int ADDITIONAL_MEMORY_LIMIT = 8;
    private static final Set<String> OPEN_FORESHADOW_STATUSES = Set.of(
        "planned",
        "planted",
        "reinforced",
        "strengthened",
        "triggered",
        "revealed"
    );
    private static final ObjectMapper FINGERPRINT_MAPPER = new ObjectMapper()
        .configure(MapperFeature.SORT_PROPERTIES_ALPHABETICALLY, true)
        .configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true);

    private final StoryMemorySnapshotRepository snapshotRepository;

    public StoryMemoryService(StoryMemorySnapshotRepository snapshotRepository) {
        this.snapshotRepository = snapshotRepository;
    }

    @Transactional(readOnly = true)
    public Map<String, Object> buildExistingMemory(UUID storyId) {
        Map<String, Object> memory = snapshotRepository.findByStoryId(storyId)
            .map(this::toMemoryMap)
            .orElseGet(() -> emptyMemory(storyId));
        memory.put("fingerprint", fingerprint(memory));
        return memory;
    }

    @Transactional(readOnly = true)
    public MemoryContext buildOutlineMemoryContext(UUID storyId) {
        StoryMemorySnapshot snapshot = snapshotRepository.findByStoryId(storyId)
            .orElseGet(() -> newSnapshot(storyId));
        return new MemoryContext(
            selectTimeline(snapshot.getTimeline()),
            limit(copyList(snapshot.getCharacters()), CHARACTER_LIMIT),
            limit(copyList(snapshot.getWorld()), WORLD_LIMIT),
            selectOpenForeshadows(snapshot.getForeshadows()),
            List.of()
        );
    }

    @Transactional
    public Map<String, Object> applyChangeSet(MemoryChangeSet changeSet, Chapter chapter) {
        StoryMemorySnapshot snapshot = snapshotRepository.findForUpdateByStoryId(changeSet.getStoryId())
            .orElseGet(() -> newSnapshot(changeSet.getStoryId()));

        ApplyCounts counts = new ApplyCounts();
        applyTimelineChanges(snapshot, changeSet, chapter, counts);
        applyCharacterChanges(snapshot, changeSet, chapter, counts);
        applyWorldChanges(snapshot, changeSet, chapter, counts);
        applyForeshadowChanges(snapshot, changeSet, chapter, counts);

        Map<String, Object> memory = toMemoryMap(snapshot);
        String hash = fingerprintHash(memory);
        snapshot.setFingerprintHash(hash);
        snapshotRepository.save(snapshot);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("status", "applied");
        result.put("appliedAt", OffsetDateTime.now().toString());
        result.put("chapterId", changeSet.getChapterId().toString());
        result.put("sourceGenerationId", changeSet.getSourceGenerationId().toString());
        result.put("counts", Map.of(
            "timeline", counts.timeline,
            "character", counts.character,
            "world", counts.world,
            "foreshadow", counts.foreshadow
        ));
        result.put("fingerprint", Map.of(
            "algorithm", "sha-256",
            "hash", hash
        ));
        return result;
    }

    public Map<String, Object> baseMemoryFingerprint(UUID storyId) {
        Map<String, Object> existingMemory = buildExistingMemory(storyId);
        Map<String, Object> fingerprint = fingerprint(existingMemory);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("algorithm", "sha-256");
        result.put("existingMemoryHash", fingerprint.get("hash"));
        result.put("existingMemory", existingMemory);
        return result;
    }

    private void applyTimelineChanges(
        StoryMemorySnapshot snapshot,
        MemoryChangeSet changeSet,
        Chapter chapter,
        ApplyCounts counts
    ) {
        List<Map<String, Object>> timeline = copyList(snapshot.getTimeline());
        for (Map<String, Object> change : nullToList(changeSet.getTimelineChanges())) {
            Map<String, Object> memory = copyMap(change);
            String id = stableId(memory, "timeline");
            memory.put("id", id);
            memory.put("memoryId", id);
            memory.putIfAbsent("chapterId", stringOrNull(changeSet.getChapterId()));
            memory.putIfAbsent("sourceGenerationId", stringOrNull(changeSet.getSourceGenerationId()));
            putIfPresent(memory, "chapterNumber", chapter == null ? null : chapter.getChapterNumber());
            normalizeEvidence(memory);
            upsertByIdentity(timeline, memory, id, List.of("id", "memoryId", "changeId"));
            counts.timeline++;
        }
        snapshot.setTimeline(timeline);
    }

    private void applyCharacterChanges(
        StoryMemorySnapshot snapshot,
        MemoryChangeSet changeSet,
        Chapter chapter,
        ApplyCounts counts
    ) {
        List<Map<String, Object>> characters = copyList(snapshot.getCharacters());
        for (Map<String, Object> change : nullToList(changeSet.getCharacterChanges())) {
            String name = characterName(change).orElseGet(() -> valueAsString(change.get("changeId"), "unknown"));
            String id = characterId(change, name);
            Map<String, Object> incoming = new LinkedHashMap<>();
            incoming.put("id", id);
            incoming.put("memoryId", id);
            incoming.put("name", name);
            incoming.put("sourceGenerationId", stringOrNull(changeSet.getSourceGenerationId()));
            putIfPresent(incoming, "lastAppearedChapter", chapter == null ? null : chapter.getChapterNumber());
            putIfPresent(incoming, "aliases", nestedList(change.get("character"), "aliases"));
            incoming.put("latestChange", copyMap(change));
            mergeCharacterState(incoming, change);
            mergeRelatedCharacters(incoming, change);
            normalizeEvidence(incoming);
            upsertCharacter(characters, incoming);
            counts.character++;
        }
        snapshot.setCharacters(characters);
    }

    private void applyWorldChanges(
        StoryMemorySnapshot snapshot,
        MemoryChangeSet changeSet,
        Chapter chapter,
        ApplyCounts counts
    ) {
        List<Map<String, Object>> world = copyList(snapshot.getWorld());
        for (Map<String, Object> change : nullToList(changeSet.getWorldChanges())) {
            Map<String, Object> memory = copyMap(change);
            String id = worldId(memory);
            memory.put("id", id);
            memory.put("memoryId", id);
            memory.putIfAbsent("sourceGenerationId", stringOrNull(changeSet.getSourceGenerationId()));
            putIfPresent(memory, "chapterNumber", chapter == null ? null : chapter.getChapterNumber());
            normalizeEvidence(memory);
            upsertByIdentity(world, memory, id, List.of("id", "memoryId", "changeId"));
            counts.world++;
        }
        snapshot.setWorld(world);
    }

    private void applyForeshadowChanges(
        StoryMemorySnapshot snapshot,
        MemoryChangeSet changeSet,
        Chapter chapter,
        ApplyCounts counts
    ) {
        List<Map<String, Object>> foreshadows = copyList(snapshot.getForeshadows());
        for (Map<String, Object> change : nullToList(changeSet.getForeshadowChanges())) {
            Map<String, Object> memory = copyMap(change);
            String id = firstText(memory, "foreshadowId", "memoryId", "id", "changeId")
                .orElseGet(() -> stableId(memory, "foreshadow"));
            memory.put("id", id);
            memory.put("memoryId", id);
            memory.put("foreshadowId", id);
            memory.put("status", foreshadowStatus(memory));
            memory.putIfAbsent("sourceGenerationId", stringOrNull(changeSet.getSourceGenerationId()));
            putIfPresent(memory, "chapterNumber", chapter == null ? null : chapter.getChapterNumber());
            normalizeEvidence(memory);
            upsertByIdentity(foreshadows, memory, id, List.of("id", "memoryId", "foreshadowId", "changeId"));
            counts.foreshadow++;
        }
        snapshot.setForeshadows(foreshadows);
    }

    private void upsertCharacter(List<Map<String, Object>> characters, Map<String, Object> incoming) {
        String id = valueAsString(incoming.get("id"), "");
        String name = valueAsString(incoming.get("name"), "");
        for (int i = 0; i < characters.size(); i++) {
            Map<String, Object> existing = characters.get(i);
            if (matches(existing, id, List.of("id", "memoryId")) || Objects.equals(valueAsString(existing.get("name"), ""), name)) {
                characters.set(i, mergeMemory(existing, incoming));
                return;
            }
        }
        characters.add(incoming);
    }

    private void upsertByIdentity(
        List<Map<String, Object>> memories,
        Map<String, Object> incoming,
        String id,
        List<String> identityKeys
    ) {
        for (int i = 0; i < memories.size(); i++) {
            Map<String, Object> existing = memories.get(i);
            if (matches(existing, id, identityKeys)) {
                memories.set(i, mergeMemory(existing, incoming));
                return;
            }
        }
        memories.add(incoming);
    }

    private boolean matches(Map<String, Object> memory, String id, List<String> keys) {
        return keys.stream().anyMatch(key -> Objects.equals(valueAsString(memory.get(key), null), id));
    }

    private Map<String, Object> mergeMemory(Map<String, Object> existing, Map<String, Object> incoming) {
        Map<String, Object> merged = copyMap(existing);
        for (Map.Entry<String, Object> entry : incoming.entrySet()) {
            Object value = entry.getValue();
            if (isBlankValue(value)) {
                continue;
            }
            Object current = merged.get(entry.getKey());
            if (current instanceof Map<?, ?> currentMap && value instanceof Map<?, ?> valueMap) {
                merged.put(entry.getKey(), mergeMemory(castMap(currentMap), castMap(valueMap)));
            } else if (current instanceof List<?> currentList && value instanceof List<?> valueList) {
                merged.put(entry.getKey(), mergeLists(currentList, valueList));
            } else {
                merged.put(entry.getKey(), value);
            }
        }
        return merged;
    }

    private List<Object> mergeLists(List<?> current, List<?> incoming) {
        List<Object> merged = new ArrayList<>();
        Set<String> seen = new LinkedHashSet<>();
        for (Object item : current) {
            addUnique(merged, seen, item);
        }
        for (Object item : incoming) {
            addUnique(merged, seen, item);
        }
        return merged;
    }

    private void addUnique(List<Object> result, Set<String> seen, Object item) {
        String key = String.valueOf(item);
        if (seen.add(key)) {
            result.add(item);
        }
    }

    private void mergeCharacterState(Map<String, Object> incoming, Map<String, Object> change) {
        Map<String, Object> currentState = new LinkedHashMap<>();
        Object after = change.get("after");
        String kind = valueAsString(change.get("changeKind"), "");
        if (!kind.isBlank() && !isBlankValue(after)) {
            currentState.put(kind, after);
        }
        putIfPresent(currentState, "impact", change.get("impact"));
        if (!currentState.isEmpty()) {
            incoming.put("currentState", currentState);
        }
    }

    private void mergeRelatedCharacters(Map<String, Object> incoming, Map<String, Object> change) {
        List<Map<String, Object>> related = listOfMaps(change.get("relatedCharacters"));
        if (!related.isEmpty()) {
            incoming.put("relatedCharacters", related);
        }
    }

    private Optional<String> characterName(Map<String, Object> change) {
        Object character = change.get("character");
        if (character instanceof Map<?, ?> characterMap) {
            String name = valueAsString(characterMap.get("name"), "");
            if (!name.isBlank()) {
                return Optional.of(name);
            }
        }
        return firstText(change, "name", "characterName");
    }

    private String characterId(Map<String, Object> change, String name) {
        Object character = change.get("character");
        if (character instanceof Map<?, ?> characterMap) {
            String memoryId = valueAsString(characterMap.get("memoryId"), "");
            if (!memoryId.isBlank()) {
                return memoryId;
            }
        }
        return "character:" + name;
    }

    private String worldId(Map<String, Object> change) {
        Optional<String> direct = firstText(change, "memoryId", "id", "changeId");
        if (direct.isPresent()) {
            return direct.get();
        }
        String type = valueAsString(change.get("subjectType"), "world");
        String subject = valueAsString(change.get("subject"), "unknown");
        return type + ":" + subject;
    }

    private String stableId(Map<String, Object> memory, String prefix) {
        return prefix + ":" + firstText(memory, "memoryId", "id", "changeId")
            .orElseGet(() -> sha256(String.valueOf(memory)).substring(0, 16));
    }

    private String foreshadowStatus(Map<String, Object> memory) {
        String operation = valueAsString(memory.get("operation"), "");
        if ("resolve".equals(operation)) {
            return "resolved";
        }
        if ("deprecate".equals(operation)) {
            return "abandoned";
        }
        String lifecycle = valueAsString(memory.get("lifecycle"), valueAsString(memory.get("status"), "planted"));
        if ("strengthened".equals(lifecycle)) {
            return "reinforced";
        }
        return lifecycle;
    }

    private List<Map<String, Object>> selectTimeline(List<Map<String, Object>> timeline) {
        List<Map<String, Object>> copy = copyList(timeline);
        if (copy.size() <= TIMELINE_LIMIT) {
            return copy;
        }
        List<Map<String, Object>> permanent = copy.stream()
            .filter(item -> Boolean.TRUE.equals(item.get("isPermanent")) || Boolean.TRUE.equals(item.get("is_permanent")))
            .toList();
        List<Map<String, Object>> high = copy.stream()
            .filter(item -> !permanent.contains(item))
            .filter(item -> "high".equals(valueAsString(item.get("importance"), "")))
            .toList();
        List<Map<String, Object>> selected = new ArrayList<>();
        selected.addAll(permanent);
        selected.addAll(high);
        for (int i = copy.size() - 1; i >= 0 && selected.size() < TIMELINE_LIMIT; i--) {
            Map<String, Object> item = copy.get(i);
            if (!selected.contains(item)) {
                selected.add(item);
            }
        }
        return selected.stream()
            .distinct()
            .limit(TIMELINE_LIMIT)
            .toList();
    }

    private List<Map<String, Object>> selectOpenForeshadows(List<Map<String, Object>> foreshadows) {
        return copyList(foreshadows).stream()
            .filter(item -> OPEN_FORESHADOW_STATUSES.contains(valueAsString(item.get("status"), "planted")))
            .sorted(Comparator
                .comparing((Map<String, Object> item) -> !Boolean.TRUE.equals(item.get("needsAttention")))
                .thenComparing(item -> !"overdue".equals(valueAsString(item.get("attentionStatus"), "")))
                .thenComparing(item -> importanceRank(valueAsString(item.get("importance"), "medium"))))
            .limit(FORESHADOW_LIMIT)
            .toList();
    }

    private int importanceRank(String importance) {
        return switch (importance) {
            case "high" -> 0;
            case "medium" -> 1;
            default -> 2;
        };
    }

    private void normalizeEvidence(Map<String, Object> memory) {
        if (!memory.containsKey("evidence")) {
            return;
        }
        Object evidence = memory.get("evidence");
        if (evidence instanceof Map<?, ?> evidenceMap) {
            memory.put("evidence", copyMap(castMap(evidenceMap)));
        }
    }

    private Map<String, Object> toMemoryMap(StoryMemorySnapshot snapshot) {
        Map<String, Object> memory = new LinkedHashMap<>();
        memory.put("timeline", copyList(snapshot.getTimeline()));
        memory.put("characters", copyList(snapshot.getCharacters()));
        memory.put("world", copyList(snapshot.getWorld()));
        memory.put("foreshadows", copyList(snapshot.getForeshadows()));
        return memory;
    }

    private Map<String, Object> emptyMemory(UUID storyId) {
        Map<String, Object> memory = new LinkedHashMap<>();
        memory.put("timeline", List.of());
        memory.put("characters", List.of());
        memory.put("world", List.of());
        memory.put("foreshadows", List.of());
        memory.put("storyId", storyId.toString());
        return memory;
    }

    private StoryMemorySnapshot newSnapshot(UUID storyId) {
        StoryMemorySnapshot snapshot = new StoryMemorySnapshot();
        snapshot.setStoryId(storyId);
        snapshot.setSchemaVersion(1);
        snapshot.setTimeline(new ArrayList<>());
        snapshot.setCharacters(new ArrayList<>());
        snapshot.setWorld(new ArrayList<>());
        snapshot.setForeshadows(new ArrayList<>());
        snapshot.setFingerprintHash("");
        return snapshot;
    }

    private Map<String, Object> fingerprint(Map<String, Object> memory) {
        return Map.of(
            "algorithm", "sha-256",
            "hash", fingerprintHash(memory)
        );
    }

    private String fingerprintHash(Map<String, Object> memory) {
        Map<String, Object> copy = copyMap(memory);
        copy.remove("fingerprint");
        return sha256(toStableJson(copy));
    }

    private String toStableJson(Object value) {
        try {
            return FINGERPRINT_MAPPER.writeValueAsString(value);
        } catch (Exception ex) {
            return String.valueOf(value);
        }
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

    private List<Map<String, Object>> copyList(List<Map<String, Object>> value) {
        return new ArrayList<>(nullToList(value).stream().map(this::copyMap).toList());
    }

    private List<Map<String, Object>> limit(List<Map<String, Object>> value, int limit) {
        return value.stream().limit(limit).toList();
    }

    private List<Map<String, Object>> nullToList(List<Map<String, Object>> value) {
        return value == null ? List.of() : value;
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> listOfMaps(Object value) {
        if (value instanceof List<?> list) {
            return list.stream()
                .filter(Map.class::isInstance)
                .map(item -> (Map<String, Object>) item)
                .map(this::copyMap)
                .toList();
        }
        return List.of();
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> copyMap(Map<String, Object> value) {
        return new LinkedHashMap<>(value == null ? Map.of() : value);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> castMap(Map<?, ?> value) {
        return (Map<String, Object>) value;
    }

    private List<Object> nestedList(Object value, String key) {
        if (value instanceof Map<?, ?> map && map.get(key) instanceof List<?> list) {
            return new ArrayList<>(list);
        }
        return List.of();
    }

    private Optional<String> firstText(Map<String, Object> value, String... keys) {
        for (String key : keys) {
            String text = valueAsString(value.get(key), "");
            if (!text.isBlank()) {
                return Optional.of(text);
            }
        }
        return Optional.empty();
    }

    private String valueAsString(Object value, String fallback) {
        if (value == null) {
            return fallback;
        }
        String text = value.toString().trim();
        return text.isEmpty() ? fallback : text;
    }

    private String stringOrNull(UUID value) {
        return value == null ? null : value.toString();
    }

    private void putIfPresent(Map<String, Object> target, String key, Object value) {
        if (!isBlankValue(value)) {
            target.put(key, value);
        }
    }

    private boolean isBlankValue(Object value) {
        return value == null || value instanceof String text && text.isBlank();
    }

    private static class ApplyCounts {
        private int timeline;
        private int character;
        private int world;
        private int foreshadow;
    }

    public record MemoryContext(
        List<Map<String, Object>> timeline,
        List<Map<String, Object>> characters,
        List<Map<String, Object>> world,
        List<Map<String, Object>> foreshadows,
        List<Map<String, Object>> additionalMemory
    ) {
    }
}
