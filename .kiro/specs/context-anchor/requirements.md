# Requirements Document

## Introduction

ContextAnchor is a developer workflow state manager that eliminates the hidden tax of context switching. It monitors git activity and enables developers to capture their mental state before switching tasks, then instantly restores that context when they return. The system combines passive observation of git operations with explicit intent capture to create high-fidelity snapshots of developer workflow state.

## Priority Model

All requirements remain in a single unified structure. Each requirement has a priority label to guide implementation sequencing without splitting the document into separate phases.

- **MUST**: Required for core product value and baseline reliability/security
- **SHOULD**: Important for production readiness and strong user experience
- **COULD**: Valuable enhancement that can follow after core delivery

## Spec Traceability

| Source in spec.md | Covered by requirements |
| --- | --- |
| Idea: monitor git activity, capture brain dump, restore instantly | R1, R2, R3, R5, R6 |
| Vision: persistent project-specific memory with rationale and unresolved items | R3, R4, R11, R12 |
| Vision: save-context prompt and intent enrichment | R2 |
| Vision: restored goals/rationale/open questions/next steps with relevant files/PRs/issues | R3, R5, R10 |
| Phase 1: CLI + git + GitHub integration | R1, R2, R6, R7, R10 |
| Phase 2: Bedrock synthesis + DynamoDB memory | R3, R4, R14 |
| Phase 3: automatic restoration on return/branch switch | R5 |
| Phase 4: validation and time-to-productivity impact measurement | R13, R16 |

## Glossary

- **ContextAnchor**: The complete developer workflow state management system
- **CLI_Tool**: Command-line interface for developer interaction
- **Context_Snapshot**: A stored representation of developer mental state including goals, rationale, open questions, and next steps
- **Git_Observer**: Component that monitors git operations (commits, branches, diffs, PRs)
- **Context_Store**: Persistent storage system for context snapshots (DynamoDB)
- **Agent_Core**: AI reasoning component that synthesizes signals into summaries (Amazon Bedrock)
- **Repository**: A git repository being monitored
- **Developer**: User of the ContextAnchor system
- **Uncommitted_Changes**: Modified files not yet committed to git
- **Branch**: A git branch within a repository
- **Context_Restoration**: Process of surfacing saved context when returning to work

## Requirements

### Requirement 1: Git Activity Monitoring

**Priority:** MUST

**User Story:** As a developer, I want the system to observe my git activity, so that it can build context from my actual work patterns.

#### Acceptance Criteria

1. WHEN a commit is created in a monitored Repository, THE Git_Observer SHALL capture the commit hash, message, timestamp, and changed files
2. WHEN a branch switch occurs in a monitored Repository, THE Git_Observer SHALL record the source branch, target branch, and timestamp
3. WHEN a diff is generated in a monitored Repository, THE Git_Observer SHALL capture the file paths and change summary
4. WHERE a PR reference exists in commit messages, THE Git_Observer SHALL extract and store the PR identifier
5. THE Git_Observer SHALL associate all captured activity with the specific Repository identifier
6. WHEN git activity is captured, THE Git_Observer SHALL record the capture source (hook, CLI fallback, or background watcher) for diagnostics

### Requirement 2: Intentional Context Capture

**Priority:** MUST

**User Story:** As a developer, I want to save my current mental state before switching tasks, so that I can resume work efficiently later.

#### Acceptance Criteria

1. WHEN a developer executes the save-context command, THE CLI_Tool SHALL analyze Uncommitted_Changes in the current Repository
2. WHEN the save-context command is executed, THE CLI_Tool SHALL prompt the developer with "What were you trying to solve right now?"
3. WHEN the developer provides a response to the prompt, THE CLI_Tool SHALL combine the response with git activity signals
4. WHEN context capture is initiated, THE CLI_Tool SHALL identify relevant files from recent git activity
5. THE CLI_Tool SHALL complete context capture within 5 seconds of receiving developer input
6. WHEN context capture is initiated, THE CLI_Tool SHALL include both unstaged and staged file metadata in the signal set
7. WHEN no uncommitted changes are present, THE CLI_Tool SHALL still allow intent capture and persist a Context_Snapshot

