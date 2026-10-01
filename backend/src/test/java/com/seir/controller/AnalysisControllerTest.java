package com.seir.controller;

import static org.hamcrest.Matchers.is;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.seir.dto.AnalysisRequest;
import com.seir.dto.AnalysisResponse;
import com.seir.exception.ResourceNotFoundException;
import com.seir.model.AnalysisStatus;
import com.seir.service.AnalysisService;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(AnalysisController.class)
class AnalysisControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private AnalysisService analysisService;

    @Test
    void createAnalysisReturnsQueuedJob() throws Exception {
        when(analysisService.createAnalysis(any(AnalysisRequest.class)))
                .thenReturn(new AnalysisResponse(1L, 7L, AnalysisStatus.QUEUED, Instant.parse("2026-01-01T00:00:00Z")));

        mockMvc.perform(post("/api/analyses")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "repositoryId": 7
                                }
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id", is(1)))
                .andExpect(jsonPath("$.repositoryId", is(7)))
                .andExpect(jsonPath("$.status", is("QUEUED")))
                .andExpect(jsonPath("$.createdAt", is("2026-01-01T00:00:00Z")));
    }

    @Test
    void getAnalysisReturnsExistingJob() throws Exception {
        when(analysisService.getAnalysis(1L))
                .thenReturn(new AnalysisResponse(1L, 7L, AnalysisStatus.QUEUED, Instant.parse("2026-01-01T00:00:00Z")));

        mockMvc.perform(get("/api/analyses/1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id", is(1)))
                .andExpect(jsonPath("$.repositoryId", is(7)))
                .andExpect(jsonPath("$.status", is("QUEUED")));
    }

    @Test
    void getAnalysisReturnsNotFoundForMissingJob() throws Exception {
        when(analysisService.getAnalysis(999L))
                .thenThrow(new ResourceNotFoundException("Analysis job not found with id: 999"));

        mockMvc.perform(get("/api/analyses/999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.message", is("Analysis job not found with id: 999")));
    }
}
