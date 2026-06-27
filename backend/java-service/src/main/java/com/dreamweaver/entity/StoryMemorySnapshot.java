package com.dreamweaver.entity;

import java.util.ArrayList;
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
    name = "story_memory_snapshots",
    indexes = @Index(name = "idx_story_memory_snapshots_story", columnList = "story_id"),
    uniqueConstraints = @UniqueConstraint(
        name = "uq_story_memory_snapshots_story",
        columnNames = "story_id"
    )
)
public class StoryMemorySnapshot extends BaseEntity {

    @Column(name = "story_id", nullable = false)
    private UUID storyId;

    @Column(name = "schema_version", nullable = false)
    private Integer schemaVersion = 1;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false, columnDefinition = "jsonb")
    private List<Map<String, Object>> timeline = new ArrayList<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false, columnDefinition = "jsonb")
    private List<Map<String, Object>> characters = new ArrayList<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false, columnDefinition = "jsonb")
    private List<Map<String, Object>> world = new ArrayList<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false, columnDefinition = "jsonb")
    private List<Map<String, Object>> foreshadows = new ArrayList<>();

    @Column(name = "fingerprint_hash", nullable = false, length = 128)
    private String fingerprintHash = "";

    public UUID getStoryId() {
        return storyId;
    }

    public void setStoryId(UUID storyId) {
        this.storyId = storyId;
    }

    public Integer getSchemaVersion() {
        return schemaVersion;
    }

    public void setSchemaVersion(Integer schemaVersion) {
        this.schemaVersion = schemaVersion;
    }

    public List<Map<String, Object>> getTimeline() {
        return timeline;
    }

    public void setTimeline(List<Map<String, Object>> timeline) {
        this.timeline = timeline;
    }

    public List<Map<String, Object>> getCharacters() {
        return characters;
    }

    public void setCharacters(List<Map<String, Object>> characters) {
        this.characters = characters;
    }

    public List<Map<String, Object>> getWorld() {
        return world;
    }

    public void setWorld(List<Map<String, Object>> world) {
        this.world = world;
    }

    public List<Map<String, Object>> getForeshadows() {
        return foreshadows;
    }

    public void setForeshadows(List<Map<String, Object>> foreshadows) {
        this.foreshadows = foreshadows;
    }

    public String getFingerprintHash() {
        return fingerprintHash;
    }

    public void setFingerprintHash(String fingerprintHash) {
        this.fingerprintHash = fingerprintHash;
    }
}