### Requirement 3: Context Snapshot Creation

**Priority:** MUST

**User Story:** As a developer, I want my workflow state synthesized into a clear summary, so that I can quickly understand where I left off.

#### Acceptance Criteria

1. WHEN raw signals and developer input are received, THE Agent_Core SHALL generate a Context_Snapshot containing goals, rationale, open questions, and next steps
2. WHEN generating a Context_Snapshot, THE Agent_Core SHALL include references to relevant files from git activity
3. WHEN generating a Context_Snapshot, THE Agent_Core SHALL include the current Branch name
4. WHEN generating a Context_Snapshot, THE Agent_Core SHALL include timestamp of capture
5. THE Agent_Core SHALL generate Context_Snapshots within 3 seconds of receiving input
6. THE Agent_Core SHALL limit Context_Snapshot summaries to 500 words maximum
7. THE Context_Snapshot schema SHALL include required fields: snapshot_id, repository_id, branch, captured_at, goals, rationale, open_questions, next_steps, relevant_files, related_prs, and related_issues
8. WHEN rendering a Context_Snapshot for display, THE CLI_Tool SHALL present sections in fixed order: Goals, Rationale, Open Questions, Next Steps
9. THE Agent_Core SHALL output between 1 and 5 Next Steps, and each step SHALL begin with an action verb

### Requirement 4: Context Persistence

**Priority:** MUST

**User Story:** As a developer, I want my context snapshots stored reliably, so that I can access them across sessions and machines.

#### Acceptance Criteria

1. WHEN a Context_Snapshot is created, THE Context_Store SHALL persist it with a unique identifier
2. WHEN storing a Context_Snapshot, THE Context_Store SHALL index it by Repository identifier and Branch name
3. WHEN storing a Context_Snapshot, THE Context_Store SHALL index it by timestamp
4. THE Context_Store SHALL retain Context_Snapshots for at least 90 days
5. WHEN a Context_Snapshot is requested, THE Context_Store SHALL retrieve it within 200 milliseconds at p95 for repositories with up to 10,000 snapshots
6. THE Context_Store SHALL support soft-delete retention of 7 days before permanent purge for recovery from accidental deletion

### Requirement 5: Automatic Context Restoration

**Priority:** MUST

**User Story:** As a developer, I want context automatically restored when I return to a project, so that I can resume work without manual effort.

#### Acceptance Criteria

1. WHEN a developer switches to a Branch with saved context, THE CLI_Tool SHALL retrieve the most recent Context_Snapshot for that Branch
2. WHEN a Context_Snapshot is retrieved, THE CLI_Tool SHALL display the goals, rationale, open questions, and next steps
3. WHEN displaying restored context, THE CLI_Tool SHALL include links to relevant files
4. WHERE PR references exist in the Context_Snapshot, THE CLI_Tool SHALL include links to those PRs
5. THE CLI_Tool SHALL complete context restoration within 2 seconds of branch switch detection
6. THE CLI_Tool SHALL detect branch switches automatically using a git post-checkout hook where repository permissions allow hook installation
7. WHEN hook installation is unavailable or disabled, THE CLI_Tool SHALL detect branch changes on the next CLI invocation and surface context at that time
8. WHEN no Context_Snapshot exists for the current Branch, THE CLI_Tool SHALL display a clear "no saved context" message and suggest save-context

### Requirement 6: CLI Command Interface

**Priority:** MUST

**User Story:** As a developer, I want simple commands to interact with ContextAnchor, so that it integrates seamlessly into my workflow.

#### Acceptance Criteria

1. THE CLI_Tool SHALL provide a save-context command that initiates context capture
2. THE CLI_Tool SHALL provide a show-context command that displays the current Branch context
3. THE CLI_Tool SHALL provide a list-contexts command that shows all saved contexts for the current Repository
4. WHEN an invalid command is entered, THE CLI_Tool SHALL display usage help within 100 milliseconds
5. THE CLI_Tool SHALL operate from any directory within a monitored Repository
6. THE CLI_Tool SHALL provide a delete-context command that permanently removes a specified Context_Snapshot

### Requirement 7: Repository Initialization

**Priority:** MUST

