package com.dreamweaver.repository;

import java.util.UUID;

import org.springframework.data.jpa.repository.JpaRepository;

import com.dreamweaver.entity.Story;

public interface StoryRepository extends JpaRepository<Story, UUID> {
}
