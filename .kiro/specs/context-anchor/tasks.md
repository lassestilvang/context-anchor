# Implementation Plan: ContextAnchor

## Overview

ContextAnchor is a developer workflow state management system that eliminates context-switching overhead through passive git monitoring and explicit intent capture. The implementation uses Python 3.11+ for the CLI tool, AWS serverless architecture (Lambda, API Gateway, DynamoDB, Bedrock, S3), and property-based testing with Hypothesis.

The system consists of:
- CLI Tool: Command interface, git signal collection, API communication, offline queue
- Git Observer: Hook installation, activity monitoring, GitHub parsing
- Agent Core: Lambda function with Bedrock integration for AI synthesis
- Context Store: DynamoDB tables with proper indexing
- API Gateway: REST endpoints for context operations
- GitHub Integration: Remote parsing, reference extraction
- Metrics: Event emission, time-to-productivity tracking
- Infrastructure: AWS CDK deployment with cost guardrails

## Tasks

- [x] 1. Set up project structure and development environment
  - Create Python package structure with src/contextanchor directory
  - Set up pyproject.toml with dependencies: Click/Typer, GitPython, boto3, hypothesis, pytest
  - Configure development tools: black, flake8, mypy, bandit
  - Create .gitignore for Python projects
  - Set up virtual environment and dependency management
  - _Requirements: 14.1, 14.2, 14.3, 14.4_

- [ ] 2. Implement core data models and validation
  - [x] 2.1 Create domain model classes with dataclasses
    - Implement ContextSnapshot with all required fields and validation
    - Implement CaptureSignals, FileChange, CommitInfo models
    - Implement Repository, GitHubRepo, Config models
    - Implement QueuedOperation for offline queue
    - Add __post_init__ validation for ContextSnapshot (1-5 next steps, action verbs, word limits)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.7, 3.9_

  - [x] 2.2 Write property test for ContextSnapshot schema completeness
    - **Property 6: Complete Context Snapshot Schema**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.7**

  - [x] 2.3 Write property test for snapshot word limit constraint
    - **Property 7: Snapshot Word Limit Constraint**
    - **Validates: Requirements 3.6**

  - [x] 2.4 Write property test for next steps format validation
    - **Property 9: Next Steps Format Validation**
    - **Validates: Requirements 3.9**


