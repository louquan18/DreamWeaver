package com.dreamweaver.entity;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;

@Entity
@Table(
    name = "memory_change_sets",
    indexes = {
        @Index(name = "idx_memory_change_sets_story_chapter", columnList = "story_id, chapter_id"),
        @Index(name = "idx_memory_change_sets_generation", columnList = "source_generation_id"),
        @Index(name = "idx_memory_change_sets_status", columnList = "status")
    },
    uniqueConstraints = @UniqueConstraint(
        name = "uq_memory_change_sets_story_chapter_generation",
        columnNames = {
            "story_id",
            "chapter_id",
            "source_generation_id"
        }
    )
)
public class MemoryChangeSet extends BaseEntity {

    @Column(name = "story_id", nullable = false)
    private UUID storyId;

    @Column(name = "chapter_id", nullable = false)
    private UUID chapterId;

    @Column(name = "source_generation_id", nullable = false)
    private UUID sourceGenerationId;

    @Column(nullable = false, length = 32)
    private MemoryChangeSetStatus status = MemoryChangeSetStatus.PENDING;

    @Column(name = "schema_version", nullable = false)
    private Integer schemaVersion = 1;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "timeline_changes", nullable = false, columnDefinition = "jsonb")
    private List<Map<String, Object>> timelineChanges = new ArrayList<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "character_changes", nullable = false, columnDefinition = "jsonb")
    private List<Map<String, Object>> characterChanges = new ArrayList<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "world_changes", nullable = false, columnDefinition = "jsonb")
    private List<Map<String, Object>> worldChanges = new ArrayList<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "foreshadow_changes", nullable = false, columnDefinition = "jsonb")
    private List<Map<String, Object>> foreshadowChanges = new ArrayList<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false, columnDefinition = "jsonb")
    private List<Map<String, Object>> conflicts = new ArrayList<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "base_memory_fingerprint", nullable = false, columnDefinition = "jsonb")
    private Map<String, Object> baseMemoryFingerprint = new HashMap<>();

    @Column(name = "source_draft_hash", nullable = false, length = 128)
    private String sourceDraftHash;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "extraction_metadata", columnDefinition = "jsonb")
    private Map<String, Object> extractionMetadata;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "apply_result", columnDefinition = "jsonb")
    private Map<String, Object> applyResult;

    @Column(name = "created_by")
    private UUID createdBy;

    @Column(name = "confirmed_by")
    private UUID confirmedBy;

    @Column(name = "rejected_by")
    private UUID rejectedBy;

    @Column(name = "confirmed_at")
    private OffsetDateTime confirmedAt;

    @Column(name = "rejected_at")
    private OffsetDateTime rejectedAt;

    public UUID getStoryId() {
        return storyId;
    }

    public void setStoryId(UUID storyId) {
        this.storyId = storyId;
    }

    public UUID getChapterId() {
        return chapterId;
    }

    public void setChapterId(UUID chapterId) {
        this.chapterId = chapterId;
    }

    public UUID getSourceGenerationId() {
        return sourceGenerationId;
    }

    public void setSourceGenerationId(UUID sourceGenerationId) {
        this.sourceGenerationId = sourceGenerationId;
    }

    public MemoryChangeSetStatus getStatus() {
        return status;
    }

    public void setStatus(MemoryChangeSetStatus status) {
        this.status = status;
    }

    public Integer getSchemaVersion() {
        return schemaVersion;
    }

    public void setSchemaVersion(Integer schemaVersion) {
        this.schemaVersion = schemaVersion;
    }

    public List<Map<String, Object>> getTimelineChanges() {
        return timelineChanges;
    }

    public void setTimelineChanges(List<Map<String, Object>> timelineChanges) {
        this.timelineChanges = timelineChanges;
    }

    public List<Map<String, Object>> getCharacterChanges() {
        return characterChanges;
    }

    public void setCharacterChanges(List<Map<String, Object>> characterChanges) {
        this.characterChanges = characterChanges;
    }

    public List<Map<String, Object>> getWorldChanges() {
        return worldChanges;
    }

    public void setWorldChanges(List<Map<String, Object>> worldChanges) {
        this.worldChanges = worldChanges;
    }

    public List<Map<String, Object>> getForeshadowChanges() {
        return foreshadowChanges;
    }

    public void setForeshadowChanges(List<Map<String, Object>> foreshadowChanges) {
        this.foreshadowChanges = foreshadowChanges;
    }

    public List<Map<String, Object>> getConflicts() {
        return conflicts;
    }

    public void setConflicts(List<Map<String, Object>> conflicts) {
        this.conflicts = conflicts;
    }

    public Map<String, Object> getBaseMemoryFingerprint() {
        return baseMemoryFingerprint;
    }

    public void setBaseMemoryFingerprint(Map<String, Object> baseMemoryFingerprint) {
        this.baseMemoryFingerprint = baseMemoryFingerprint;
    }

    public String getSourceDraftHash() {
        return sourceDraftHash;
    }

    public void setSourceDraftHash(String sourceDraftHash) {
        this.sourceDraftHash = sourceDraftHash;
    }

    public Map<String, Object> getExtractionMetadata() {
        return extractionMetadata;
    }

    public void setExtractionMetadata(Map<String, Object> extractionMetadata) {
        this.extractionMetadata = extractionMetadata;
    }

    public Map<String, Object> getApplyResult() {
        return applyResult;
    }

    public void setApplyResult(Map<String, Object> applyResult) {
        this.applyResult = applyResult;
    }

    public UUID getCreatedBy() {
        return createdBy;
    }

    public void setCreatedBy(UUID createdBy) {
        this.createdBy = createdBy;
    }

    public UUID getConfirmedBy() {
        return confirmedBy;
    }

    public void setConfirmedBy(UUID confirmedBy) {
        this.confirmedBy = confirmedBy;
    }

    public UUID getRejectedBy() {
        return rejectedBy;
    }

    public void setRejectedBy(UUID rejectedBy) {
        this.rejectedBy = rejectedBy;
    }

    public OffsetDateTime getConfirmedAt() {
        return confirmedAt;
    }

    public void setConfirmedAt(OffsetDateTime confirmedAt) {
        this.confirmedAt = confirmedAt;
    }

    public OffsetDateTime getRejectedAt() {
        return rejectedAt;
    }

    public void setRejectedAt(OffsetDateTime rejectedAt) {
        this.rejectedAt = rejectedAt;
    }
}
