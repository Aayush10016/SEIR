package com.seir.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.seir.dto.AnalysisRequest;
import com.seir.dto.AnalysisResponse;
import com.seir.exception.ResourceNotFoundException;
import com.seir.model.AnalysisJob;
import com.seir.model.AnalysisStatus;
import com.seir.model.Repository;
import com.seir.repository.AnalysisJobRepository;
import com.seir.repository.RepositoryEntityRepository;
import java.time.Instant;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class AnalysisServiceTest {

    @Mock
    private AnalysisJobRepository analysisJobRepository;

    @Mock
    private RepositoryEntityRepository repositoryEntityRepository;

    @InjectMocks
    private AnalysisService analysisService;

    @Test
    void createAnalysisQueuesJobForRepository() {
        Repository repository = new Repository();
        repository.setId(1L);
        repository.setUrl("https://github.com/example/payment-system");

        AnalysisJob savedJob = new AnalysisJob();
        savedJob.setId(10L);
        savedJob.setRepository(repository);
        savedJob.setStatus(AnalysisStatus.QUEUED);
        savedJob.setCreatedAt(Instant.parse("2026-01-01T00:00:00Z"));

        when(repositoryEntityRepository.findById(1L)).thenReturn(Optional.of(repository));
        when(analysisJobRepository.save(any(AnalysisJob.class))).thenReturn(savedJob);

        AnalysisResponse response = analysisService.createAnalysis(new AnalysisRequest(1L));

        assertThat(response.id()).isEqualTo(10L);
        assertThat(response.repositoryId()).isEqualTo(1L);
        assertThat(response.status()).isEqualTo(AnalysisStatus.QUEUED);
        verify(analysisJobRepository).save(any(AnalysisJob.class));
    }

    @Test
    void createAnalysisFailsWhenRepositoryDoesNotExist() {
        when(repositoryEntityRepository.findById(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> analysisService.createAnalysis(new AnalysisRequest(99L)))
                .isInstanceOf(ResourceNotFoundException.class)
                .hasMessage("Repository not found with id: 99");
    }
}
