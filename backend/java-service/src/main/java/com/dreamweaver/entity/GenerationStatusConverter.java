package com.dreamweaver.entity;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class GenerationStatusConverter implements AttributeConverter<GenerationStatus, String> {

    @Override
    public String convertToDatabaseColumn(GenerationStatus attribute) {
        return attribute == null ? null : attribute.value();
    }

    @Override
    public GenerationStatus convertToEntityAttribute(String dbData) {
        return dbData == null ? null : GenerationStatus.fromValue(dbData);
    }
}
