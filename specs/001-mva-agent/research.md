# Research Summary: Minimum Viable Agent (Digital FTE)

## Technical Decisions

### File Monitoring Solution
- **Decision**: Use `watchdog` library for cross-platform filesystem monitoring
- **Rationale**: Provides efficient, cross-platform file system event monitoring with low latency; meets 5-second detection requirement
- **Alternatives considered**:
  - `pyinotify` (Linux-only, less portable)
  - Polling mechanism (higher resource usage, less responsive)
  - `fsevents` (macOS only)

### Agent Architecture Pattern
- **Decision**: Implement Perception → Reasoning → Memory loop using separate modules
- **Rationale**: Matches specified architecture and separates concerns for maintainability
- **Alternatives considered**:
  - Monolithic design (less maintainable)
  - Microservices (overkill for local-first agent)

### File Processing Pipeline
- **Decision**: Use Claude Code API integration for reasoning component
- **Rationale**: Leverages specified AI agent capabilities for intelligent processing
- **Alternatives considered**:
  - Rule-based processing (less intelligent)
  - Other AI APIs (different ecosystem)

### Dashboard Implementation
- **Decision**: Use markdown file (`Dashboard.md`) with real-time updates
- **Rationale**: Simple, observable format that can be viewed in any editor; meets real-time requirement
- **Alternatives considered**:
  - Database with web interface (more complex)
  - Static HTML generation (less observable)

### Configuration Management
- **Decision**: Use `.env` file with python-dotenv for secret management
- **Rationale**: Standard practice for environment variables; secure API key storage
- **Alternatives considered**:
  - Hardcoded values (insecure)
  - Command-line arguments (exposed in process list)

### Error Handling Strategy
- **Decision**: Exponential backoff with retry attempts and error queue
- **Rationale**: Resilient handling of transient failures while preventing infinite loops
- **Alternatives considered**:
  - Immediate failure (poor resilience)
  - Infinite retries (potential for hanging processes)

## Technology Stack

### Core Dependencies
- **Python 3.10+**: Modern Python version with good async support
- **watchdog**: Cross-platform file system monitoring
- **python-dotenv**: Environment variable management
- **pytest**: Testing framework for TDD approach
- **requests**: API communication with Claude Code

### Development Tools
- **Git**: Version control
- **Virtual environments**: Dependency isolation
- **Structured logging**: Observability and debugging

## Implementation Approach

### Phased Development
1. **Phase 1**: Core filesystem monitoring and trigger generation
2. **Phase 2**: Claude Code integration for reasoning
3. **Phase 3**: Dashboard updates and visualization
4. **Phase 4**: Error handling and resilience
5. **Phase 5**: Security and observability features

### Testing Strategy
- Unit tests for each module
- Integration tests for end-to-end file processing pipeline
- Contract tests for API interactions
- Performance tests to verify 5-second detection requirement