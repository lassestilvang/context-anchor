# ContextAnchor Architecture

ContextAnchor consists of two major components: a local CLI client and an AWS Serverless backend.

## System Components

### 1. Local CLI
- **Git Observer:** Hooks into `post-commit` and `post-checkout` events to capture state changes such as branch switches, code modifications, and commit messages.
- **Privacy Filter:** Runs locally to redact predefined secret patterns (like API keys) *before* data ever leaves your machine.
- **Local Storage:** Acts as an offline queue. If the API is unreachable, ContextAnchor stores the event locally and retries it later using exponential backoff.
- **API Client:** Handles secure TLS 1.3 communication with the AWS backend.

### 2. AWS Serverless Backend
- **API Gateway:** Provides secure REST endpoints for capturing and retrieving contexts.
- **Lambda (Agent Core):** Asynchronously processes captured signals (uncommitted diffs, commit messages). It calls **Amazon Bedrock** (Anthropic Claude 3 Haiku) to synthesize developer intent into goals, rationale, and next steps.
- **DynamoDB:** Stores context snapshots using a `Repository + Branch` partition/sort key design for high-performance retrieval. Data is encrypted at rest (AES-256).

## Data Flow: Context Capture

1. **Trigger:** Developer runs `contextanchor save-context` or a git hook fires.
2. **Collection:** CLI collects diffs and asks for developer intent.
3. **Redaction:** Secrets are scrubbed using regex patterns.
4. **Transmission:** CLI sends a POST request to API Gateway.
5. **Synthesis:** API Gateway triggers a Lambda function. The function delegates complex processing to a background Lambda event to keep the CLI responsive.
6. **AI Analysis:** The background Lambda invokes Amazon Bedrock to summarize the changes.
7. **Storage:** The synthesized context is stored in DynamoDB.

## Security & Privacy

ContextAnchor is built with privacy in mind:
- **No Source Code Uploads:** Only uncommitted diff paths and high-level commit messages are sent. The full source code is *never* uploaded.
- **Secret Redaction:** Customizable regex patterns ensure accidental API keys in intent messages are scrubbed.
- **Encryption:** All data in transit uses TLS 1.3. All data at rest in DynamoDB is encrypted using AES-256.
- **Developer Scoping:** Data is stored per developer and repository, ensuring clean isolation.

## AWS Resource Usage & Cost

The infrastructure is optimized to fit within the AWS Free Tier for small to medium usage:
- **Lambda:** Python 3.11 runtimes with small memory footprints.
- **DynamoDB:** On-demand billing mode with TTL (Time To Live) configured to automatically delete expired contexts (default: 30 days).
- **Bedrock:** The system uses the highly cost-efficient Claude 3 Haiku model.
