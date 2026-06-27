package com.dreamweaver.dto;

import java.util.List;

public record AiAdditionalMemoryRetrieveRequest(
    String query,
    Integer k,
    List<Integer> chapterRange
) {
}
