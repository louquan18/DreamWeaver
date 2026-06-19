package com.dreamweaver.entity;

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
import jakarta.persistence.UniqueConstraint;

@Entity
@Table(
    name = "chapter_outline_options",
    uniqueConstraints = {
        @UniqueConstraint(name = "uq_chapter_outline_option_group_code", columnNames = {
            "chapter_id",
            "option_group_id",
            "option_code"
        }),
        @UniqueConstraint(name = "uq_chapter_outline_option_group_type", columnNames = {
            "chapter_id",
            "option_group_id",
            "option_type"
        })
    }
)
public class ChapterOutlineOption extends BaseEntity {

    @Column(name = "story_id", nullable = false)
    private UUID storyId;

    @Column(name = "chapter_id", nullable = false)
    private UUID chapterId;

    @Column(name = "option_group_id", nullable = false)
    private UUID optionGroupId;

    @Column(name = "option_code", nullable = false, length = 1)
    private OutlineOptionCode optionCode;

    @Column(name = "option_type", nullable = false, length = 30)
    private OutlineOptionType optionType;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "title_candidates", nullable = false, columnDefinition = "jsonb")
    private List<String> titleCandidates = new ArrayList<>();

    @Column(name = "chapter_goal", nullable = false, columnDefinition = "text")
    private String chapterGoal;

    @Column(name = "story_summary", nullable = false, columnDefinition = "text")
    private String storySummary;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "scene_outline", nullable = false, columnDefinition = "jsonb")
    private List<Map<String, Object>> sceneOutline = new ArrayList<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "characters_involved", nullable = false, columnDefinition = "jsonb")
    private List<Map<String, Object>> charactersInvolved = new ArrayList<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false, columnDefinition = "jsonb")
    private Map<String, Object> conflict = new HashMap<>();

    @Column(name = "highlight_moment", columnDefinition = "text")
    private String highlightMoment;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "foreshadow_actions", nullable = false, columnDefinition = "jsonb")
    private List<Map<String, Object>> foreshadowActions = new ArrayList<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "memory_references", nullable = false, columnDefinition = "jsonb")
    private List<Map<String, Object>> memoryReferences = new ArrayList<>();

    @Column(name = "why_this_plan", columnDefinition = "text")
    private String whyThisPlan;

    @Column(name = "ending_hook", columnDefinition = "text")
    private String endingHook;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "risk_notes", nullable = false, columnDefinition = "jsonb")
    private List<String> riskNotes = new ArrayList<>();

    @Column(nullable = false, length = 20)
    private OutlineOptionStatus status = OutlineOptionStatus.GENERATED;

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

    public UUID getOptionGroupId() {
        return optionGroupId;
    }

    public void setOptionGroupId(UUID optionGroupId) {
        this.optionGroupId = optionGroupId;
    }

    public OutlineOptionCode getOptionCode() {
        return optionCode;
    }

    public void setOptionCode(OutlineOptionCode optionCode) {
        this.optionCode = optionCode;
    }

    public OutlineOptionType getOptionType() {
        return optionType;
    }

    public void setOptionType(OutlineOptionType optionType) {
        this.optionType = optionType;
    }

    public List<String> getTitleCandidates() {
        return titleCandidates;
    }

    public void setTitleCandidates(List<String> titleCandidates) {
        this.titleCandidates = titleCandidates;
    }

    public String getChapterGoal() {
        return chapterGoal;
    }

    public void setChapterGoal(String chapterGoal) {
        this.chapterGoal = chapterGoal;
    }

    public String getStorySummary() {
        return storySummary;
    }

    public void setStorySummary(String storySummary) {
        this.storySummary = storySummary;
    }

    public List<Map<String, Object>> getSceneOutline() {
        return sceneOutline;
    }

    public void setSceneOutline(List<Map<String, Object>> sceneOutline) {
        this.sceneOutline = sceneOutline;
    }

    public List<Map<String, Object>> getCharactersInvolved() {
        return charactersInvolved;
    }

    public void setCharactersInvolved(List<Map<String, Object>> charactersInvolved) {
        this.charactersInvolved = charactersInvolved;
    }

    public Map<String, Object> getConflict() {
        return conflict;
    }

    public void setConflict(Map<String, Object> conflict) {
        this.conflict = conflict;
    }

    public String getHighlightMoment() {
        return highlightMoment;
    }

    public void setHighlightMoment(String highlightMoment) {
        this.highlightMoment = highlightMoment;
    }

    public List<Map<String, Object>> getForeshadowActions() {
        return foreshadowActions;
    }

    public void setForeshadowActions(List<Map<String, Object>> foreshadowActions) {
        this.foreshadowActions = foreshadowActions;
    }

    public List<Map<String, Object>> getMemoryReferences() {
        return memoryReferences;
    }

    public void setMemoryReferences(List<Map<String, Object>> memoryReferences) {
        this.memoryReferences = memoryReferences;
    }

    public String getWhyThisPlan() {
        return whyThisPlan;
    }

    public void setWhyThisPlan(String whyThisPlan) {
        this.whyThisPlan = whyThisPlan;
    }

    public String getEndingHook() {
        return endingHook;
    }

    public void setEndingHook(String endingHook) {
        this.endingHook = endingHook;
    }

    public List<String> getRiskNotes() {
        return riskNotes;
    }

    public void setRiskNotes(List<String> riskNotes) {
        this.riskNotes = riskNotes;
    }

    public OutlineOptionStatus getStatus() {
        return status;
    }

    public void setStatus(OutlineOptionStatus status) {
        this.status = status;
    }
}
