package com.dreamweaver.entity;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class StoryStatusConverter implements AttributeConverter<StoryStatus, String> {

    @Override
    public String convertToDatabaseColumn(StoryStatus attribute) {
        return attribute == null ? null : attribute.value();
    }

    @Override
    public StoryStatus convertToEntityAttribute(String dbData) {
        return dbData == null ? null : StoryStatus.fromValue(dbData);
    }
}
