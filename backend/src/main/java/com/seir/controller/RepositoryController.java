package com.seir.controller;

import com.seir.dto.RepositoryRequest;
import com.seir.dto.RepositoryResponse;
import com.seir.service.RepositoryService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/repositories")
@RequiredArgsConstructor
public class RepositoryController {

    private final RepositoryService repositoryService;

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public RepositoryResponse registerRepository(@Valid @RequestBody RepositoryRequest request) {
        return repositoryService.registerRepository(request);
    }
}
