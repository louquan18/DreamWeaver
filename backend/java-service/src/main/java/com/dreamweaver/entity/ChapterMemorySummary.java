package com.dreamweaver.entity;

import java.util.HashMap;
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
    name = "chapter_memory_summaries",
    indexes = {
        @Index(name = "idx_chapter_memory_summaries_story_number", columnList = "story_id, chapter_number"),
        @Index(name = "idx_chapter_memory_summaries_chapter", columnList = "chapter_id")
    },
    uniqueConstraints = @UniqueConstraint(
        name = "uq_chapter_memory_summaries_story_chapter",
        columnNames = {
            "story_id",
            "chapter_id"
        }
    )
)
public class ChapterMemorySummary extends BaseEntity {

    @Column(name = "story_id", nullable = false)
    private UUID storyId;

    @Column(name = "chapter_id", nullable = false)
    private UUID chapterId;

    @Column(name = "chapter_number", nullable = false)
    private Integer chapterNumber;

    @Column(length = 200)
    private String title;

    @Column(nullable = false, columnDefinition = "text")
    private String summary;

    @Column(name = "source_draft_hash", nullable = false, length = 128)
    private String sourceDraftHash;

    @Column(name = "source_generation_id")
    private UUID sourceGenerationId;

    @Column(name = "extractor_version", length = 100)
    private String extractorVersion;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "extraction_metadata", nullable = false, columnDefinition = "jsonb")
    private Map<String, Object> extractionMetadata = new HashMap<>();

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

    public String getSummary() {
        return summary;
    }

    public void setSummary(String summary) {
        this.summary = summary;
    }

    public String getSourceDraftHash() {
        return sourceDraftHash;
    }

    public void setSourceDraftHash(String sourceDraftHash) {
        this.sourceDraftHash = sourceDraftHash;
    }

    public UUID getSourceGenerationId() {
        return sourceGenerationId;
    }

    public void setSourceGenerationId(UUID sourceGenerationId) {
        this.sourceGenerationId = sourceGenerationId;
    }

    public String getExtractorVersion() {
        return extractorVersion;
    }

    public void setExtractorVersion(String extractorVersion) {
        this.extractorVersion = extractorVersion;
    }

    public Map<String, Object> getExtractionMetadata() {
        return extractionMetadata;
    }

    public void setExtractionMetadata(Map<String, Object> extractionMetadata) {
        this.extractionMetadata = extractionMetadata;
    }
}
