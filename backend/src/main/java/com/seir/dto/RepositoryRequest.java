package com.seir.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record RepositoryRequest(
        @NotBlank(message = "Repository URL is required")
        @Size(max = 2048, message = "Repository URL must be at most 2048 characters")
        @Pattern(regexp = "^https?://.+", message = "Repository URL must start with http:// or https://")
        String url
) {
}
