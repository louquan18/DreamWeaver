package com.dreamweaver.controller;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import com.dreamweaver.entity.Story;
import com.dreamweaver.entity.StoryStatus;
import com.dreamweaver.service.BadRequestException;
import com.dreamweaver.service.StoryMemoryService;
import com.dreamweaver.service.StoryService;

class StoryMemoryControllerTests {

    private static final UUID STORY_ID = UUID.fromString("10000000-0000-0000-0000-000000000092");

    @Test
    void getMemoryReturnsStoryScopedLibraryJson() throws Exception {
        StoryService storyService = Mockito.mock(StoryService.class);
        StoryMemoryService memoryService = Mockito.mock(StoryMemoryService.class);
        when(storyService.get(STORY_ID)).thenReturn(story());
        when(memoryService.library(STORY_ID, "characters")).thenReturn(new StoryMemoryService.MemoryLibrary(
            "characters",
            List.of(Map.of("id", "character:Lin Jin", "name", "Lin Jin")),
            Map.of("algorithm", "sha-256", "hash", "abc")
        ));

        mockMvc(storyService, memoryService).perform(get(
                "/api/stories/{storyId}/memories/{memoryType}",
                STORY_ID,
                "characters"
            ))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.storyId").value(STORY_ID.toString()))
            .andExpect(jsonPath("$.type").value("characters"))
            .andExpect(jsonPath("$.count").value(1))
            .andExpect(jsonPath("$.items[0].name").value("Lin Jin"))
            .andExpect(jsonPath("$.fingerprint.hash").value("abc"));
    }

    @Test
    void invalidMemoryTypeUsesApiErrorShape() throws Exception {
        StoryService storyService = Mockito.mock(StoryService.class);
        StoryMemoryService memoryService = Mockito.mock(StoryMemoryService.class);
        when(storyService.get(STORY_ID)).thenReturn(story());
        when(memoryService.library(STORY_ID, "unknown")).thenThrow(new BadRequestException(
            "memory_type_invalid",
            "Unsupported story memory type: unknown"
        ));

        mockMvc(storyService, memoryService).perform(get(
                "/api/stories/{storyId}/memories/{memoryType}",
                STORY_ID,
                "unknown"
            ))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.error").value("memory_type_invalid"));
    }

    private MockMvc mockMvc(StoryService storyService, StoryMemoryService memoryService) {
        StoryMemoryController controller = new StoryMemoryController(storyService, memoryService);
        return MockMvcBuilders.standaloneSetup(controller)
            .setControllerAdvice(new GlobalExceptionHandler())
            .build();
    }

    private Story story() {
        Story story = new Story();
        story.setId(STORY_ID);
        story.setTitle("Mirror Fire");
        story.setStatus(StoryStatus.DRAFT);
        return story;
    }
}
