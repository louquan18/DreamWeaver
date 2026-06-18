package com.dreamweaver.service;

import java.util.List;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.dreamweaver.dto.ChapterCreateRequest;
import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.ChapterStatus;
import com.dreamweaver.repository.ChapterRepository;

@Service
public class ChapterService {

    private final ChapterRepository chapterRepository;
    private final StoryService storyService;

    public ChapterService(ChapterRepository chapterRepository, StoryService storyService) {
        this.chapterRepository = chapterRepository;
        this.storyService = storyService;
    }

    @Transactional
    public Chapter create(UUID storyId, ChapterCreateRequest request) {
        storyService.get(storyId);

        if (chapterRepository.existsByStoryIdAndChapterNumber(storyId, request.chapterNumber())) {
            throw new BadRequestException(
                "Chapter number already exists for story: " + request.chapterNumber()
            );
        }

        Chapter chapter = new Chapter();
        chapter.setStoryId(storyId);
        chapter.setChapterNumber(request.chapterNumber());
        chapter.setTitle(request.title());
        chapter.setStatus(ChapterStatus.DRAFT);
        return chapterRepository.save(chapter);
    }

    @Transactional(readOnly = true)
    public List<Chapter> list(UUID storyId) {
        storyService.get(storyId);
        return chapterRepository.findByStoryIdOrderByChapterNumberAsc(storyId);
    }

    @Transactional(readOnly = true)
    public Chapter get(UUID storyId, UUID chapterId) {
        return chapterRepository.findByIdAndStoryId(chapterId, storyId)
            .orElseThrow(() -> new ResourceNotFoundException(
                "Chapter not found: " + chapterId
            ));
    }

    @Transactional
    public Chapter save(Chapter chapter) {
        return chapterRepository.save(chapter);
    }
}
