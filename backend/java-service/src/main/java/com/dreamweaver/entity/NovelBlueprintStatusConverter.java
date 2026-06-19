package com.dreamweaver.entity;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class NovelBlueprintStatusConverter implements AttributeConverter<NovelBlueprintStatus, String> {

    @Override
    public String convertToDatabaseColumn(NovelBlueprintStatus attribute) {
        return attribute == null ? null : attribute.value();
    }

    @Override
    public NovelBlueprintStatus convertToEntityAttribute(String dbData) {
        return dbData == null ? null : NovelBlueprintStatus.fromValue(dbData);
    }
}
