package com.dreamweaver.repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.dreamweaver.entity.NovelBlueprint;
import com.dreamweaver.entity.NovelBlueprintStatus;

public interface NovelBlueprintRepository extends JpaRepository<NovelBlueprint, UUID> {

    List<NovelBlueprint> findByStoryIdOrderByCreatedAtDesc(UUID storyId);

    Optional<NovelBlueprint> findByIdAndStoryId(UUID id, UUID storyId);

    Optional<NovelBlueprint> findFirstByStoryIdAndStatusOrderByCreatedAtDesc(
        UUID storyId,
        NovelBlueprintStatus status
    );

    boolean existsByStoryIdAndStatus(UUID storyId, NovelBlueprintStatus status);
}
