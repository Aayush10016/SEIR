package com.seir.dto;

import com.seir.model.Repository;
import java.time.Instant;

public record RepositoryResponse(
        Long id,
        String url,
        Instant createdAt
) {

    public static RepositoryResponse from(Repository repository) {
        return new RepositoryResponse(
                repository.getId(),
                repository.getUrl(),
                repository.getCreatedAt()
        );
    }
}
