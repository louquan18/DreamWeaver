package com.dreamweaver.service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.dreamweaver.dto.AiMemoryExtractionRequest;
import com.dreamweaver.dto.AiMemoryExtractionResponse;
import com.dreamweaver.dto.MemoryChangeSetConfirmRequest;
import com.dreamweaver.dto.MemoryChangeSetExtractRequest;
import com.dreamweaver.dto.MemoryChangeSetUpdateRequest;
import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.ChapterGeneration;
import com.dreamweaver.entity.ChapterStatus;
import com.dreamweaver.entity.ChapterWorkflowStage;
import com.dreamweaver.entity.MemoryChangeSet;
import com.dreamweaver.entity.MemoryChangeSetStatus;
import com.dreamweaver.repository.ChapterGenerationRepository;
import com.dreamweaver.repository.MemoryChangeSetRepository;

@Service
public class MemoryChangeSetService {

    public record FreezeResult(Chapter chapter, MemoryChangeSet memoryChangeSet) {
    }

    private static final Set<ChapterWorkflowStage> EXTRACTION_ALLOWED_STAGES = EnumSet.of(
        ChapterWorkflowStage.DRAFT_CONFIRMED,
        ChapterWorkflowStage.MEMORY_EXTRACTING,
        ChapterWorkflowStage.MEMORY_PENDING_CONFIRMATION
    );

    private final MemoryChangeSetRepository changeSetRepository;
    private final ChapterService chapterService;
    private final ChapterGenerationRepository generationRepository;
    private final AiMemoryClient aiMemoryClient;

    public MemoryChangeSetService(
        MemoryChangeSetRepository changeSetRepository,
        ChapterService chapterService,
        ChapterGenerationRepository generationRepository,
        AiMemoryClient aiMemoryClient
    ) {
        this.changeSetRepository = changeSetRepository;
        this.chapterService = chapterService;
        this.generationRepository = generationRepository;
        this.aiMemoryClient = aiMemoryClient;
    }

    @Transactional
    public MemoryChangeSet extract(
        UUID storyId,
        UUID chapterId,
        MemoryChangeSetExtractRequest request
    ) {
        Chapter chapter = chapterService.get(storyId, chapterId);
        UUID sourceGenerationId = requireSourceGeneration(chapter);
        String confirmedDraft = requireConfirmedDraft(chapter);

        return changeSetRepository.findByStoryIdAndChapterIdAndSourceGenerationId(
            storyId,
            chapterId,
            sourceGenerationId
        ).orElseGet(() -> createPendingChangeSet(
            storyId,
            chapterId,
            request,
            chapter,
            sourceGenerationId,
            confirmedDraft
        ));
    }

    @Transactional(readOnly = true)
    public List<MemoryChangeSet> list(UUID storyId, UUID chapterId) {
        chapterService.get(storyId, chapterId);
        return changeSetRepository.findByStoryIdAndChapterIdOrderByCreatedAtDesc(storyId, chapterId);
    }

