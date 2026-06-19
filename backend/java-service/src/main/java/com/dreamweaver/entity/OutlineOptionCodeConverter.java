package com.dreamweaver.entity;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class OutlineOptionCodeConverter implements AttributeConverter<OutlineOptionCode, String> {

    @Override
    public String convertToDatabaseColumn(OutlineOptionCode attribute) {
        return attribute == null ? null : attribute.value();
    }

    @Override
    public OutlineOptionCode convertToEntityAttribute(String dbData) {
        return dbData == null ? null : OutlineOptionCode.fromValue(dbData);
    }
}
