package com.dreamweaver.entity;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class OutlineOptionTypeConverter implements AttributeConverter<OutlineOptionType, String> {

    @Override
    public String convertToDatabaseColumn(OutlineOptionType attribute) {
        return attribute == null ? null : attribute.value();
    }

    @Override
    public OutlineOptionType convertToEntityAttribute(String dbData) {
        return dbData == null ? null : OutlineOptionType.fromValue(dbData);
    }
}