    @Transactional(readOnly = true)
    public MemoryChangeSet get(UUID storyId, UUID chapterId, UUID changeSetId) {
        return changeSetRepository.findByIdAndStoryIdAndChapterId(changeSetId, storyId, chapterId)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Memory change set not found: " + changeSetId
            ));
    }

    @Transactional
    public MemoryChangeSet update(
        UUID storyId,
        UUID chapterId,
        UUID changeSetId,
        MemoryChangeSetUpdateRequest request
    ) {
        MemoryChangeSet changeSet = getForUpdate(storyId, chapterId, changeSetId);
        assertPending(changeSet, "edited");

        if (request.timelineChanges() != null) {
            changeSet.setTimelineChanges(copyList(request.timelineChanges()));
        }
        if (request.characterChanges() != null) {
            changeSet.setCharacterChanges(copyList(request.characterChanges()));
        }
        if (request.worldChanges() != null) {
            changeSet.setWorldChanges(copyList(request.worldChanges()));
        }
        if (request.foreshadowChanges() != null) {
            changeSet.setForeshadowChanges(copyList(request.foreshadowChanges()));
        }
        if (request.conflicts() != null) {
            changeSet.setConflicts(copyList(request.conflicts()));
        }
        if (request.extractionMetadata() != null) {
            changeSet.setExtractionMetadata(copyMap(request.extractionMetadata()));
        }

        return changeSetRepository.save(changeSet);
    }

    @Transactional
    public MemoryChangeSet confirm(
        UUID storyId,
        UUID chapterId,
        UUID changeSetId,
        MemoryChangeSetConfirmRequest request
    ) {
        MemoryChangeSet changeSet = getForUpdate(storyId, chapterId, changeSetId);
        assertPending(changeSet, "confirmed");

        Chapter chapter = chapterService.get(storyId, chapterId);
        changeSet.setStatus(MemoryChangeSetStatus.CONFIRMED);
        changeSet.setConfirmedAt(OffsetDateTime.now());
        changeSet.setConfirmedBy(userId(request == null ? null : request.userId()));

        chapter.setWorkflowStage(ChapterWorkflowStage.MEMORY_CONFIRMED);
        chapterService.save(chapter);
        return changeSetRepository.save(changeSet);
    }

    @Transactional
    public FreezeResult freeze(UUID storyId, UUID chapterId, UUID changeSetId) {
        MemoryChangeSet changeSet = getForUpdate(storyId, chapterId, changeSetId);
        if (changeSet.getStatus() != MemoryChangeSetStatus.CONFIRMED) {
            throw new ConflictException(
                "memory_change_set_not_confirmed",
                "Only confirmed memory change set can be frozen"
            );
        }

        Chapter chapter = chapterService.get(storyId, chapterId);
        if (chapter.getWorkflowStage() == ChapterWorkflowStage.CHAPTER_CONFIRMED) {
            return new FreezeResult(chapter, changeSet);
        }
        if (chapter.getWorkflowStage() != ChapterWorkflowStage.MEMORY_CONFIRMED) {
            throw new ConflictException(
                "chapter_memory_not_confirmed",
                "Chapter memory must be confirmed before chapter freeze"
            );
        }

        OffsetDateTime now = OffsetDateTime.now();
        chapter.setStatus(ChapterStatus.APPROVED);
        chapter.setWorkflowStage(ChapterWorkflowStage.CHAPTER_CONFIRMED);
        if (chapter.getConfirmedAt() == null) {
            chapter.setConfirmedAt(now);
        }

        changeSet.setApplyResult(applyResult(changeSet, now));
        Chapter savedChapter = chapterService.save(chapter);
        MemoryChangeSet savedChangeSet = changeSetRepository.save(changeSet);
        return new FreezeResult(savedChapter, savedChangeSet);
    }

    private MemoryChangeSet createPendingChangeSet(
        UUID storyId,
        UUID chapterId,
        MemoryChangeSetExtractRequest request,
        Chapter chapter,
        UUID sourceGenerationId,
        String confirmedDraft
    ) {
        if (!EXTRACTION_ALLOWED_STAGES.contains(chapter.getWorkflowStage())) {
            throw new BadRequestException(
                "memory_extraction_stage_invalid",
                "Chapter draft must be confirmed before memory extraction: " + chapterId
            );
        }

        ChapterGeneration generation = generationRepository.findByIdAndStoryIdAndChapterId(
            sourceGenerationId,
            storyId,
            chapterId
        ).orElseThrow(() -> new ResourceNotFoundException(
            "Chapter generation not found: " + sourceGenerationId
        ));

        AiMemoryExtractionResponse response = aiMemoryClient.extractMemoryChanges(
            storyId,
            chapterId,
            pythonRequest(storyId, chapterId, sourceGenerationId, confirmedDraft, generation, request)
        );
        validateAiResponseIdentity(response, storyId, chapterId, sourceGenerationId);

        MemoryChangeSet changeSet = new MemoryChangeSet();
        changeSet.setStoryId(storyId);
        changeSet.setChapterId(chapterId);
        changeSet.setSourceGenerationId(sourceGenerationId);
        changeSet.setStatus(MemoryChangeSetStatus.PENDING);
        changeSet.setCreatedBy(userId(request == null ? null : request.userId()));
        changeSet.setSchemaVersion(response.schemaVersion() == null ? 1 : response.schemaVersion());
        applyGroupedChanges(changeSet, response.changes());
        changeSet.setConflicts(conflicts(response));
        changeSet.setSourceDraftHash(sha256(confirmedDraft));
        changeSet.setBaseMemoryFingerprint(baseMemoryFingerprint());
        changeSet.setExtractionMetadata(extractionMetadata(response, generation, request));

        MemoryChangeSet saved = changeSetRepository.save(changeSet);
        chapter.setWorkflowStage(ChapterWorkflowStage.MEMORY_PENDING_CONFIRMATION);
        chapterService.save(chapter);
        return saved;
    }

    private AiMemoryExtractionRequest pythonRequest(
        UUID storyId,
        UUID chapterId,
        UUID sourceGenerationId,
        String confirmedDraft,
        ChapterGeneration generation,
        MemoryChangeSetExtractRequest request
    ) {
        Map<String, Object> generationRequest = nullToEmpty(generation.getRequest());
        Map<String, Object> writingContext = mapValue(generationRequest.get("writing_context"));
        return new AiMemoryExtractionRequest(
            storyId,
            chapterId,
            sourceGenerationId,
            confirmedDraft,
            mapValue(writingContext.get("story")),
            mapValue(writingContext.get("chapter")),
            mapValue(writingContext.get("blueprint")),
            mapValue(writingContext.get("confirmedOutline")),
            listOfMaps(writingContext.get("recentChapters")),
            Map.of(),
            generationMetadata(generation, request),
            nullToEmpty(generation.getReviewReport()),
            nullToEmpty(generation.getConsistencyReport()),
            Map.of()
        );
    }

    private void validateAiResponseIdentity(
        AiMemoryExtractionResponse response,
        UUID storyId,
        UUID chapterId,
        UUID sourceGenerationId
    ) {
        List<String> mismatched = new ArrayList<>();
        if (!storyId.toString().equals(response.storyId())) {
            mismatched.add("storyId");
        }
        if (!chapterId.toString().equals(response.chapterId())) {
            mismatched.add("chapterId");
        }
        if (!sourceGenerationId.toString().equals(response.sourceGenerationId())) {
            mismatched.add("sourceGenerationId");
        }
        if (!mismatched.isEmpty()) {
            throw new AiWorkerException(
                "ai_worker_error",
                "AI memory extraction response mismatched request fields: " + String.join(", ", mismatched)
            );
        }
    }

    private void applyGroupedChanges(
        MemoryChangeSet changeSet,
        List<Map<String, Object>> changes
    ) {
        List<Map<String, Object>> timeline = new ArrayList<>();
        List<Map<String, Object>> character = new ArrayList<>();
        List<Map<String, Object>> world = new ArrayList<>();
        List<Map<String, Object>> foreshadow = new ArrayList<>();

        for (Map<String, Object> change : changes == null ? List.<Map<String, Object>>of() : changes) {
            Map<String, Object> copy = copyMap(change);
            String memoryType = String.valueOf(copy.get("memoryType"));
            if ("timeline".equals(memoryType)) {
                timeline.add(copy);
            } else if ("character".equals(memoryType)) {
                character.add(copy);
            } else if ("world".equals(memoryType)) {
                world.add(copy);
            } else if ("foreshadow".equals(memoryType)) {
                foreshadow.add(copy);
            }
        }

        changeSet.setTimelineChanges(timeline);
        changeSet.setCharacterChanges(character);
        changeSet.setWorldChanges(world);
        changeSet.setForeshadowChanges(foreshadow);
    }

    private List<Map<String, Object>> conflicts(AiMemoryExtractionResponse response) {
        List<Map<String, Object>> conflicts = new ArrayList<>();
        for (Map<String, Object> warning : response.warnings() == null
            ? List.<Map<String, Object>>of()
            : response.warnings()) {
            Map<String, Object> item = copyMap(warning);
            item.putIfAbsent("source", "warning");
            conflicts.add(item);
        }
        for (Map<String, Object> change : response.changes() == null
            ? List.<Map<String, Object>>of()
            : response.changes()) {
            String changeId = String.valueOf(change.get("changeId"));
            for (Map<String, Object> hint : listOfMaps(change.get("conflictHints"))) {
                Map<String, Object> item = copyMap(hint);
                item.put("changeId", changeId);
                item.putIfAbsent("source", "conflictHint");
                conflicts.add(item);
            }
            for (Object hint : listValue(change.get("blockingHints"))) {
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("changeId", changeId);
                item.put("source", "blockingHint");
                item.put("severity", "blocking");
                item.put("message", String.valueOf(hint));
                conflicts.add(item);
            }
        }
        return conflicts;
    }

    private Map<String, Object> applyResult(MemoryChangeSet changeSet, OffsetDateTime appliedAt) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("status", "applied");
        result.put("appliedAt", appliedAt.toString());
        result.put("chapterId", changeSet.getChapterId().toString());
        result.put("sourceGenerationId", changeSet.getSourceGenerationId().toString());
        result.put("counts", Map.of(
            "timeline", changeSet.getTimelineChanges().size(),
            "character", changeSet.getCharacterChanges().size(),
            "world", changeSet.getWorldChanges().size(),
            "foreshadow", changeSet.getForeshadowChanges().size()
        ));
        result.put(
            "note",
            "current version records confirmed memory changes for later long-term memory application"
        );
        return result;
    }

    private Map<String, Object> extractionMetadata(
        AiMemoryExtractionResponse response,
        ChapterGeneration generation,
        MemoryChangeSetExtractRequest request
    ) {
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("source", "python-ai");
        metadata.put("status", response.status());
        metadata.put("summary", response.summary());
        metadata.put("extractorVersion", response.extractorVersion());
        metadata.put("warnings", response.warnings() == null ? List.of() : response.warnings());
        metadata.put("sourceGenerationId", generation.getId().toString());
        metadata.put("generationStatus", generation.getStatus().value());
        metadata.put("options", request == null || request.options() == null ? Map.of() : request.options());
        return metadata;
    }

    private Map<String, Object> generationMetadata(
        ChapterGeneration generation,
        MemoryChangeSetExtractRequest request
    ) {
        Map<String, Object> metadata = new LinkedHashMap<>();
        metadata.put("generationId", generation.getId().toString());
        metadata.put("status", generation.getStatus().value());
        metadata.put("modelProfile", generation.getModelProfile());
        metadata.put("modelName", generation.getModelName());
        metadata.put("wordCount", generation.getWordCount());
        metadata.put("executionHistory", generation.getExecutionHistory());
        metadata.put("options", request == null || request.options() == null ? Map.of() : request.options());
        return metadata;
    }

    private Map<String, Object> baseMemoryFingerprint() {
        Map<String, Object> fingerprint = new LinkedHashMap<>();
        fingerprint.put("algorithm", "sha-256");
        fingerprint.put("existingMemoryHash", sha256("{}"));
        fingerprint.put("existingMemory", Map.of());
        return fingerprint;
    }

    private MemoryChangeSet getForUpdate(UUID storyId, UUID chapterId, UUID changeSetId) {
        return changeSetRepository.findForUpdateByIdAndStoryIdAndChapterId(
            changeSetId,
            storyId,
            chapterId
        ).orElseThrow(() -> new ResourceNotFoundException(
            "Memory change set not found: " + changeSetId
        ));
    }

    private UUID requireSourceGeneration(Chapter chapter) {
        if (chapter.getLastGenerationId() == null) {
            throw new BadRequestException(
                "source_generation_required",
                "Confirmed chapter must have lastGenerationId before memory extraction"
            );
        }
        return chapter.getLastGenerationId();
    }

    private String requireConfirmedDraft(Chapter chapter) {
        if (chapter.getContent() == null || chapter.getContent().isBlank()) {
            throw new BadRequestException(
                "confirmed_draft_required",
                "Confirmed chapter content is required before memory extraction"
            );
        }
        return chapter.getContent();
    }

    private void assertPending(MemoryChangeSet changeSet, String action) {
        if (changeSet.getStatus() != MemoryChangeSetStatus.PENDING) {
            throw new ConflictException(
                "memory_change_set_not_pending",
                "Only pending memory change set can be " + action
            );
        }
    }

    private UUID userId(UUID userId) {
        return userId == null ? StoryService.DEFAULT_USER_ID : userId;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> mapValue(Object value) {
        return value instanceof Map<?, ?> map ? (Map<String, Object>) map : Map.of();
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> listOfMaps(Object value) {
        if (value instanceof List<?> list) {
            return list.stream()
                .filter(Map.class::isInstance)
                .map(item -> (Map<String, Object>) item)
                .toList();
        }
        return List.of();
    }

    private List<Object> listValue(Object value) {
        return value instanceof List<?> list ? new ArrayList<>(list) : List.of();
    }

    private Map<String, Object> nullToEmpty(Map<String, Object> value) {
        return value == null ? Map.of() : value;
    }

    private List<Map<String, Object>> copyList(List<Map<String, Object>> value) {
        return value.stream().map(this::copyMap).toList();
    }

    private Map<String, Object> copyMap(Map<String, Object> value) {
        return new LinkedHashMap<>(value == null ? Map.of() : value);
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
