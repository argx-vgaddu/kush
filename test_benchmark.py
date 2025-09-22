#!/usr/bin/env python3
"""
Test script for SAS Environment Benchmark
Tests with small iteration values to verify everything works before running full benchmark
"""

from sas_environment_benchmark import SASEnvironmentBenchmark

def test_small_values():
    """Test with just 1 and 10 iterations"""
    print("="*70)
    print("TESTING WITH SMALL VALUES")
    print("="*70)
    
    # Test with n = [0, 1] which gives us [1, 10] iterations
    benchmark = SASEnvironmentBenchmark(n_values=[0, 1])
    
    try:
        benchmark.run_all_benchmarks()
        benchmark.print_summary()
        benchmark.create_visualization()
        
        print("\n✅ Test completed successfully!")
        print("You can now run the full benchmark with larger values.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_small_values()
