package com.dreamweaver.dto;

import jakarta.validation.Valid;

public record NovelBlueprintConfirmRequest(
    @Valid
    NovelBlueprintUpdateRequest editedBlueprint
) {
}
