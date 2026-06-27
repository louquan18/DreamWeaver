package com.dreamweaver.repository;

import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import com.dreamweaver.entity.StoryMemorySnapshot;

import jakarta.persistence.LockModeType;

public interface StoryMemorySnapshotRepository extends JpaRepository<StoryMemorySnapshot, UUID> {

    Optional<StoryMemorySnapshot> findByStoryId(UUID storyId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("""
        select snapshot
        from StoryMemorySnapshot snapshot
        where snapshot.storyId = :storyId
        """)
    Optional<StoryMemorySnapshot> findForUpdateByStoryId(@Param("storyId") UUID storyId);
}
