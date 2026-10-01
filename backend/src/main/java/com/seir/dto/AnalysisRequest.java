package com.seir.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

public record AnalysisRequest(
        @NotNull(message = "Repository ID is required")
        @Positive(message = "Repository ID must be positive")
        Long repositoryId
) {
}
