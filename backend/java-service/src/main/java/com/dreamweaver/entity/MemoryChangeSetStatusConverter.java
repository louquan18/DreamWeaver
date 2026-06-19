package com.dreamweaver.entity;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class MemoryChangeSetStatusConverter implements AttributeConverter<MemoryChangeSetStatus, String> {

    @Override
    public String convertToDatabaseColumn(MemoryChangeSetStatus attribute) {
        return attribute == null ? null : attribute.value();
    }

    @Override
    public MemoryChangeSetStatus convertToEntityAttribute(String dbData) {
        return dbData == null ? null : MemoryChangeSetStatus.fromValue(dbData);
    }
}
