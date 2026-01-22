"""
Timing utilities for measuring performance of different pipeline components.
"""

import time
import json
from contextlib import contextmanager
from collections import defaultdict
from typing import Dict, List


class TimingStats:
    """Track timing statistics for different operations"""

    def __init__(self):
        self.timings: Dict[str, List[float]] = defaultdict(list)
        self.counts: Dict[str, int] = defaultdict(int)

    def record(self, operation: str, duration: float):
        """Record a timing measurement"""
        self.timings[operation].append(duration)
        self.counts[operation] += 1

    def get_stats(self, operation: str) -> Dict:
        """Get statistics for a specific operation"""
        if operation not in self.timings:
            return {}

        durations = self.timings[operation]
        return {
            "count": len(durations),
            "total_time": sum(durations),
            "avg_time": sum(durations) / len(durations),
            "min_time": min(durations),
            "max_time": max(durations),
        }

    def get_all_stats(self) -> Dict:
        """Get statistics for all operations"""
        stats = {}
        for operation in self.timings.keys():
            stats[operation] = self.get_stats(operation)
        return stats

    def print_summary(self):
        """Print a formatted summary of all timings"""
        print("\n" + "=" * 80)
        print("TIMING SUMMARY")
        print("=" * 80)

        all_stats = self.get_all_stats()

        # Sort by total time (most expensive first)
        sorted_ops = sorted(
            all_stats.items(),
            key=lambda x: x[1].get("total_time", 0),
            reverse=True
        )

        for operation, stats in sorted_ops:
            print(f"\n{operation}:")
            print(f"  Count:      {stats['count']:,}")
            print(f"  Total:      {stats['total_time']:.2f}s")
            print(f"  Average:    {stats['avg_time']:.3f}s")
            print(f"  Min:        {stats['min_time']:.3f}s")
            print(f"  Max:        {stats['max_time']:.3f}s")

        print("\n" + "=" * 80)
        print(f"OVERALL TOTAL: {sum(s['total_time'] for s in all_stats.values()):.2f}s")
        print("=" * 80 + "\n")

    def save_to_file(self, filepath: str):
        """Save timing stats to JSON file"""
        stats = self.get_all_stats()
        with open(filepath, 'w') as f:
            json.dump(stats, f, indent=2)

    def reset(self):
        """Clear all timing data"""
        self.timings.clear()
        self.counts.clear()


# Global timing instance
_timing_stats = TimingStats()


def get_timing_stats() -> TimingStats:
    """Get the global timing stats instance"""
    return _timing_stats


@contextmanager
def timed_operation(operation_name: str):
    """
    Context manager for timing an operation.

    Usage:
        with timed_operation("vector_store_search"):
            results = search_vector_store(...)
    """
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        _timing_stats.record(operation_name, duration)


def time_function(operation_name: str):
    """
    Decorator for timing a function.

    Usage:
        @time_function("my_function")
        def my_function():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with timed_operation(operation_name):
                return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator
