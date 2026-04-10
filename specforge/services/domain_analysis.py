"""Domain analysis — backward-compatible facade over the domain intelligence engine.

All public functions retain their original signatures so that existing callers
(``prd.py``, tests, etc.) continue to work without changes.  Internally they
delegate to ``domain_intelligence`` which contains the weighted, configurable
rule engine.
"""

from __future__ import annotations

from .domain_intelligence import (
    calculate_rms,
    detect_conflicts,
    detect_domain,
    detect_implied_users,
    detect_missing_features,
    generate_functional_reqs,
    generate_questions,
    reset_profiles,
)

# Re-export DOMAIN_TEMPLATES for any code that accesses it directly
from .domain_intelligence import _get_profiles as _get_profiles

# Pre-build the templates dict at import time (thread-safe, no external deps).
DOMAIN_TEMPLATES: dict[str, list[str]] = {
    name: profile.feature_template
    for name, profile in _get_profiles().items()
}

__all__ = [
    "DOMAIN_TEMPLATES",
    "calculate_rms",
    "detect_conflicts",
    "detect_domain",
    "detect_implied_users",
    "detect_missing_features",
    "generate_functional_reqs",
    "generate_questions",
    "reset_profiles",
]
