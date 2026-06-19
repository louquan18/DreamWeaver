package com.dreamweaver.entity;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class ChapterOutlineStatusConverter implements AttributeConverter<ChapterOutlineStatus, String> {

    @Override
    public String convertToDatabaseColumn(ChapterOutlineStatus attribute) {
        return attribute == null ? null : attribute.value();
    }

    @Override
    public ChapterOutlineStatus convertToEntityAttribute(String dbData) {
        return dbData == null ? null : ChapterOutlineStatus.fromValue(dbData);
    }
}
