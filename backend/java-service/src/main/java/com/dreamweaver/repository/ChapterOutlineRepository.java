package com.dreamweaver.repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.dreamweaver.entity.ChapterOutline;
import com.dreamweaver.entity.ChapterOutlineStatus;

public interface ChapterOutlineRepository extends JpaRepository<ChapterOutline, UUID> {

    List<ChapterOutline> findByStoryIdAndChapterIdOrderByCreatedAtDesc(
        UUID storyId,
        UUID chapterId
    );

    List<ChapterOutline> findByStoryIdAndChapterIdAndStatusOrderByCreatedAtDesc(
        UUID storyId,
        UUID chapterId,
        ChapterOutlineStatus status
    );

    Optional<ChapterOutline> findFirstByStoryIdAndChapterIdAndStatusOrderByCreatedAtDesc(
        UUID storyId,
        UUID chapterId,
        ChapterOutlineStatus status
    );

    Optional<ChapterOutline> findByIdAndStoryIdAndChapterId(
        UUID id,
        UUID storyId,
        UUID chapterId
    );

    boolean existsByStoryIdAndChapterIdAndStatus(
        UUID storyId,
        UUID chapterId,
        ChapterOutlineStatus status
    );
}
