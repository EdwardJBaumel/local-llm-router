from local_llm_router.benchmark import run_benchmark, routed_model_mix


def test_benchmark_routes_mixed_tiers():
    report = run_benchmark(model_names=["qwen3:4b", "qwen3:8b", "qwen3:14b", "qwen3:30b-a3b"])
    assert len(report.rows) == 10
    assert report.tier_counts["simple"] >= 1
    assert report.tier_counts["complex"] >= 1
    assert report.tier_counts["reasoning"] >= 1


def test_benchmark_model_mix_uses_more_than_one_model():
    report = run_benchmark(model_names=["qwen3:4b", "qwen3:8b", "qwen3:14b"])
    mix = routed_model_mix(report)
    assert len(mix) >= 2
