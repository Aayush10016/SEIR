package com.seir.service;

import com.seir.dto.RepositoryRequest;
import com.seir.dto.RepositoryResponse;
import com.seir.model.Repository;
import com.seir.repository.RepositoryEntityRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
public class RepositoryService {

    private final RepositoryEntityRepository repositoryEntityRepository;

    @Transactional
    public RepositoryResponse registerRepository(RepositoryRequest request) {
        Repository repository = new Repository();
        repository.setUrl(request.url());

        Repository savedRepository = repositoryEntityRepository.save(repository);
        return RepositoryResponse.from(savedRepository);
    }
}
