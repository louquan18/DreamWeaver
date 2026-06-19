package com.dreamweaver.entity;

import java.time.OffsetDateTime;
import java.util.UUID;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;

@Entity
@Table(
    name = "chapters",
    uniqueConstraints = @UniqueConstraint(name = "uq_chapter_story_number", columnNames = {
        "story_id",
        "chapter_number"
    })
)
public class Chapter extends BaseEntity {

    @Column(name = "story_id", nullable = false)
    private UUID storyId;

    @Column(name = "chapter_number", nullable = false)
    private Integer chapterNumber;

    @Column(length = 200)
    private String title;

    @Column(columnDefinition = "text")
    private String content;

    @Column(name = "content_url", columnDefinition = "text")
    private String contentUrl;

    @Column(name = "word_count")
    private Integer wordCount;

    @Column(nullable = false, length = 20)
    private ChapterStatus status = ChapterStatus.DRAFT;

    @Column(name = "workflow_stage", nullable = false, length = 50)
    private ChapterWorkflowStage workflowStage = ChapterWorkflowStage.CHAPTER_CREATED;

    @Column(name = "confirmed_at")
    private OffsetDateTime confirmedAt;

    @Column(name = "last_generation_id")
    private UUID lastGenerationId;

    public UUID getStoryId() {
        return storyId;
    }

    public void setStoryId(UUID storyId) {
        this.storyId = storyId;
    }

    public Integer getChapterNumber() {
        return chapterNumber;
    }

    public void setChapterNumber(Integer chapterNumber) {
        this.chapterNumber = chapterNumber;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content;
    }

    public String getContentUrl() {
        return contentUrl;
    }

    public void setContentUrl(String contentUrl) {
        this.contentUrl = contentUrl;
    }

    public Integer getWordCount() {
        return wordCount;
    }

    public void setWordCount(Integer wordCount) {
        this.wordCount = wordCount;
    }

    public ChapterStatus getStatus() {
        return status;
    }

    public void setStatus(ChapterStatus status) {
        this.status = status;
    }

    public ChapterWorkflowStage getWorkflowStage() {
        return workflowStage;
    }

    public void setWorkflowStage(ChapterWorkflowStage workflowStage) {
        this.workflowStage = workflowStage;
    }

    public OffsetDateTime getConfirmedAt() {
        return confirmedAt;
    }

    public void setConfirmedAt(OffsetDateTime confirmedAt) {
        this.confirmedAt = confirmedAt;
    }

    public UUID getLastGenerationId() {
        return lastGenerationId;
    }

    public void setLastGenerationId(UUID lastGenerationId) {
        this.lastGenerationId = lastGenerationId;
    }
}
