"""
Privacy and security filtering for ContextAnchor.

Provides redaction of secrets and stripping of sensitive source code
blocks before data is transmitted to the API.
"""

import re


class PrivacyFilter:
    """
    Filters and redacts sensitive information from context snapshots.
    """

    # Common secret patterns (API keys, tokens, etc.)
    SECRET_PATTERNS = [
        # AWS Access Key ID
        r"(?i)AKIA[0-9A-Z]{16}",
        # AWS Secret Access Key
        r"(?i)SECRET_ACCESS_KEY=['\"]?[0-9a-zA-Z/+=]{40}['\"]?",
        # GitHub Personal Access Token
        r"(?i)ghp_[0-9a-zA-Z]{36}",
        # Generic API Key/Token patterns
        r"(?i)(api[_-]?key|auth[_-]?token|secret|password|credential)['\"]?\s*[:=]\s*['\"]?[0-9a-zA-Z\-_/+=]{8,}['\"]?",
        # Stripe API Key
        r"(?i)sk_(live|test)_[0-9a-zA-Z]{24}",
    ]

    def __init__(self, redact_code: bool = True, max_code_lines: int = 50):
        """
        Initialize PrivacyFilter.

        Args:
            redact_code: Whether to strip large code blocks.
            max_code_lines: Maximum number of lines allowed in a code block.
        """
        self.redact_code = redact_code
        self.max_code_lines = max_code_lines
        self.compiled_patterns = [re.compile(p) for p in self.SECRET_PATTERNS]

    def redact_secrets(self, text: str) -> str:
        """
        Redact common secrets from the given text.

        Args:
            text: Input text potentially containing secrets.

        Returns:
            Redacted version of the text.
        """
        if not text:
            return text

        redacted = text
        for pattern in self.compiled_patterns:
            redacted = pattern.sub("[REDACTED]", redacted)

        return redacted

    def strip_code_blocks(self, text: str) -> str:
        """
        Identify and strip or truncate large source code blocks.

        Args:
            text: Input text potentially containing code blocks.

        Returns:
            Processed text with large code blocks truncated or removed.
        """
        if not self.redact_code or not text:
            return text

        # Simple heuristic for code blocks (markdown fences)
        def replace_block(match: re.Match[str]) -> str:
            content = match.group(2)
            lines = content.strip().split("\n")
            if len(lines) > self.max_code_lines:
                return f"{match.group(1)}\n[... {len(lines)} lines of source code stripped for privacy ...]\n{match.group(3)}"
            return match.group(0)

        # Regex to find markdown code blocks
        code_block_regex = re.compile(r"(```[a-z]*\n)(.*?)(\n```)", re.DOTALL)
        return code_block_regex.sub(replace_block, text)

    def apply(self, data: str) -> str:
        """
        Apply all privacy filters to the data.

        Args:
            data: Input string (goals, rationale, etc.)

        Returns:
            Redacted and filtered string.
        """
        data = self.redact_secrets(data)
        data = self.strip_code_blocks(data)
        return data
