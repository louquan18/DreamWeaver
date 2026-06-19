package com.dreamweaver.service;

import java.util.List;
import java.util.UUID;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.dreamweaver.dto.AiOutlineOptionResponse;
import com.dreamweaver.dto.AiOutlineOptionsGenerateRequest;
import com.dreamweaver.dto.AiOutlineOptionsGenerateResponse;
import com.dreamweaver.dto.ChapterOutlineOptionsGenerateRequest;
import com.dreamweaver.entity.Chapter;
import com.dreamweaver.entity.ChapterOutlineOption;
import com.dreamweaver.entity.ChapterWorkflowStage;
import com.dreamweaver.entity.OutlineOptionCode;
import com.dreamweaver.entity.OutlineOptionStatus;
import com.dreamweaver.entity.OutlineOptionType;
import com.dreamweaver.repository.ChapterOutlineOptionRepository;
import com.dreamweaver.repository.ChapterRepository;
import com.dreamweaver.repository.StoryRepository;

@Service
public class ChapterOutlineOptionService {

    private static final String AI_WORKER_ERROR = "ai_worker_error";

    private final StoryRepository storyRepository;
    private final ChapterRepository chapterRepository;
    private final ChapterOutlineOptionRepository optionRepository;
    private final AiOutlineClient aiOutlineClient;

    public ChapterOutlineOptionService(
        StoryRepository storyRepository,
        ChapterRepository chapterRepository,
        ChapterOutlineOptionRepository optionRepository,
        AiOutlineClient aiOutlineClient
    ) {
        this.storyRepository = storyRepository;
        this.chapterRepository = chapterRepository;
        this.optionRepository = optionRepository;
        this.aiOutlineClient = aiOutlineClient;
    }

    @Transactional
    public GeneratedOutlineOptions generate(
        UUID storyId,
        UUID chapterId,
        ChapterOutlineOptionsGenerateRequest request
    ) {
        getStory(storyId);
        Chapter chapter = getChapter(storyId, chapterId);
        UUID optionGroupId = UUID.randomUUID();

        AiOutlineOptionsGenerateResponse generated = aiOutlineClient.generateOutlineOptions(
            storyId,
            chapterId,
            new AiOutlineOptionsGenerateRequest(
                optionGroupId.toString(),
                request == null ? null : request.authorIntent()
            )
        );
        validateGeneratedResponse(storyId, chapterId, optionGroupId, generated);

        List<ChapterOutlineOption> options = generated.options().stream()
            .map(option -> toEntity(storyId, chapterId, optionGroupId, option))
            .toList();
        List<ChapterOutlineOption> savedOptions = optionRepository.saveAll(options);

        chapter.setWorkflowStage(ChapterWorkflowStage.OUTLINE_OPTIONS_GENERATED);
        chapterRepository.save(chapter);

        return new GeneratedOutlineOptions(chapter, savedOptions);
    }

    private void getStory(UUID storyId) {
        storyRepository.findById(storyId)
            .orElseThrow(() -> new ResourceNotFoundException("Story not found: " + storyId));
    }

    private Chapter getChapter(UUID storyId, UUID chapterId) {
        return chapterRepository.findByIdAndStoryId(chapterId, storyId)
            .orElseThrow(() -> new ResourceNotFoundException("Chapter not found: " + chapterId));
    }

    private void validateGeneratedResponse(
        UUID storyId,
        UUID chapterId,
        UUID optionGroupId,
        AiOutlineOptionsGenerateResponse generated
    ) {
        if (generated == null || generated.options() == null || generated.options().size() != 3) {
            throw new AiWorkerException(AI_WORKER_ERROR, "AI worker must return exactly three outline options");
        }
        if (generated.storyId() != null && !generated.storyId().equals(storyId.toString())) {
            throw new AiWorkerException(AI_WORKER_ERROR, "AI worker returned options for a different story");
        }
        if (generated.chapterId() != null && !generated.chapterId().equals(chapterId.toString())) {
            throw new AiWorkerException(AI_WORKER_ERROR, "AI worker returned options for a different chapter");
        }
        if (generated.optionGroupId() != null && !generated.optionGroupId().equals(optionGroupId.toString())) {
            throw new AiWorkerException(AI_WORKER_ERROR, "AI worker returned options for a different group");
        }
    }

    private ChapterOutlineOption toEntity(
        UUID storyId,
        UUID chapterId,
        UUID optionGroupId,
        AiOutlineOptionResponse generated
    ) {
        ChapterOutlineOption option = new ChapterOutlineOption();
        option.setStoryId(storyId);
        option.setChapterId(chapterId);
        option.setOptionGroupId(optionGroupId);
        option.setOptionCode(OutlineOptionCode.fromValue(generated.optionCode()));
        option.setOptionType(OutlineOptionType.fromValue(generated.optionType()));
        option.setTitleCandidates(generated.titleCandidates());
        option.setChapterGoal(generated.chapterGoal());
        option.setStorySummary(generated.storySummary());
        option.setSceneOutline(generated.sceneOutline());
        option.setCharactersInvolved(generated.charactersInvolved());
        option.setConflict(generated.conflict());
        option.setHighlightMoment(generated.highlightMoment());
        option.setForeshadowActions(generated.foreshadowActions());
        option.setMemoryReferences(generated.memoryReferences());
        option.setWhyThisPlan(generated.whyThisPlan());
        option.setEndingHook(generated.endingHook());
        option.setRiskNotes(generated.riskNotes());
        option.setStatus(OutlineOptionStatus.GENERATED);
        return option;
    }

    public record GeneratedOutlineOptions(Chapter chapter, List<ChapterOutlineOption> options) {
    }
}