**User Story:** As a developer, I want to enable ContextAnchor for specific repositories, so that I control which projects are monitored.

#### Acceptance Criteria

1. THE CLI_Tool SHALL provide an init command that enables monitoring for the current Repository
2. WHEN the init command is executed, THE CLI_Tool SHALL create a configuration file in the Repository
3. WHEN the init command is executed in an already initialized Repository, THE CLI_Tool SHALL display a message indicating the Repository is already initialized
4. THE CLI_Tool SHALL verify git is available before initializing a Repository
5. WHEN initialization fails, THE CLI_Tool SHALL display a descriptive error message
6. WHEN initialization succeeds, THE CLI_Tool SHALL report whether automatic branch-switch detection is active, degraded, or unavailable

### Requirement 8: Error Handling and Recovery

**Priority:** MUST

**User Story:** As a developer, I want clear error messages when something goes wrong, so that I can resolve issues quickly.

#### Acceptance Criteria

1. WHEN the Context_Store is unavailable, THE CLI_Tool SHALL display an error message and cache the Context_Snapshot locally
2. WHEN the Agent_Core is unavailable, THE CLI_Tool SHALL store raw signals without AI summarization
3. WHEN git operations fail, THE CLI_Tool SHALL log the error and continue operation
4. WHEN network connectivity is lost, THE CLI_Tool SHALL queue operations for retry when connectivity is restored
5. THE CLI_Tool SHALL log all errors to a local log file with timestamps
6. THE CLI_Tool SHALL store at least 200 queued offline operations per Repository before applying backpressure controls
7. WHEN retrying queued operations, THE CLI_Tool SHALL use exponential backoff and stop after 24 hours with a surfaced recovery message
8. WHEN in offline mode, THE CLI_Tool SHALL continue to support save-context and local history operations

### Requirement 9: Privacy and Security

**Priority:** MUST

**User Story:** As a developer, I want my code and context data protected, so that sensitive information remains secure.

#### Acceptance Criteria

1. THE Context_Store SHALL encrypt Context_Snapshots at rest using AES-256 encryption
2. THE CLI_Tool SHALL encrypt data in transit using TLS 1.3 or higher
3. THE ContextAnchor SHALL store Context_Snapshots scoped to the authenticated Developer
4. THE CLI_Tool SHALL provide a delete-context command that permanently removes a Context_Snapshot
5. THE ContextAnchor SHALL NOT transmit source code content to external services, and SHALL limit transmitted git metadata to repository identifier, branch, file paths, file status, line-change counts, commit hashes, and commit messages
6. THE CLI_Tool SHALL redact secrets matching configured token patterns from developer free-text input before external transmission

### Requirement 10: GitHub Integration

**Priority:** SHOULD

**User Story:** As a developer, I want ContextAnchor to understand my GitHub workflow, so that it can include PR and issue context.

#### Acceptance Criteria

