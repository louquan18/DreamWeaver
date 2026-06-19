package com.dreamweaver.dto;

import java.util.List;

public record AiOutlineOptionsGenerateResponse(
    String storyId,
    String chapterId,
    String optionGroupId,
    List<AiOutlineOptionResponse> options
) {
}
