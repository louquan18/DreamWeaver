package com.dreamweaver.repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.dreamweaver.entity.ChapterOutlineOption;
import com.dreamweaver.entity.OutlineOptionStatus;

public interface ChapterOutlineOptionRepository extends JpaRepository<ChapterOutlineOption, UUID> {

    List<ChapterOutlineOption> findByStoryIdAndChapterIdOrderByCreatedAtDesc(
        UUID storyId,
        UUID chapterId
    );

    List<ChapterOutlineOption> findByStoryIdAndChapterIdAndOptionGroupIdOrderByOptionCodeAsc(
        UUID storyId,
        UUID chapterId,
        UUID optionGroupId
    );

    List<ChapterOutlineOption> findByStoryIdAndChapterIdAndStatusOrderByCreatedAtDesc(
        UUID storyId,
        UUID chapterId,
        OutlineOptionStatus status
    );

    Optional<ChapterOutlineOption> findByIdAndStoryIdAndChapterId(
        UUID id,
        UUID storyId,
        UUID chapterId
    );
}