- [ ] 3. Implement Git Observer component
  - [x] 3.1 Create GitObserver class with repository detection
    - Implement repository root detection using GitPython
    - Implement git availability check
    - Implement remote URL extraction
    - Implement repository_id generation (SHA-256 hash of remote + path)
    - _Requirements: 1.5, 7.4, 11.4, 11.6_

  - [x] 3.2 Implement git signal capture methods
    - Implement capture_commit_signal (hash, message, timestamp, files)
    - Implement capture_branch_switch (from_branch, to_branch, timestamp)
    - Implement capture_uncommitted_changes (staged and unstaged)
    - Implement capture_diff_signal (file paths, summary stats)
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.6_

  - [x] 3.3 Write property tests for signal capture completeness
    - **Property 1: Complete Commit Signal Capture**
    - **Property 2: Complete Branch Switch Signal Capture**
    - **Property 3: Complete Diff Signal Capture**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.5, 1.6**

  - [x] 3.4 Implement GitHub integration methods
    - Implement parse_remote_url to extract owner/repo from GitHub URLs
    - Implement parse_pr_references using regex patterns (#123, PR #123)
    - Implement parse_issue_references with keywords (fixes, closes, resolves, refs)
    - Implement format_pr_link and format_issue_link
    - _Requirements: 10.1, 10.2, 10.3, 10.6_

  - [x] 3.5 Write property test for reference extraction
    - **Property 4: Reference Extraction from Commit Messages**
    - **Validates: Requirements 1.4, 10.2, 10.3, 10.6**

  - [x] 3.6 Write property test for GitHub remote parsing
    - **Property 35: GitHub Remote Parsing**
    - **Validates: Requirements 10.1**

  - [x] 3.7 Implement git hook installation
    - Create post-checkout hook template for branch switch detection
    - Create post-commit hook template for commit signal capture
    - Implement install_hooks method with permission checks
    - Implement hook status detection (active, degraded, unavailable)
    - _Requirements: 5.6, 7.6_

  - [-] 3.8 Write unit tests for git operations
    - Test repository detection from subdirectories
    - Test git availability check
    - Test hook installation with various permission scenarios
    - Test error handling for git command failures
    - _Requirements: 6.5, 7.4, 8.3_

- [~] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 5. Implement local storage and offline queue
  - [~] 5.1 Create LocalStorage class using SQLite
    - Implement SQLite schema for offline queue (operation_id, type, payload, timestamps)
    - Implement queue_operation method to store operations locally
    - Implement get_pending_operations to retrieve queued items
    - Implement mark_operation_complete to remove from queue
    - Implement cache for Context_Snapshots
    - _Requirements: 8.1, 8.4, 8.6_

  - [~] 5.2 Implement retry logic with exponential backoff
    - Implement retry_operation with exponential backoff calculation
    - Implement operation expiration after 24 hours
    - Implement next_retry_at calculation
    - Add retry_count tracking
    - _Requirements: 8.7_

  - [~] 5.3 Write property test for offline queue capacity
    - **Property 29: Offline Queue Capacity**
    - **Validates: Requirements 8.6**

  - [~] 5.4 Write property test for exponential backoff
    - **Property 30: Exponential Backoff and Expiration**
    - **Validates: Requirements 8.7**

  - [~] 5.5 Write unit tests for offline operations
    - Test queue storage and retrieval
    - Test operation expiration
    - Test cache functionality
    - _Requirements: 8.1, 8.4, 8.8_

- [ ] 6. Implement configuration management
  - [~] 6.1 Create Config class and YAML parser
    - Implement Config dataclass with all configuration fields
    - Implement load_config from ~/.contextanchor/config.yaml
    - Implement default configuration values
    - Implement config validation with schema checking
    - _Requirements: 15.1, 15.5, 15.6_

  - [~] 6.2 Implement configuration customization
    - Support custom capture prompt configuration
    - Support custom retention period configuration
    - Support enabled_signals list configuration
    - Support redact_patterns list configuration
    - _Requirements: 15.2, 15.3, 15.4_

  - [~] 6.3 Write property tests for configuration
    - **Property 46: Custom Prompt Configuration**
    - **Property 47: Custom Retention Configuration**
    - **Property 48: Signal Monitoring Configuration**
    - **Property 49: Invalid Configuration Handling**
    - **Validates: Requirements 15.2, 15.3, 15.4, 15.5, 15.6**

  - [~] 6.4 Write unit tests for configuration edge cases
    - Test missing config file (use defaults)
    - Test invalid YAML syntax
    - Test invalid field types
    - Test partial configuration (merge with defaults)
    - _Requirements: 15.5, 15.6_


- [ ] 7. Implement AWS infrastructure with CDK
  - [~] 7.1 Create CDK stack for DynamoDB tables
    - Define ContextSnapshots table with PK (REPO#id) and SK (BRANCH#branch#TS#timestamp)
    - Add GSI ByDeveloper (PK: DEV#id, SK: TS#timestamp)
    - Add GSI BySnapshotId (PK: SNAPSHOT#id, SK: SNAPSHOT#id)
    - Configure on-demand billing mode
    - Enable encryption at rest with AES-256
    - Configure TTL on retention_expires_at field
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 9.1, 14.1_

  - [~] 7.2 Create CDK stack for Lambda functions
    - Define Lambda function for context capture (Python 3.11, 512MB, 30s timeout)
    - Define Lambda function for context retrieval
    - Define Lambda function for context deletion
    - Define Lambda function for context listing
    - Configure IAM roles with least-privilege access
    - _Requirements: 14.3_

  - [~] 7.3 Create CDK stack for API Gateway
    - Define REST API with regional endpoint
    - Create POST /v1/contexts endpoint
    - Create GET /v1/contexts/latest endpoint
    - Create GET /v1/contexts/{snapshot_id} endpoint
    - Create GET /v1/contexts (list) endpoint
    - Create DELETE /v1/contexts/{snapshot_id} endpoint
    - Create GET /v1/health endpoint
    - Configure API key authentication
    - Enable TLS 1.3 requirement
    - _Requirements: 9.2, 14.4_

  - [~] 7.4 Create CDK stack for S3 and cost guardrails
    - Define S3 bucket with lifecycle policies
    - Configure AWS Budgets with Free Tier thresholds
    - Set up CloudWatch alarms for cost alerts
    - _Requirements: 14.5, 14.6_

  - [~] 7.5 Write unit tests for CDK constructs
    - Test DynamoDB table configuration
    - Test Lambda function configuration
    - Test API Gateway endpoint configuration
    - Test IAM role permissions

- [~] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 9. Implement Context Store component
  - [~] 9.1 Create ContextStore class with DynamoDB client
    - Initialize boto3 DynamoDB client
    - Implement store_snapshot method with proper key structure
    - Implement get_snapshot_by_id using BySnapshotId GSI
    - Implement get_latest_snapshot with Query on PK/SK
    - Implement list_snapshots with pagination support
    - _Requirements: 4.1, 4.2, 4.3, 12.6_

  - [~] 9.2 Implement soft-delete and purge operations
    - Implement soft_delete_snapshot (set is_deleted=true, deleted_at timestamp)
    - Implement purge_deleted_snapshots (delete items where purge_after_delete_at < now)
    - Ensure deleted snapshots excluded from active reads immediately
    - _Requirements: 4.6, 9.4_

  - [~] 9.3 Write property test for storage round trip
    - **Property 10: Context Storage Round Trip**
    - **Validates: Requirements 4.1**

  - [~] 9.4 Write property tests for indexing
    - **Property 11: Repository and Branch Indexing**
    - **Property 12: Timestamp Indexing**
    - **Validates: Requirements 4.2, 4.3**

  - [~] 9.5 Write property test for soft delete retention
    - **Property 14: Soft Delete Retention**
    - **Validates: Requirements 4.6**

  - [~] 9.6 Write property test for developer scoped storage
    - **Property 32: Developer Scoped Storage**
    - **Validates: Requirements 9.3**

  - [~] 9.7 Write unit tests for Context Store operations
    - Test pagination with next_token
    - Test empty result sets
    - Test DynamoDB error handling
    - Test TTL expiration behavior
    - _Requirements: 4.4, 4.5, 12.6_

- [ ] 10. Implement Agent Core component (Lambda)
  - [~] 10.1 Create AgentCore class with Bedrock client
    - Initialize boto3 Bedrock Runtime client
    - Implement synthesize_context method
    - Implement _build_bedrock_prompt with template
    - Implement _parse_bedrock_response to extract sections
    - Implement _validate_snapshot for schema compliance
    - _Requirements: 3.1, 14.2_

  - [~] 10.2 Implement Bedrock prompt template
    - Create prompt template with sections for developer intent and git signals
    - Include instructions for Goals, Rationale, Open Questions, Next Steps
    - Add word limit constraint (500 words)
    - Add action verb requirement for Next Steps
    - _Requirements: 3.6, 3.9_

  - [~] 10.3 Write property test for context capture signal inclusion
    - **Property 5: Context Capture Includes All Signal Types**
    - **Validates: Requirements 2.1, 2.3, 2.4, 2.6**

  - [~] 10.4 Write unit tests for Agent Core
    - Test Bedrock prompt construction
    - Test response parsing with various formats
    - Test validation error handling
    - Test Bedrock API error handling with fallback
    - Mock Bedrock responses for testing
    - _Requirements: 3.5, 8.2_


- [ ] 11. Implement Lambda handler functions
  - [~] 11.1 Create context capture Lambda handler
    - Implement handler for POST /v1/contexts
    - Parse request body (repository_id, branch, signals, developer_intent)
    - Invoke AgentCore.synthesize_context
    - Store snapshot in ContextStore
    - Return snapshot_id and captured_at
    - Handle errors with appropriate HTTP status codes
    - _Requirements: 3.1, 4.1_

  - [~] 11.2 Create context retrieval Lambda handlers
    - Implement handler for GET /v1/contexts/latest
    - Implement handler for GET /v1/contexts/{snapshot_id}
    - Implement handler for GET /v1/contexts (list with pagination)
    - Return 404 for missing snapshots
    - _Requirements: 5.1, 12.1_

  - [~] 11.3 Create context deletion Lambda handler
    - Implement handler for DELETE /v1/contexts/{snapshot_id}
    - Call ContextStore.soft_delete_snapshot
    - Return deletion confirmation with purge_after timestamp
    - _Requirements: 6.6, 9.4_

  - [~] 11.4 Create health check Lambda handler
    - Implement handler for GET /v1/health
    - Return status and timestamp
    - No authentication required
    - _Requirements: 14.4_

  - [~] 11.5 Write integration tests for Lambda handlers
    - Test capture flow with mocked Bedrock and DynamoDB
    - Test retrieval with various query parameters
    - Test deletion flow
    - Test error scenarios (missing data, invalid input)

- [~] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 13. Implement API client for CLI
  - [~] 13.1 Create APIClient class
    - Implement HTTP client with requests library
    - Implement create_context method (POST /v1/contexts)
    - Implement get_latest_context method (GET /v1/contexts/latest)
    - Implement get_context_by_id method (GET /v1/contexts/{id})
    - Implement list_contexts method (GET /v1/contexts)
    - Implement delete_context method (DELETE /v1/contexts/{id})
    - Load API key from ~/.contextanchor/credentials
    - _Requirements: 4.1, 5.1, 6.3, 6.6, 12.2_

  - [~] 13.2 Implement network error handling
    - Detect network unavailability before API calls
    - Implement retry logic with exponential backoff
    - Implement timeout handling (30 seconds default)
    - Return clear error messages for network failures
    - _Requirements: 8.4, 8.7_

  - [~] 13.3 Write unit tests for API client
    - Test successful API calls with mocked responses
    - Test network error handling
    - Test timeout handling
    - Test authentication with API key
    - Test retry logic

- [ ] 14. Implement CLI command interface
  - [~] 14.1 Create CLI application with Click/Typer
    - Set up CLI application structure
    - Implement command group for contextanchor
    - Add version and help options
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.6_

  - [~] 14.2 Implement init command
    - Detect current repository
    - Check if already initialized
    - Create .contextanchor/config.yaml in repository root
    - Install git hooks (with permission checks)
    - Report hook status (active, degraded, unavailable)
    - Display success message or error
    - _Requirements: 7.1, 7.2, 7.3, 7.5, 7.6_

  - [~] 14.3 Write property tests for init command
    - **Property 20: Initialization Creates Configuration**
    - **Property 21: Git Availability Check**
    - **Property 67: Re-Initialization Detection**
    - **Validates: Requirements 7.2, 7.4, 7.3**

  - [~] 14.4 Write unit tests for init command
    - Test initialization in valid repository
    - Test re-initialization detection
    - Test initialization outside repository
    - Test hook installation with various permissions
    - _Requirements: 7.3, 7.4, 7.5, 11.5_


- [ ] 15. Implement save-context command
  - [~] 15.1 Create save-context command handler
    - Detect current repository and branch
    - Collect git signals using GitObserver
    - Prompt user with configured prompt text
    - Collect developer intent input
    - Apply secret redaction to user input
    - Send signals and intent to API
    - Handle offline mode (queue operation)
    - Display confirmation with snapshot_id
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.6, 6.1, 9.6_

  - [~] 15.2 Implement secret redaction
    - Apply configured redact_patterns to user input
    - Replace matched secrets with [REDACTED]
    - Log redaction events
    - _Requirements: 9.6_

  - [~] 15.3 Write property tests for save-context
    - **Property 54: Exact Prompt Wording**
    - **Property 56: Intent Capture Without Uncommitted Changes**
    - **Property 34: Secret Redaction**
    - **Validates: Requirements 2.2, 2.7, 9.6**

  - [~] 15.4 Write property test for no source code transmission
    - **Property 33: No Source Code Transmission**
    - **Validates: Requirements 9.5**

  - [~] 15.5 Write unit tests for save-context
    - Test with uncommitted changes
    - Test without uncommitted changes
    - Test with network unavailable (offline mode)
    - Test secret redaction with various patterns
    - Test error handling
    - _Requirements: 2.5, 2.7, 8.1, 8.2_

- [ ] 16. Implement show-context command
  - [~] 16.1 Create show-context command handler
    - Detect current repository and branch
    - Support optional --branch parameter
    - Support optional --timestamp parameter for historical snapshots
    - Retrieve context from API or local cache
    - Format and display context sections in order
    - Include links to relevant files
    - Include links to PRs and issues (if GitHub metadata present)
    - Display "no saved context" message if not found
    - _Requirements: 5.2, 5.3, 5.4, 5.8, 6.2, 12.4_

  - [~] 16.2 Implement context display formatting
    - Format sections in order: Goals, Rationale, Open Questions, Next Steps
    - Format file links as clickable paths
    - Format PR/issue links as GitHub URLs
    - Use rich terminal formatting for readability
    - _Requirements: 3.8, 10.4_

  - [~] 16.3 Write property tests for context display
    - **Property 8: Snapshot Display Order**
    - **Property 16: Complete Context Display**
    - **Property 36: GitHub Link Generation**
    - **Validates: Requirements 3.8, 5.2, 5.3, 5.4, 10.4**

  - [~] 16.4 Write unit tests for show-context
    - Test display with complete context
    - Test display with missing PR/issue data
    - Test display with no context found
    - Test historical snapshot retrieval
    - _Requirements: 5.8, 12.4_


- [ ] 17. Implement list-contexts and history commands
  - [~] 17.1 Create list-contexts command handler
    - Detect current repository
    - Query API for all contexts in repository
    - Display list with timestamps and summaries
    - Support pagination with --limit and --next-token
    - _Requirements: 6.3, 12.6_

  - [~] 17.2 Create history command handler
    - Detect current repository and branch
    - Support optional --branch parameter
    - Query API for branch-specific contexts
    - Display chronological list (most recent first)
    - Show timestamps and truncated summaries
    - Default limit to 20 snapshots
    - Support pagination
    - _Requirements: 12.1, 12.2, 12.3, 12.5, 12.6_

  - [~] 17.3 Write property tests for history
    - **Property 41: Chronological Snapshot Ordering**
    - **Property 42: History Display Completeness**
    - **Property 43: Default History Limit**
    - **Property 44: History Pagination**
    - **Validates: Requirements 12.1, 12.3, 12.5, 12.6**

  - [~] 17.4 Write unit tests for list and history commands
    - Test with multiple snapshots
    - Test with empty results
    - Test pagination
    - Test branch filtering
    - _Requirements: 11.2, 12.1, 12.5_

- [ ] 18. Implement delete-context command
  - [~] 18.1 Create delete-context command handler
    - Accept snapshot_id as parameter
    - Call API to soft-delete snapshot
    - Display confirmation with purge deadline
    - Handle errors (not found, network failure)
    - _Requirements: 6.6, 9.4_

  - [~] 18.2 Write property test for deletion irreversibility
    - **Property 70: Deletion Irreversibility Semantics**
    - **Validates: Requirements 9.4**

  - [~] 18.3 Write unit tests for delete-context
    - Test successful deletion
    - Test deletion of non-existent snapshot
    - Test offline mode (queue deletion)

- [~] 19. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 20. Implement automatic context restoration
  - [~] 20.1 Create branch switch detection mechanism
    - Implement _hook-branch-switch internal command for git hooks
    - Implement fallback branch detection on CLI invocation
    - Store last known branch in local state
    - Detect branch changes when hooks unavailable
    - _Requirements: 5.6, 5.7_

  - [~] 20.2 Implement automatic context display on branch switch
    - Trigger show-context automatically on branch switch
    - Retrieve latest context for new branch
    - Display context or "no saved context" message
    - Complete restoration within 2 seconds
    - _Requirements: 5.1, 5.5, 5.8_

  - [~] 20.3 Write property tests for restoration
    - **Property 15: Latest Snapshot Retrieval**
    - **Property 17: Fallback Branch Detection**
    - **Property 60: Primary Branch-Switch Detection Path**
    - **Property 61: No-Context Branch Message**
    - **Validates: Requirements 5.1, 5.6, 5.7, 5.8**

  - [~] 20.4 Write unit tests for automatic restoration
    - Test hook-triggered restoration
    - Test fallback detection
    - Test with no saved context
    - Test performance with large snapshot counts
    - _Requirements: 5.5, 5.6, 5.7, 13.6_

- [ ] 21. Implement metrics and instrumentation
  - [~] 21.1 Create MetricsCollector class
    - Implement event emission for context_capture_started, context_capture_completed, context_capture_failed
    - Implement event emission for context_restored, context_restore_failed
    - Implement event emission for resume_session_started
    - Implement event emission for first_productive_action
    - Store events in local SQLite database
    - _Requirements: 16.1, 16.2, 16.3_

  - [~] 21.2 Implement time-to-productivity calculation
    - Implement calculate_time_to_productivity method
    - Track resume_session_started events
    - Track first_productive_action events (commit, staged change)
    - Calculate duration between events
    - _Requirements: 16.4_

  - [~] 21.3 Create metrics export command
    - Implement export-metrics command
    - Support JSON and CSV output formats
    - Include timestamps for all events
    - Calculate and include time-to-productivity metrics
    - _Requirements: 16.5_

  - [~] 21.4 Write property tests for metrics
    - **Property 50: Event Emission for Operations**
    - **Property 51: Resume Session Event**
    - **Property 53: Time to Productivity Calculation**
    - **Property 87: Metrics Export Formats**
    - **Validates: Requirements 16.1, 16.2, 16.4, 16.5**

  - [~] 21.5 Write unit tests for metrics
    - Test event emission
    - Test time-to-productivity calculation
    - Test export in JSON format
    - Test export in CSV format
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_


- [ ] 22. Implement error handling and logging
  - [~] 22.1 Create error handling infrastructure
    - Implement error categories (Network, Git, Data, User)
    - Implement error logging to ~/.contextanchor/logs/contextanchor.log
    - Implement log rotation (10MB max, keep 5 files)
    - Add timestamps and context to all log entries
    - _Requirements: 8.5_

  - [~] 22.2 Implement graceful degradation
    - Handle Context_Store unavailable (cache locally)
    - Handle Agent_Core unavailable (store raw signals)
    - Handle GitHub API unavailable (continue without metadata)
    - Handle git command failures (log and continue)
    - _Requirements: 8.1, 8.2, 8.3, 10.5_

  - [~] 22.3 Write property tests for error handling
    - **Property 24: Offline Context Caching**
    - **Property 25: Graceful Agent Core Degradation**
    - **Property 26: Git Operation Error Resilience**
    - **Property 27: Network Failure Operation Queuing**
    - **Property 28: Error Logging with Timestamps**
    - **Property 31: Offline Mode Functionality**
    - **Property 37: GitHub Rate Limit Resilience**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.8, 10.5**

  - [~] 22.4 Write unit tests for error scenarios
    - Test network unavailable scenarios
    - Test git command failures
    - Test invalid data handling
    - Test log file creation and rotation
    - _Requirements: 8.1, 8.2, 8.3, 8.5_

- [ ] 23. Implement CLI user experience enhancements
  - [~] 23.1 Add command validation and help
    - Implement invalid command detection
    - Display usage help for invalid commands
    - Add --help flag to all commands
    - _Requirements: 6.4_

  - [~] 23.2 Add status indicators for long operations
    - Implement spinner for operations > 1 second
    - Update status every 2 seconds
    - Show progress for API calls
    - _Requirements: 13.5_

  - [~] 23.3 Implement repository detection from subdirectories
    - Detect repository root from any subdirectory
    - Display error when executed outside repository
    - _Requirements: 6.5, 11.5_

  - [~] 23.4 Write property tests for CLI behavior
    - **Property 18: Invalid Command Help Display**
    - **Property 19: Repository-Relative Command Execution**
    - **Property 45: Long Operation Status Updates**
    - **Property 72: Outside-Repository Execution Guard**
    - **Validates: Requirements 6.4, 6.5, 11.5, 13.5**

  - [~] 23.5 Write unit tests for CLI UX
    - Test help display
    - Test repository detection
    - Test status indicators
    - Test error messages
    - _Requirements: 6.4, 6.5, 11.5_

- [~] 24. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 25. Implement multi-repository support
  - [~] 25.1 Enhance repository identification
    - Implement repository_id generation with remote URL and path hash
    - Ensure unique IDs for same folder name with different remotes
    - Store repository metadata in local database
    - _Requirements: 11.6_

  - [~] 25.2 Implement repository isolation
    - Filter list-contexts by current repository
    - Filter history by current repository
    - Ensure Context_Store queries include repository_id
    - _Requirements: 11.2, 11.3_

  - [~] 25.3 Write property tests for multi-repository support
    - **Property 38: Repository Isolation**
    - **Property 39: Repository Detection from Working Directory**
    - **Property 40: Repository Identifier Uniqueness**
    - **Property 71: Simultaneous Multi-Repository Monitoring**
    - **Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.6**

  - [~] 25.4 Write unit tests for multi-repository scenarios
    - Test with multiple initialized repositories
    - Test repository ID collision scenarios
    - Test context isolation between repositories
    - _Requirements: 11.1, 11.2, 11.3, 11.6_

- [ ] 26. Implement security and privacy features
  - [~] 26.1 Implement encryption configuration
    - Configure DynamoDB encryption at rest (AES-256)
    - Configure TLS 1.3 for API client
    - Validate certificate chains
    - _Requirements: 9.1, 9.2_

  - [~] 26.2 Implement developer-scoped access
    - Store developer_id with each snapshot
    - Filter queries by developer_id
    - Implement API key management
    - _Requirements: 9.3_

  - [~] 26.3 Write property tests for security
    - **Property 68: Encryption at Rest Enforcement**
    - **Property 69: Encryption in Transit Enforcement**
    - **Validates: Requirements 9.1, 9.2**

  - [~] 26.4 Write unit tests for privacy features
    - Test source code exclusion from transmitted data
    - Test secret redaction
    - Test developer-scoped queries
    - _Requirements: 9.3, 9.5, 9.6_


- [ ] 27. Implement Hypothesis property-based test infrastructure
  - [~] 27.1 Create Hypothesis strategies for domain models
    - Implement context_snapshots strategy with valid field generation
    - Implement action_verbs_text strategy for next steps
    - Implement file_paths strategy for relevant files
    - Implement capture_signals strategy
    - Configure minimum 100 iterations per property test
    - _Requirements: All property tests_

  - [~] 27.2 Configure property test execution
    - Set up pytest configuration for Hypothesis
    - Configure deterministic seed for CI/CD
    - Set up test tagging with property references
    - Create test fixtures for common scenarios
    - _Requirements: All property tests_

  - [~] 27.3 Write remaining property tests not covered in component tasks
    - **Property 13: Retention Period Enforcement**
    - **Property 22: Initialization Failure Error Messages**
    - **Property 23: Hook Status Reporting**
    - **Property 52: Productive Action Timestamp Recording**
    - **Property 62-66: Command Availability Properties**
    - **Property 73: history Command Availability**
    - **Property 74: Timestamped Historical Snapshot Retrieval**
    - **Property 86: Configuration File Support**
    - **Validates: Requirements 4.4, 6.1, 6.2, 6.3, 6.6, 7.5, 7.6, 12.2, 12.4, 15.1, 16.3**

- [ ] 28. Write integration tests
  - [~] 28.1 Create end-to-end capture flow test
    - Test full flow: init → save-context → verify storage
    - Use temporary git repository
    - Mock AWS services with moto
    - Verify all components work together
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 4.1_

  - [~] 28.2 Create end-to-end restoration flow test
    - Test full flow: save-context → switch branch → restore context
    - Verify automatic restoration triggers
    - Verify context display formatting
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.6_

  - [~] 28.3 Create offline sync flow test
    - Test save-context while offline
    - Verify local queueing
    - Simulate connectivity restoration
    - Verify sync with exponential backoff
    - _Requirements: 8.1, 8.4, 8.7_

  - [~] 28.4 Create multi-repository integration test
    - Initialize multiple repositories
    - Save contexts in each repository
    - Verify isolation between repositories
    - _Requirements: 11.1, 11.2, 11.3_

- [~] 29. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 30. Implement performance optimizations
  - [~] 30.1 Optimize CLI startup time
    - Lazy load heavy dependencies
    - Cache repository detection results
    - Optimize import statements
    - Target < 500ms command dispatch at p95
    - _Requirements: 13.2_

  - [~] 30.2 Optimize git hook overhead
    - Make hook execution asynchronous
    - Minimize hook script size
    - Target < 50ms overhead at p95
    - _Requirements: 13.3_

  - [~] 30.3 Optimize context restoration performance
    - Implement local caching for recent contexts
    - Optimize DynamoDB query patterns
    - Target < 2 seconds restoration at p95 with 10,000 snapshots
    - _Requirements: 5.5, 13.6_

  - [~] 30.4 Implement async processing for AI synthesis
    - Make Bedrock calls asynchronous
    - Return CLI acknowledgement immediately
    - Target < 300ms acknowledgement at p95
    - _Requirements: 13.4_

  - [~] 30.5 Write performance benchmark tests
    - Benchmark CLI dispatch latency
    - Benchmark git hook overhead
    - Benchmark context restoration with large datasets
    - Benchmark memory usage during monitoring
    - Note: These are benchmarks, not pass/fail tests
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

- [ ] 31. Create deployment and packaging
  - [~] 31.1 Create Python package configuration
    - Configure pyproject.toml with package metadata
    - Define entry points for CLI commands
    - Specify dependencies with version constraints
    - Configure build system (setuptools or poetry)
    - _Requirements: 6.1, 6.2, 6.3, 6.6_

  - [~] 31.2 Create CDK deployment scripts
    - Create cdk.json configuration
    - Create deployment script for AWS resources
    - Document deployment prerequisites
    - Create teardown script for cleanup
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_

  - [~] 31.3 Create installation documentation
    - Document Python version requirements (3.11+)
    - Document AWS account setup
    - Document pip installation process
    - Document CDK deployment process
    - Document API key configuration
    - _Requirements: 7.1, 14.1, 14.2, 14.3, 14.4_


- [ ] 32. Create user documentation
  - [~] 32.1 Create getting started guide
    - Document installation steps
    - Document repository initialization
    - Document basic workflow (save, restore, list)
    - Include example commands and outputs
    - _Requirements: 6.1, 6.2, 6.3, 7.1_

  - [~] 32.2 Create command reference documentation
    - Document all CLI commands with parameters
    - Document configuration file format
    - Document environment variables
    - Include troubleshooting section
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.6, 7.1, 12.2, 15.1_

  - [~] 32.3 Create architecture documentation
    - Document system components and interactions
    - Document data flow patterns
    - Document AWS resource usage
    - Document privacy and security features
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 14.1, 14.2, 14.3, 14.4_

- [ ] 33. Final integration and validation
  - [~] 33.1 Run complete test suite
    - Run all unit tests with coverage report (target 80%+)
    - Run all property-based tests (100 iterations)
    - Run all integration tests
    - Fix any failing tests
    - _Requirements: All_

  - [~] 33.2 Run code quality checks
    - Run black formatter
    - Run flake8 linter
    - Run mypy type checker
    - Run bandit security scanner
    - Fix all issues
    - _Requirements: 9.1, 9.2, 9.5, 9.6_

  - [~] 33.3 Perform end-to-end manual testing
    - Test complete workflow in real repository
    - Test offline mode and sync
    - Test multi-repository scenarios
    - Test error scenarios
    - Verify performance targets
    - _Requirements: All_

  - [~] 33.4 Deploy to test AWS environment
    - Deploy CDK stack to test account
    - Verify all AWS resources created correctly
    - Test CLI against deployed API
    - Verify cost guardrails configured
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_

- [~] 34. Final checkpoint - Ensure all tests pass and system is ready
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks in this plan are required for delivery quality and completion.
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties with Hypothesis (minimum 100 iterations)
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end flows
- All property tests are annotated with property numbers and requirement references
- Python 3.11+ is the implementation language for all components
- AWS CDK (Python) is used for infrastructure as code
- The system is designed to stay within AWS Free Tier limits with cost guardrails
