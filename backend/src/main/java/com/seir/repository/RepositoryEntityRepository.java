package com.seir.repository;

import com.seir.model.Repository;
import org.springframework.data.jpa.repository.JpaRepository;

public interface RepositoryEntityRepository extends JpaRepository<Repository, Long> {
}
