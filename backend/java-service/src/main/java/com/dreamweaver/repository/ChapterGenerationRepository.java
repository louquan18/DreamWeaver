package com.dreamweaver.repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.dreamweaver.entity.ChapterGeneration;

public interface ChapterGenerationRepository extends JpaRepository<ChapterGeneration, UUID> {

    List<ChapterGeneration> findByStoryIdAndChapterIdOrderByCreatedAtDesc(
        UUID storyId,
        UUID chapterId
    );

    Optional<ChapterGeneration> findByIdAndStoryIdAndChapterId(
        UUID id,
        UUID storyId,
        UUID chapterId
    );
}
