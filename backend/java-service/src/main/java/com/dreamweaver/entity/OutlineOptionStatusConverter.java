package com.dreamweaver.entity;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

@Converter(autoApply = true)
public class OutlineOptionStatusConverter implements AttributeConverter<OutlineOptionStatus, String> {

    @Override
    public String convertToDatabaseColumn(OutlineOptionStatus attribute) {
        return attribute == null ? null : attribute.value();
    }

    @Override
    public OutlineOptionStatus convertToEntityAttribute(String dbData) {
        return dbData == null ? null : OutlineOptionStatus.fromValue(dbData);
    }
}
