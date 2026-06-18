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
@Table(name = "chapter_generations")
public class ChapterGeneration extends BaseEntity {

    @Column(name = "story_id", nullable = false)
    private UUID storyId;

    @Column(name = "chapter_id", nullable = false)
    private UUID chapterId;

    @Column(name = "user_id", nullable = false)
    private UUID userId;

    @Column(nullable = false, length = 20)
    private GenerationStatus status = GenerationStatus.QUEUED;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false, columnDefinition = "jsonb")
    private Map<String, Object> request = new HashMap<>();

    @Column(columnDefinition = "text")
    private String draft;

    @Column(name = "draft_url", columnDefinition = "text")
    private String draftUrl;

    @Column(name = "word_count")
    private Integer wordCount;

    @Column(name = "model_profile", length = 50)
    private String modelProfile;

    @Column(name = "model_name", length = 100)
    private String modelName;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "execution_history", nullable = false, columnDefinition = "jsonb")
    private List<Map<String, Object>> executionHistory = new ArrayList<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "consistency_report", columnDefinition = "jsonb")
    private Map<String, Object> consistencyReport;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "review_report", columnDefinition = "jsonb")
    private Map<String, Object> reviewReport;

    @Column(name = "checkpoint_id")
    private UUID checkpointId;

    @Column(name = "error_message", columnDefinition = "text")
    private String errorMessage;

    @Column(name = "started_at")
    private OffsetDateTime startedAt;

    @Column(name = "completed_at")
    private OffsetDateTime completedAt;

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

    public UUID getUserId() {
        return userId;
    }

    public void setUserId(UUID userId) {
        this.userId = userId;
    }

    public GenerationStatus getStatus() {
        return status;
    }

    public void setStatus(GenerationStatus status) {
        this.status = status;
    }

    public Map<String, Object> getRequest() {
        return request;
    }

    public void setRequest(Map<String, Object> request) {
        this.request = request;
    }

    public String getDraft() {
        return draft;
    }

    public void setDraft(String draft) {
        this.draft = draft;
    }

    public String getDraftUrl() {
        return draftUrl;
    }

    public void setDraftUrl(String draftUrl) {
        this.draftUrl = draftUrl;
    }

    public Integer getWordCount() {
        return wordCount;
    }

    public void setWordCount(Integer wordCount) {
        this.wordCount = wordCount;
    }

    public String getModelProfile() {
        return modelProfile;
    }

    public void setModelProfile(String modelProfile) {
        this.modelProfile = modelProfile;
    }

    public String getModelName() {
        return modelName;
    }

    public void setModelName(String modelName) {
        this.modelName = modelName;
    }

    public List<Map<String, Object>> getExecutionHistory() {
        return executionHistory;
    }

    public void setExecutionHistory(List<Map<String, Object>> executionHistory) {
        this.executionHistory = executionHistory;
    }

    public Map<String, Object> getConsistencyReport() {
        return consistencyReport;
    }

    public void setConsistencyReport(Map<String, Object> consistencyReport) {
        this.consistencyReport = consistencyReport;
    }

    public Map<String, Object> getReviewReport() {
        return reviewReport;
    }

    public void setReviewReport(Map<String, Object> reviewReport) {
        this.reviewReport = reviewReport;
    }

    public UUID getCheckpointId() {
        return checkpointId;
    }

    public void setCheckpointId(UUID checkpointId) {
        this.checkpointId = checkpointId;
    }

    public String getErrorMessage() {
        return errorMessage;
    }

    public void setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
    }

    public OffsetDateTime getStartedAt() {
        return startedAt;
    }

    public void setStartedAt(OffsetDateTime startedAt) {
        this.startedAt = startedAt;
    }

    public OffsetDateTime getCompletedAt() {
        return completedAt;
    }

    public void setCompletedAt(OffsetDateTime completedAt) {
        this.completedAt = completedAt;
    }
}
