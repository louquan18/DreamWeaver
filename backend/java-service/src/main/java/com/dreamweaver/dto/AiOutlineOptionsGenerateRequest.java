package com.dreamweaver.dto;

import java.util.Map;

public record AiOutlineOptionsGenerateRequest(
    String optionGroupId,
    Map<String, Object> authorIntent
) {
}
