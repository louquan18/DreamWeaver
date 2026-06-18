package com.dreamweaver.repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.dreamweaver.entity.Chapter;

public interface ChapterRepository extends JpaRepository<Chapter, UUID> {

    List<Chapter> findByStoryIdOrderByChapterNumberAsc(UUID storyId);

    Optional<Chapter> findByIdAndStoryId(UUID id, UUID storyId);

    boolean existsByStoryIdAndChapterNumber(UUID storyId, Integer chapterNumber);
}
