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
@Table(name = "chapter_outlines")
public class ChapterOutline extends BaseEntity {

    @Column(name = "story_id", nullable = false)
    private UUID storyId;

    @Column(name = "chapter_id", nullable = false)
    private UUID chapterId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "source_option_ids", nullable = false, columnDefinition = "jsonb")
    private List<UUID> sourceOptionIds = new ArrayList<>();

    @Column(name = "user_feedback", columnDefinition = "text")
    private String userFeedback;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "final_outline", nullable = false, columnDefinition = "jsonb")
    private Map<String, Object> finalOutline = new HashMap<>();

    @Column(nullable = false, length = 20)
    private ChapterOutlineStatus status = ChapterOutlineStatus.DRAFT;

    @Column(name = "confirmed_at")
    private OffsetDateTime confirmedAt;

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

    public List<UUID> getSourceOptionIds() {
        return sourceOptionIds;
    }

    public void setSourceOptionIds(List<UUID> sourceOptionIds) {
        this.sourceOptionIds = sourceOptionIds;
    }

    public String getUserFeedback() {
        return userFeedback;
    }

    public void setUserFeedback(String userFeedback) {
        this.userFeedback = userFeedback;
    }

    public Map<String, Object> getFinalOutline() {
        return finalOutline;
    }

    public void setFinalOutline(Map<String, Object> finalOutline) {
        this.finalOutline = finalOutline;
    }

    public ChapterOutlineStatus getStatus() {
        return status;
    }

    public void setStatus(ChapterOutlineStatus status) {
        this.status = status;
    }

    public OffsetDateTime getConfirmedAt() {
        return confirmedAt;
    }

    public void setConfirmedAt(OffsetDateTime confirmedAt) {
        this.confirmedAt = confirmedAt;
    }
}
