"""Unit tests for Differential Privacy releases and epsilon budget tracking."""

import pytest
import numpy as np
from prahari.harmonisation.differential_privacy import DifferentialPrivacyEngine


def test_differential_privacy_count_release():
    engine = DifferentialPrivacyEngine(default_epsilon=1.0, seed=42)

    true_count = 50.0
    release = engine.release_count(
        true_count=true_count,
        epsilon=1.0,
        sensitivity=1.0,
        signal_type="clinical_resp",
    )

    assert release.true_count == 50.0
    assert release.noisy_count >= 0.0
    assert release.epsilon == 1.0

    # Privacy budget consumed
    summary = engine.get_budget_summary()
    assert summary["total_epsilon_consumed"] == 1.0
    assert summary["total_queries_released"] == 1


def test_differential_privacy_noise_scaling():
    """
    Higher epsilon (weaker privacy guarantee) -> lower noise variance.
    Lower epsilon (stronger privacy guarantee) -> higher noise variance.
    """
    engine_high_eps = DifferentialPrivacyEngine(seed=42)
    engine_low_eps = DifferentialPrivacyEngine(seed=42)

    # Collect 100 samples with eps=10.0 vs eps=0.1
    high_eps_errors = [
        abs(engine_high_eps.release_count(100.0, epsilon=10.0).noisy_count - 100.0)
        for _ in range(50)
    ]
    low_eps_errors = [
        abs(engine_low_eps.release_count(100.0, epsilon=0.1).noisy_count - 100.0)
        for _ in range(50)
    ]

    mean_err_high = float(np.mean(high_eps_errors))
    mean_err_low = float(np.mean(low_eps_errors))

    assert mean_err_low > mean_err_high


def test_invalid_epsilon():
    engine = DifferentialPrivacyEngine()
    with pytest.raises(ValueError, match="strictly positive"):
        engine.release_count(50.0, epsilon=0.0)

