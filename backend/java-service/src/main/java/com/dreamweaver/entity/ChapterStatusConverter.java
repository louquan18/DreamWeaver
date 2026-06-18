package com.dreamweaver.entity;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class ChapterStatusConverter implements AttributeConverter<ChapterStatus, String> {

    @Override
    public String convertToDatabaseColumn(ChapterStatus attribute) {
        return attribute == null ? null : attribute.value();
    }

    @Override
    public ChapterStatus convertToEntityAttribute(String dbData) {
        return dbData == null ? null : ChapterStatus.fromValue(dbData);
    }
}
