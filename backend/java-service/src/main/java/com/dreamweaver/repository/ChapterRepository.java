package com.dreamweaver.repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.ChapterStatus;
import com.dreamweaver.entity.ChapterWorkflowStage;

public interface ChapterRepository extends JpaRepository<Chapter, UUID> {

    List<Chapter> findByStoryIdOrderByChapterNumberAsc(UUID storyId);

    Optional<Chapter> findByIdAndStoryId(UUID id, UUID storyId);

    Optional<Chapter> findByStoryIdAndChapterNumber(UUID storyId, Integer chapterNumber);

    Optional<Chapter> findTopByStoryIdOrderByChapterNumberDesc(UUID storyId);

    Optional<Chapter> findFirstByStoryIdAndChapterNumberLessThanOrderByChapterNumberDesc(
        UUID storyId,
        Integer chapterNumber
    );

    boolean existsByStoryIdAndChapterNumber(UUID storyId, Integer chapterNumber);

    boolean existsByStoryIdAndChapterNumberAndStatus(
        UUID storyId,
        Integer chapterNumber,
        ChapterStatus status
    );

    boolean existsByStoryIdAndChapterNumberAndWorkflowStage(
        UUID storyId,
        Integer chapterNumber,
        ChapterWorkflowStage workflowStage
    );
}
