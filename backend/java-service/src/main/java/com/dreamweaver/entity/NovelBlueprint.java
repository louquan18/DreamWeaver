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
import jakarta.persistence.Table;

@Entity
@Table(name = "novel_blueprints")
public class NovelBlueprint extends BaseEntity {

    @Column(name = "story_id", nullable = false)
    private UUID storyId;

    @Column(name = "source_prompt", columnDefinition = "text")
    private String sourcePrompt;

    @Column(nullable = false, columnDefinition = "text")
    private String premise;

    @Column(length = 50)
    private String genre;

    @Column(length = 100)
    private String tone;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false, columnDefinition = "jsonb")
    private Map<String, Object> protagonist = new HashMap<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "main_thread", nullable = false, columnDefinition = "jsonb")
    private Map<String, Object> mainThread = new HashMap<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "core_conflict", nullable = false, columnDefinition = "jsonb")
    private Map<String, Object> coreConflict = new HashMap<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "world_seed", nullable = false, columnDefinition = "jsonb")
    private Map<String, Object> worldSeed = new HashMap<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "writing_preferences", nullable = false, columnDefinition = "jsonb")
    private Map<String, Object> writingPreferences = new HashMap<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "locked_facts", nullable = false, columnDefinition = "jsonb")
    private List<Map<String, Object>> lockedFacts = new ArrayList<>();

    @Column(nullable = false, length = 20)
    private NovelBlueprintStatus status = NovelBlueprintStatus.GENERATED;

    @Column(name = "confirmed_at")
    private OffsetDateTime confirmedAt;

    @Column(name = "superseded_at")
    private OffsetDateTime supersededAt;

    public UUID getStoryId() {
        return storyId;
    }

    public void setStoryId(UUID storyId) {
        this.storyId = storyId;
    }

    public String getSourcePrompt() {
        return sourcePrompt;
    }

    public void setSourcePrompt(String sourcePrompt) {
        this.sourcePrompt = sourcePrompt;
    }

    public String getPremise() {
        return premise;
    }

    public void setPremise(String premise) {
        this.premise = premise;
    }

    public String getGenre() {
        return genre;
    }

    public void setGenre(String genre) {
        this.genre = genre;
    }

    public String getTone() {
        return tone;
    }

    public void setTone(String tone) {
        this.tone = tone;
    }

    public Map<String, Object> getProtagonist() {
        return protagonist;
    }

    public void setProtagonist(Map<String, Object> protagonist) {
        this.protagonist = protagonist;
    }

    public Map<String, Object> getMainThread() {
        return mainThread;
    }

    public void setMainThread(Map<String, Object> mainThread) {
        this.mainThread = mainThread;
    }

    public Map<String, Object> getCoreConflict() {
        return coreConflict;
    }

    public void setCoreConflict(Map<String, Object> coreConflict) {
        this.coreConflict = coreConflict;
    }

    public Map<String, Object> getWorldSeed() {
        return worldSeed;
    }

    public void setWorldSeed(Map<String, Object> worldSeed) {
        this.worldSeed = worldSeed;
    }

    public Map<String, Object> getWritingPreferences() {
        return writingPreferences;
    }

    public void setWritingPreferences(Map<String, Object> writingPreferences) {
        this.writingPreferences = writingPreferences;
    }

    public List<Map<String, Object>> getLockedFacts() {
        return lockedFacts;
    }

    public void setLockedFacts(List<Map<String, Object>> lockedFacts) {
        this.lockedFacts = lockedFacts;
    }

    public NovelBlueprintStatus getStatus() {
        return status;
    }

    public void setStatus(NovelBlueprintStatus status) {
        this.status = status;
    }

    public OffsetDateTime getConfirmedAt() {
        return confirmedAt;
    }

    public void setConfirmedAt(OffsetDateTime confirmedAt) {
        this.confirmedAt = confirmedAt;
    }

    public OffsetDateTime getSupersededAt() {
        return supersededAt;
    }

    public void setSupersededAt(OffsetDateTime supersededAt) {
        this.supersededAt = supersededAt;
    }
}
