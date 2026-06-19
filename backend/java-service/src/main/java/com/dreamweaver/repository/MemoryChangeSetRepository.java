package com.dreamweaver.repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import com.dreamweaver.entity.MemoryChangeSet;
import com.dreamweaver.entity.MemoryChangeSetStatus;

import jakarta.persistence.LockModeType;

public interface MemoryChangeSetRepository extends JpaRepository<MemoryChangeSet, UUID> {

    List<MemoryChangeSet> findByStoryIdAndChapterIdOrderByCreatedAtDesc(
        UUID storyId,
        UUID chapterId
    );

    Optional<MemoryChangeSet> findByIdAndStoryIdAndChapterId(
        UUID id,
        UUID storyId,
        UUID chapterId
    );

    Optional<MemoryChangeSet> findByStoryIdAndChapterIdAndSourceGenerationId(
        UUID storyId,
        UUID chapterId,
        UUID sourceGenerationId
    );

    Optional<MemoryChangeSet> findFirstByStoryIdAndChapterIdAndStatusOrderByCreatedAtDesc(
        UUID storyId,
        UUID chapterId,
        MemoryChangeSetStatus status
    );

    List<MemoryChangeSet> findByStatusOrderByCreatedAtAsc(MemoryChangeSetStatus status);

    boolean existsByStoryIdAndChapterIdAndStatus(
        UUID storyId,
        UUID chapterId,
        MemoryChangeSetStatus status
    );

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
        select changeSet
        from MemoryChangeSet changeSet
        where changeSet.id = :id
            and changeSet.storyId = :storyId
            and changeSet.chapterId = :chapterId
        """)
    Optional<MemoryChangeSet> findForUpdateByIdAndStoryIdAndChapterId(
        @Param("id") UUID id,
        @Param("storyId") UUID storyId,
        @Param("chapterId") UUID chapterId
    );
}
