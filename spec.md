# ContextAnchor

## Idea

ContextAnchor eliminates the hidden tax of context switching and is an Al agent that acts as a "save state" for your workflow. It monitors git activity and allows developers to capture intent with a one-command "brain dump" before switching tasks. When you return, it instantly restores what you were solving, why, and what's next - eliminating the hidden "re-learning tax" of context switching. Al-powered memory for developers who juggle multiple projects.

## Vision

I will build a lightweight agent that observes developer activity - git commits, diffs, branches, and related PRs - and maintains a persistent, project-specific memory of what a developer was working on, why certain decisions were made, and what remains unresolved.

The core feature is intentional context capture. Before switching tasks or branches, a developer can run a simple command e.g. "save-context". The agent analyzes uncommitted changes and recent activity, then asks a single prompt: "What were you trying to solve right now?" This combines passive signals with explicit human intent to create a high-fidelity snapshot of the developer's mental state.

When the developer returns to a project, the agent automatically restores this context: a concise summary of goals, rationale, open questions, relevant files, and next steps. This enables developers to resume work instantly and dramatically reduce context-switching overhead.

## Game Plan

Build a focused, production-quality MVP that demonstrates clear value with minimal complexity.

### Phase 1: Core Context Capture
I will build a CLI tool and GitHub integration that observe git activity - commits, branches, diffs, PR references - and store project-scoped context. A save-context command will allow developers to intentionally capture intent. The agent analyzes uncommitted changes and asks a single reflective prompt to enrich the context snapshot.

### Phase 2: Agent Reasoning and Memory
Using Amazon Bedrock, the agent will synthesize raw signals and human input into concise "mental state" summaries: goals, rationale, open questions, and next steps. These snapshots will be stored in DynamoDB as durable, resumable project memory. Strands Agents or Bedrock AgentCore will orchestrate observation, summarization, and retrieval.

### Phase 3: Context Restoration
When a developer switches branches or returns to a repository, the agent automatically surfaces the latest saved context via CLI output or a lightweight notification. This includes links to relevant files, PRs,
and issues.

### Phase 4: Validation and Metrics
I will validate impact by measuring time-to-productivity after context switches and collecting qualitative developer feedback. All components will be built using AWS serverless services - API Gateway, Lambda, DynamoDB, S3 - to stay within Free Tier limits while demonstrating scalability and real-world
applicability.