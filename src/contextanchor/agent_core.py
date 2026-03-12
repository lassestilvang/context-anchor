"""
Agent Core component for interacting with AWS Bedrock to synthesize contexts.
"""

import json
from typing import Dict, Any, List, cast
import boto3
from datetime import datetime, UTC

from .models import ContextSnapshot, CaptureSignals, generate_snapshot_id
from .privacy import PrivacyFilter


class AgentCore:
    def __init__(self, bedrock_client: Any = None) -> None:
        import os
        self.bedrock = bedrock_client or boto3.client("bedrock-runtime")
        # Ensure we always get the latest from environment
        self.model_id = os.environ.get(
            "BEDROCK_MODEL_ID", "eu.anthropic.claude-haiku-4-5-20251001-v1:0"
        )
        self.privacy_filter = PrivacyFilter()

    def synthesize_context(
        self,
        repository_id: str,
        branch: str,
        developer_id: str,
        intent: str,
        signals: CaptureSignals,
    ) -> ContextSnapshot:
        """
        Synthesize a context snapshot from developer intent and git signals.
        """
        prompt = self._build_bedrock_prompt(intent, signals)

        try:
            response_text = self._invoke_bedrock(prompt)
            parsed_data = self._parse_bedrock_response(response_text)

            snapshot = ContextSnapshot(
                snapshot_id=generate_snapshot_id(),
                repository_id=repository_id,
                branch=branch,
                captured_at=datetime.now(UTC),
                developer_id=developer_id,
                goals=self.privacy_filter.apply(parsed_data.get("goals", "")),
                rationale=self.privacy_filter.apply(parsed_data.get("rationale", "")),
                open_questions=[
                    self.privacy_filter.apply(q) for q in parsed_data.get("open_questions", [])
                ],
                next_steps=[
                    self.privacy_filter.apply(s) for s in parsed_data.get("next_steps", [])
                ],
                relevant_files=self._extract_relevant_files(signals),
                related_prs=signals.pr_references,
                related_issues=signals.issue_references,
                github_metadata=signals.github_metadata,
            )

            # ContextSnapshot's __post_init__ will validate the schema compliance here
            return snapshot

        except Exception as e:
            raise ValueError(f"Failed to synthesize context or validation failed: {str(e)}")

    def _build_bedrock_prompt(self, intent: str, signals: CaptureSignals) -> str:
        """Construct the prompt payload for Bedrock."""
        system_prompt = """You are ContextAnchor, an AI assistant analyzing developer workflows.
Synthesize a structured summary of the developer's current context based on their stated intent and git signals.
Your response MUST be strict JSON with the following keys:
- "goals": string, what the developer is trying to accomplish
- "rationale": string, why this work matters
- "open_questions": list of strings, unresolved questions or decisions
- "next_steps": list of strings, concrete action items (1 to 5 items)

CRITICAL CONSTRAINTS:
1. Total text must be under 500 words.
2. Every item in "next_steps" MUST start with a valid action verb from this list: add, update, fix, remove, refactor, test, document, implement, create, verify, investigate, optimize, migrate, review, ship, develop.
"""

        signals_dict = {
            "uncommitted_files": [
                {"path": fc.path, "status": fc.status} for fc in signals.uncommitted_files
            ],
            "recent_commits": [
                {"message": c.message, "files": c.files_changed} for c in signals.recent_commits
            ],
        }

        user_message = f"Developer Intent:\n{self.privacy_filter.apply(intent)}\n\nGit Signals:\n{json.dumps(signals_dict, indent=2)}\n\nSynthesize the context into the requested JSON format."

        # Nova expects a slightly different Converse API format if using invoke_model directly with Nova IDs
        is_nova = "nova" in self.model_id.lower()
        is_llama = "llama" in self.model_id.lower()

        payload: Dict[str, Any]

        if is_nova:
            payload = {
                "inferenceConfig": {
                    "max_new_tokens": 1000,
                    "temperature": 0.1
                },
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"text": f"System: {system_prompt}\n\nUser: {user_message}"}
                        ]
                    }
                ]
            }
            return json.dumps(payload)

        # Llama 3.2
        if is_llama:
            payload = {
                "prompt": f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{user_message}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
                "max_gen_len": 1000,
                "temperature": 0.1,
            }
            return json.dumps(payload)

        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": [{"type": "text", "text": user_message}]}],
        }
        return json.dumps(payload)

    def _invoke_bedrock(self, prompt: str) -> str:
        """Invoke the Bedrock model."""
        response = self.bedrock.invoke_model(modelId=self.model_id, body=prompt)
        response_body = json.loads(response.get("body").read())

        # Support Claude, Nova, and Llama response formats
        if "content" in response_body:
            return str(response_body["content"][0]["text"])
        elif "output" in response_body and "message" in response_body["output"]:
            return str(response_body["output"]["message"]["content"][0]["text"])
        elif "generation" in response_body:
            return str(response_body["generation"])
        return str(response_body)

    def _parse_bedrock_response(self, response_text: str) -> Dict[str, Any]:
        """Extract and parse JSON from the Bedrock response."""
        try:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start != -1 and end != 0:
                json_str = response_text[start:end]
                return cast(Dict[str, Any], json.loads(json_str))
            return cast(Dict[str, Any], json.loads(response_text))
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse Bedrock response as JSON: {response_text}")

    def _extract_relevant_files(self, signals: CaptureSignals) -> List[str]:
        """Extract all relevant files from signals."""
        files = set()
        for fc in signals.uncommitted_files:
            files.add(fc.path)
        for c in signals.recent_commits:
            for f in c.files_changed:
                files.add(f)
        return sorted(list(files))

    def synthesize_context_async(
        self,
        repository_id: str,
        branch: str,
        developer_id: str,
        intent: str,
        signals: CaptureSignals,
        callback: Any = None,
    ) -> None:
        """
        Synthesize context asynchronously in a background thread.

        Returns immediately after launching the background task. The CLI
        can acknowledge the save request in <300ms while synthesis continues.

        Args:
            callback: Optional callable(snapshot) invoked when synthesis completes.
        """
        import threading

        def _run() -> None:
            try:
                snapshot = self.synthesize_context(
                    repository_id, branch, developer_id, intent, signals
                )
                if callback:
                    callback(snapshot)
            except Exception:  # nosec
                pass  # Background failures are logged, not raised

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
