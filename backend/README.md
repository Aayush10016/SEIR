# SEIR Backend

SEIR, Software Evolution Intelligence & Risk Analysis, is a university capstone platform for understanding how a software repository evolves and where change risk may exist.

This backend is the first foundation layer, approximately the first 30% of backend development. It provides stable REST APIs, persistence models, validation, and error handling so future team modules can plug into the system without tightly coupling to one another.

## Technology Stack

- Java 17
- Spring Boot 3.5.x
- Maven
- PostgreSQL
- Spring Data JPA
- Jakarta Validation
- JUnit 5
- Mockito

## Current Scope

Implemented now:

- Spring Boot project foundation
- Health API
- Repository registration API
- Analysis job creation API
- Analysis status lookup API
- Basic validation and global exception handling
- Focused controller and service tests

Intentionally not implemented yet:

- Static code analysis
- Dependency graph generation
- Git mining or commit analysis
- Runtime/configuration analysis
- AI explanations
- Risk scoring
- Impact analysis
- Authentication
- Frontend integration
- Distributed/asynchronous processing

## Run Locally

From the backend folder:

```bash
mvn spring-boot:run
```

The API starts on port `8080` by default.

## Database Configuration

The backend is configured for PostgreSQL using environment variables:

```bash
DB_URL=jdbc:postgresql://localhost:5432/seir
DB_USERNAME=seir
DB_PASSWORD=your-local-password
```

Safe local defaults are provided in `src/main/resources/application.properties`, but no secrets are committed.

## Tests

Run:

```bash
mvn clean test
```

Tests use an in-memory H2 database in PostgreSQL compatibility mode where persistence context is needed.

## API Endpoints

### Health

`GET /api/health`

Response:

```json
{
  "status": "UP",
  "service": "SEIR Backend"
}
```

### Register Repository

`POST /api/repositories`

Request:

```json
{
  "url": "https://github.com/example/payment-system"
}
```

Response:

```json
{
  "id": 1,
  "url": "https://github.com/example/payment-system",
  "createdAt": "2026-01-01T00:00:00Z"
}
```

### Create Analysis Job

`POST /api/analyses`

Request:

```json
{
  "repositoryId": 1
}
```

Response:

```json
{
  "id": 1,
  "repositoryId": 1,
  "status": "QUEUED",
  "createdAt": "2026-01-01T00:00:00Z"
}
```

### Get Analysis Job

`GET /api/analyses/{id}`

Response:

```json
{
  "id": 1,
  "repositoryId": 1,
  "status": "QUEUED",
  "createdAt": "2026-01-01T00:00:00Z"
}
```

## Data Model

Current entities:

- `Repository`: `id`, `url`, `createdAt`
- `AnalysisJob`: `id`, `repository`, `status`, `createdAt`

Analysis status values:

- `QUEUED`
- `RUNNING`
- `COMPLETED`
- `FAILED`

Future modules can add `Component`, `Dependency`, `Evidence`, `RiskAssessment`, and `ImpactAnalysis` after the team is ready for those parts.