1. WHERE a Repository has a GitHub remote, THE Git_Observer SHALL extract the repository owner and name
2. WHEN a commit message contains a PR reference (e.g., #123), THE Git_Observer SHALL store the PR number
3. WHEN a commit message contains an issue reference (e.g., fixes #456), THE Git_Observer SHALL store the issue number
4. WHERE GitHub integration is configured, THE CLI_Tool SHALL include PR and issue links in restored context
5. WHEN GitHub API rate limits are exceeded, THE CLI_Tool SHALL continue operation without GitHub metadata
6. THE Git_Observer SHALL correctly parse PR and issue references from keywords including fixes, closes, resolves, and refs

### Requirement 11: Multi-Repository Support

**Priority:** SHOULD

**User Story:** As a developer, I want to use ContextAnchor across multiple projects, so that I can manage context for all my work.

#### Acceptance Criteria

1. THE ContextAnchor SHALL support monitoring multiple Repositories simultaneously
2. WHEN listing contexts, THE CLI_Tool SHALL filter results to the current Repository
3. THE Context_Store SHALL isolate Context_Snapshots by Repository identifier
4. THE CLI_Tool SHALL detect the current Repository from the working directory
5. WHEN executed outside a Repository, THE CLI_Tool SHALL display an error message indicating no Repository is detected
6. WHEN Repository identifiers collide by folder name, THE ContextAnchor SHALL disambiguate using canonical git remote URL and root path hash

### Requirement 12: Context History and Versioning

**Priority:** SHOULD

**User Story:** As a developer, I want to access previous context snapshots, so that I can review my thought process over time.

#### Acceptance Criteria

1. THE Context_Store SHALL maintain all Context_Snapshots for a Branch in chronological order
2. THE CLI_Tool SHALL provide a history command that displays past Context_Snapshots for the current Branch
3. WHEN displaying history, THE CLI_Tool SHALL show timestamps and truncated summaries
4. THE CLI_Tool SHALL provide a show-context command with a timestamp parameter to view specific historical snapshots
5. THE CLI_Tool SHALL limit history display to the 20 most recent Context_Snapshots by default
6. THE CLI_Tool SHALL allow pagination for history beyond the default 20 most recent snapshots

### Requirement 13: Lightweight Performance

**Priority:** SHOULD

**User Story:** As a developer, I want ContextAnchor to have minimal performance impact, so that it doesn't slow down my workflow.

#### Acceptance Criteria

1. THE Git_Observer SHALL consume less than 50MB of memory at p95 during a 60-minute run monitoring up to 3 Repositories
2. THE CLI_Tool SHALL start and complete command dispatch within 500 milliseconds at p95 on reference developer hardware
3. THE Git_Observer SHALL NOT block git operations and SHALL add no more than 50 milliseconds overhead to hook-triggered operations at p95
4. THE ContextAnchor SHALL use asynchronous processing for all AI summarization and SHALL return command acknowledgement within 300 milliseconds at p95
5. THE CLI_Tool SHALL provide a status indicator when operations exceed 1 second and refresh status at least every 2 seconds until completion
6. THE CLI_Tool SHALL complete automatic context restoration within 2 seconds at p95 for repositories with up to 10,000 snapshots

### Requirement 14: AWS Serverless Architecture

**Priority:** MUST

**User Story:** As a system operator, I want ContextAnchor built on AWS serverless services, so that it scales efficiently and stays within Free Tier limits.

#### Acceptance Criteria

1. THE Context_Store SHALL use DynamoDB for persistent storage
2. THE Agent_Core SHALL use Amazon Bedrock for AI reasoning
3. THE ContextAnchor SHALL use AWS Lambda for serverless compute
4. THE ContextAnchor SHALL use API Gateway for HTTP endpoints
5. WHERE file storage is needed, THE ContextAnchor SHALL use S3 with lifecycle policies to manage costs
6. THE deployment configuration SHALL define cost guardrails with alerts when monthly projected spend exceeds configured Free Tier thresholds

### Requirement 15: Configuration and Customization

**Priority:** COULD

**User Story:** As a developer, I want to customize ContextAnchor behavior, so that it fits my specific workflow needs.

#### Acceptance Criteria

1. THE CLI_Tool SHALL support a config file for user preferences
2. WHERE configured, THE CLI_Tool SHALL allow customization of the context capture prompt
3. WHERE configured, THE CLI_Tool SHALL allow customization of Context_Snapshot retention period
4. WHERE configured, THE CLI_Tool SHALL allow disabling of specific git activity monitoring
5. WHEN configuration is invalid, THE CLI_Tool SHALL display validation errors and use default values
6. THE CLI_Tool SHALL validate configuration against a published schema and report exact invalid fields

### Requirement 16: Validation and Metrics Instrumentation

**Priority:** SHOULD

**User Story:** As a system operator, I want measurable usage and productivity signals, so that I can validate whether ContextAnchor reduces context-switching overhead.

#### Acceptance Criteria

1. THE ContextAnchor SHALL emit events for context_capture_started, context_capture_completed, context_restored, and context_restore_failed
2. THE CLI_Tool SHALL emit a resume_session_started event when context is shown after repository return or branch switch
3. THE ContextAnchor SHALL record first_productive_action timestamps using configured proxies such as first commit, first staged change, or first task marker command
4. THE analytics layer SHALL compute time_to_productivity as duration between resume_session_started and first_productive_action
5. THE CLI_Tool SHALL provide a metrics export command that outputs timestamped measurements in JSON and CSV formats
