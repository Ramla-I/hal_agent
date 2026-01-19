model_costs = {
    "gpt-5.2": {
        "input_cost_pm": 1.75,
        "input_cached_cost_pm": 0.18,
        "output_cost_pm": 14,
        "window": 400_000,
        "max_output_tokens": 128_000,
    },
    "gpt-oss-120b": {
        "input_cost_pm": 0.15,
        "input_cached_cost_pm": 0.075,
        "output_cost_pm": 0.60,
        "window": 131_072,
        "max_output_tokens": 65_536,
    },
    "gpt-5-nano": {
        "input_cost_pm": 0.05,
        "input_cached_cost_pm": 0.01,
        "output_cost_pm": 0.40,
        "window": 400_000,
        "max_output_tokens": 128_000,
    },
        "gpt-4.1-nano": {
        "input_cost_pm": 0.10,
        "input_cached_cost_pm": 0.03,
        "output_cost_pm": 0.40,
        "window": 1_047_576,
        "max_output_tokens": 32_678,
    },
}