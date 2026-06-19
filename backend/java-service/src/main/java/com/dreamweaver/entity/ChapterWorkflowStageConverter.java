package com.dreamweaver.entity;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class ChapterWorkflowStageConverter implements AttributeConverter<ChapterWorkflowStage, String> {

    @Override
    public String convertToDatabaseColumn(ChapterWorkflowStage attribute) {
        return attribute == null ? null : attribute.value();
    }

    @Override
    public ChapterWorkflowStage convertToEntityAttribute(String dbData) {
        return dbData == null ? null : ChapterWorkflowStage.fromValue(dbData);
    }
}
