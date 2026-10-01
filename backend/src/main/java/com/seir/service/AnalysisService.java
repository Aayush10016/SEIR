package com.seir.service;

import com.seir.dto.AnalysisRequest;
import com.seir.dto.AnalysisResponse;
import com.seir.exception.ResourceNotFoundException;
import com.seir.model.AnalysisJob;
import com.seir.model.AnalysisStatus;
import com.seir.model.Repository;
import com.seir.repository.AnalysisJobRepository;
import com.seir.repository.RepositoryEntityRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class AnalysisService {

    private final AnalysisJobRepository analysisJobRepository;
    private final RepositoryEntityRepository repositoryEntityRepository;

    @Transactional
    public AnalysisResponse createAnalysis(AnalysisRequest request) {
        Repository repository = repositoryEntityRepository.findById(request.repositoryId())
                .orElseThrow(() -> new ResourceNotFoundException("Repository not found with id: " + request.repositoryId()));

        AnalysisJob analysisJob = new AnalysisJob();
        analysisJob.setRepository(repository);
        analysisJob.setStatus(AnalysisStatus.QUEUED);

        AnalysisJob savedAnalysisJob = analysisJobRepository.save(analysisJob);
        return AnalysisResponse.from(savedAnalysisJob);
    }

    @Transactional(readOnly = true)
    public AnalysisResponse getAnalysis(Long id) {
        AnalysisJob analysisJob = analysisJobRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Analysis job not found with id: " + id));

        return AnalysisResponse.from(analysisJob);
    }
}
