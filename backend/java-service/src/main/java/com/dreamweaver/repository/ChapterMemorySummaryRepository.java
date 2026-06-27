package com.dreamweaver.repository;

import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.dreamweaver.entity.ChapterMemorySummary;

public interface ChapterMemorySummaryRepository extends JpaRepository<ChapterMemorySummary, UUID> {

    Optional<ChapterMemorySummary> findByStoryIdAndChapterId(UUID storyId, UUID chapterId);

    List<ChapterMemorySummary> findByStoryIdAndChapterIdIn(UUID storyId, Collection<UUID> chapterIds);

    List<ChapterMemorySummary> findByStoryIdOrderByChapterNumberDesc(UUID storyId);
}
