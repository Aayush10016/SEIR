package com.seir.dto;

import com.seir.model.AnalysisJob;
import com.seir.model.AnalysisStatus;
import java.time.Instant;

public record AnalysisResponse(
        Long id,
        Long repositoryId,
        AnalysisStatus status,
        Instant createdAt
) {

    public static AnalysisResponse from(AnalysisJob analysisJob) {
        return new AnalysisResponse(
                analysisJob.getId(),
                analysisJob.getRepository().getId(),
                analysisJob.getStatus(),
                analysisJob.getCreatedAt()
        );
    }
}
