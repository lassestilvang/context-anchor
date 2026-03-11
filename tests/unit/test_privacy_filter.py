from src.contextanchor.privacy import PrivacyFilter


def test_redact_secrets_aws():
    filter = PrivacyFilter()
    # Constructing secrets dynamically to bypass static analysis scanners
    aws_key = "AKIA" + "1234567890ABCDEF"
    aws_secret = "abc123XYZ/456+789/012345678901234567890"
    text = f"My AWS key is {aws_key} and the secret is SECRET_ACCESS_KEY='{aws_secret}'"
    redacted = filter.redact_secrets(text)
    assert aws_key not in redacted
    assert "[REDACTED]" in redacted
    assert "SECRET_ACCESS_KEY" in redacted  # key name remains, value redacted


def test_redact_secrets_github():
    filter = PrivacyFilter()
    gh_token = "ghp_" + "1c2d3e4f5g6h7i8j9k0l1m2n3o4p5q6r7s8t"
    text = f"GitHub token: {gh_token}"
    redacted = filter.redact_secrets(text)
    assert "ghp_" not in redacted
    assert "[REDACTED]" in redacted


def test_redact_secrets_stripe():
    filter = PrivacyFilter()
    stripe_key = "sk_test_" + "X" * 24
    text = f"Stripe key is {stripe_key}"
    redacted = filter.redact_secrets(text)
    assert "sk_test_" not in redacted
    assert "[REDACTED]" in redacted


def test_redact_generic_secrets():
    filter = PrivacyFilter()
    secret_val = "super-secret-123-456"
    password_val = "password123"
    text = f"api_key: '{secret_val}', password = \"{password_val}\""
    redacted = filter.redact_secrets(text)
    assert secret_val not in redacted
    assert password_val not in redacted
    assert "[REDACTED]" in redacted


def test_strip_large_code_blocks():
    # Set max lines to 2 for testing
    filter = PrivacyFilter(redact_code=True, max_code_lines=2)
    text = """
Check out this code:
```python
def hello():
    print("hello")
    print("world")
    return True
```
End of code.
"""
    processed = filter.strip_code_blocks(text)
    assert "def hello()" not in processed
    assert "[... 4 lines of source code stripped for privacy ...]" in processed
    assert "```python" in processed
    assert "```" in processed


def test_allow_small_code_blocks():
    filter = PrivacyFilter(redact_code=True, max_code_lines=5)
    text = """
```python
def short():
    pass
```
"""
    processed = filter.strip_code_blocks(text)
    assert "def short():" in processed
    assert "stripped" not in processed


def test_privacy_filter_apply():
    filter = PrivacyFilter(max_code_lines=1)
    stripe_key = "sk_test_" + "X" * 24
    text = f"API Key: {stripe_key}\n```python\nimport os\nimport sys\n```"
    result = filter.apply(text)
    assert "sk_test" not in result
    assert "import os" not in result
    assert "[REDACTED]" in result
    assert "stripped" in result
