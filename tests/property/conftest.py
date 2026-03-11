"""
Hypothesis configuration for property-based tests.
"""

import os
from hypothesis import settings, Verbosity, HealthCheck

# Register profiles for different environments
# Default profile: 100 examples
settings.register_profile(
    "default",
    max_examples=100,
    deadline=1000,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)

# CI profile: More examples, stricter checks
settings.register_profile(
    "ci",
    max_examples=500,
    deadline=2000,
    suppress_health_check=[HealthCheck.too_slow],
)

# Debug profile: Less examples, high verbosity
settings.register_profile(
    "debug",
    max_examples=10,
    verbosity=Verbosity.verbose,
)

# Load profile from environment variable or default to 'default'
profile = os.getenv("HYPOTHESIS_PROFILE", "default")
settings.load_profile(profile)

# Configure deterministic seed if provided in environment
seed = os.getenv("HYPOTHESIS_SEED")
if seed:
    import hypothesis

    hypothesis.seed(int(seed))
