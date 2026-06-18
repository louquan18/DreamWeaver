package com.dreamweaver.service;

import java.util.List;
import java.util.UUID;

import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.dreamweaver.dto.StoryCreateRequest;
import com.dreamweaver.entity.Story;
import com.dreamweaver.entity.StoryStatus;
import com.dreamweaver.repository.StoryRepository;

@Service
public class StoryService {

    public static final UUID DEFAULT_USER_ID =
        UUID.fromString("00000000-0000-0000-0000-000000000001");

    private final StoryRepository storyRepository;

    public StoryService(StoryRepository storyRepository) {
        this.storyRepository = storyRepository;
    }

    @Transactional
    public Story create(StoryCreateRequest request) {
        Story story = new Story();
        story.setUserId(DEFAULT_USER_ID);
        story.setTitle(request.title());
        story.setDescription(request.description());
        story.setGenre(request.genre());
        story.setTargetWords(request.targetWords());
        story.setStatus(StoryStatus.DRAFT);
        return storyRepository.save(story);
    }

    @Transactional(readOnly = true)
    public List<Story> list() {
        return storyRepository.findAll(Sort.by(Sort.Direction.DESC, "createdAt"));
    }

    @Transactional(readOnly = true)
    public Story get(UUID storyId) {
        return storyRepository.findById(storyId)
            .orElseThrow(() -> new ResourceNotFoundException("Story not found: " + storyId));
    }
}
