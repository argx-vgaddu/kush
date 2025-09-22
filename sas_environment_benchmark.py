#!/usr/bin/env python3
"""
SAS Environment Performance Benchmark
Compares execution performance across three SAS environments:
1. CASL on CAS Server
2. Base SAS on Viya Compute Server  
3. Base SAS on Local SAS Installation

Easy configuration: Modify N_VALUES at the top to change iteration counts.
"""

import json
import time
import os
import re
import subprocess
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

from sas_base_casl_comparision import (
    get_sas_tokens,
    get_config,
    SASJobExecutionClient
)

# ============================================================================
# CONFIGURATION - MODIFY THESE VALUES TO CHANGE ITERATION COUNTS
# ============================================================================

# Define the n values for 10^n iterations
# Examples:
#   [0, 1, 2] = [1, 10, 100] iterations
#   [0, 1, 2, 3, 4] = [1, 10, 100, 1000, 10000] iterations
#   [1, 2, 3] = [10, 100, 1000] iterations

N_VALUES = [0, 1, 2, 3, 4]  # This gives us [1, 10, 100, 1000, 10000] iterations

# For testing with smaller values, uncomment this line:
# N_VALUES = [0, 1, 2]  # Just [1, 10, 100] iterations for quick testing

# ============================================================================


class SASEnvironmentBenchmark:
    """Benchmarks SAS simulation performance across different environments"""
    
    def __init__(self, n_values=None):
        # Use provided n_values or default from configuration
        self.n_values = n_values if n_values is not None else N_VALUES
        self.iteration_counts = [10**n for n in self.n_values]
        
        print(f"Configured to test iterations: {self.iteration_counts}")
        print(f"(n values: {self.n_values})")
        
        self.environments = ['CASL_CAS', 'BASE_VIYA', 'BASE_LOCAL']
        self.results = {
            'CASL_CAS': [],
            'BASE_VIYA': [],
            'BASE_LOCAL': []
        }
        self.setup_file = 'config/setup.sas'
        self.backup_file = 'config/setup.sas.backup'
        self.client = None
        self.executor = ThreadPoolExecutor(max_workers=3)
        
    def backup_setup_file(self):
        """Create a backup of the original setup.sas file"""
        with open(self.setup_file, 'r') as f:
            content = f.read()
        with open(self.backup_file, 'w') as f:
            f.write(content)
        print(f"Created backup: {self.backup_file}")
    
    def restore_setup_file(self):
        """Restore the original setup.sas file from backup"""
        if os.path.exists(self.backup_file):
            with open(self.backup_file, 'r') as f:
                content = f.read()
            with open(self.setup_file, 'w') as f:
                f.write(content)
            print(f"Restored original setup.sas")
            os.remove(self.backup_file)
    
    def update_iteration_count(self, new_iter: int) -> str:
        """Update the iter macro variable in setup.sas"""
        with open(self.setup_file, 'r') as f:
            content = f.read()
        
        pattern = r'(%let\s+iter\s*=\s*)\d+(\s*;)'
        replacement = rf'\g<1>{new_iter}\g<2>'
        new_content = re.sub(pattern, replacement, content)
        
        with open(self.setup_file, 'w') as f:
            f.write(new_content)
        
        print(f"Testing with {new_iter} iterations")
        return new_content
    
    def run_casl_cas(self, setup_code: str) -> float:
        """Run CASL program on CAS server"""
        try:
            start_time = time.time()
            
            with open("programs/casl_simulation.sas", 'r') as f:
                program_code = f.read()
            
            full_code = f"{setup_code}\n\n{program_code}"
            
            job_definition = {
                "name": f"CASL CAS Simulation - {datetime.now().strftime('%H%M%S')}",
                "type": "Compute",
                "code": full_code,
                "parameters": [],
                "environment": {
                    "casServerId": "cas-shared-default"
                }
            }
            
            # Submit job with compute context (will be added automatically by client)
            job = self.client.submit_job(job_definition=job_definition)
            job_id = job['id']
            
            # Wait for completion
            timeout = 1800
            poll_interval = 5
            
            while time.time() - start_time < timeout:
                state = self.client.get_job_state(job_id)
                if state in ['completed', 'failed', 'cancelled']:
                    elapsed_time = time.time() - start_time
                    if state == 'completed':
                        return elapsed_time
                    elif state == 'failed':
                        try:
                            job_details = self.client.get_job_details(job_id)
                            error_msg = job_details.get('message', 'No error message available')
                            print(f"CASL job failed: {error_msg}")
                        except Exception as e:
                            print(f"CASL job failed (could not get details: {e})")
                        return None
                    elif state == 'cancelled':
                        print("CASL job cancelled")
                        return None
                time.sleep(poll_interval)
            
            print("CASL job timed out")
            return None
            
        except Exception as e:
            print(f"CASL error: {e}")
            return None
    
    def run_base_viya(self, setup_code: str) -> float:
        """Run Base SAS on Viya Compute server"""
        try:
            start_time = time.time()
            
            with open("programs/base_simulation.sas", 'r') as f:
                program_code = f.read()
            
            full_code = f"{setup_code}\n\n{program_code}"
            
            job_definition = {
                "name": f"Base SAS Viya Simulation - {datetime.now().strftime('%H%M%S')}",
                "type": "Compute",
                "code": full_code,
                "parameters": [],
                "environment": {}
            }
            
            # Submit job with compute context (will be added automatically by client)
            job = self.client.submit_job(job_definition=job_definition)
            job_id = job['id']
            
            # Wait for completion
            timeout = 1800
            poll_interval = 5
            
            while time.time() - start_time < timeout:
                state = self.client.get_job_state(job_id)
                if state in ['completed', 'failed', 'cancelled']:
                    elapsed_time = time.time() - start_time
                    if state == 'completed':
                        return elapsed_time
                    elif state == 'failed':
                        try:
                            job_details = self.client.get_job_details(job_id)
                            error_msg = job_details.get('message', 'No error message available')
                            print(f"Base Viya job failed: {error_msg}")
                        except Exception as e:
                            print(f"Base Viya job failed (could not get details: {e})")
                        return None
                    elif state == 'cancelled':
                        print("Base Viya job cancelled")
                        return None
                time.sleep(poll_interval)
            
            print("Base Viya job timed out")
            return None
            
        except Exception as e:
            print(f"Base Viya error: {e}")
            return None
    
    def run_base_local(self, setup_file: str) -> float:
        """Run Base SAS on local SAS installation"""
        try:
            start_time = time.time()
            
            local_program = "programs/base_local_simulation.sas"
            
            # Find SAS executable
            sas_paths = [
                r"C:\Program Files\SASHome\SASFoundation\9.4\sas.exe",
                r"C:\Program Files\SAS\SASFoundation\9.4\sas.exe",
                r"C:\Program Files (x86)\SASHome\SASFoundation\9.4\sas.exe",
                r"C:\SAS9.4\sas.exe",
            ]
            
            sas_exe = None
            for path in sas_paths:
                if os.path.exists(path):
                    sas_exe = path
                    break
            
            if not sas_exe:
                sas_exe = "sas"
            
            cmd = [
                sas_exe,
                "-sysin", local_program,
                "-log", "results/base_local_simulation.log",
                "-print", "results/base_local_simulation.lst",
                "-nosplash",
                "-noterminal",
                "-nologo"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800,
                cwd=os.getcwd()
            )
            
            elapsed_time = time.time() - start_time
            
            if result.returncode == 0:
                return elapsed_time
            else:
                print(f"Local SAS failed with return code {result.returncode}")
                return None
                
        except subprocess.TimeoutExpired:
            print("Local SAS timed out")
            return None
        except Exception as e:
            print(f"Local SAS error: {e}")
            return None
    
    def run_iteration_benchmark(self, iter_count: int, n_value: int) -> Dict[str, float]:
        """Run all three environments in parallel for given iteration count"""
        
        print(f"\n{'='*60}")
        print(f"Benchmarking 10^{n_value} = {iter_count} iterations")
        print(f"{'='*60}")
        
        setup_code = self.update_iteration_count(iter_count)
        
        # Submit all three jobs in parallel
        futures = {
            self.executor.submit(self.run_casl_cas, setup_code): 'CASL_CAS',
            self.executor.submit(self.run_base_viya, setup_code): 'BASE_VIYA',
            self.executor.submit(self.run_base_local, self.setup_file): 'BASE_LOCAL'
        }
        
        results = {}
        
        # Collect results as they complete
        for future in as_completed(futures):
            env_name = futures[future]
            try:
                elapsed_time = future.result()
                results[env_name] = elapsed_time
                
                if elapsed_time:
                    print(f"✓ {env_name}: {elapsed_time:.2f} seconds")
                else:
                    print(f"✗ {env_name}: Failed")
                    
            except Exception as e:
                print(f"✗ {env_name}: Error - {e}")
                results[env_name] = None
        
        # Analyze results for this iteration
        valid_results = {k: v for k, v in results.items() if v is not None}
        if len(valid_results) >= 2:
            fastest = min(valid_results.items(), key=lambda x: x[1])
            print(f"\nFastest for {iter_count} iterations: {fastest[0]} ({fastest[1]:.2f}s)")
            
            for env, time in valid_results.items():
                if env != fastest[0]:
                    slowdown = (time / fastest[1] - 1) * 100
                    print(f"  {env} is {slowdown:.1f}% slower")
        
        return results
    
    def run_all_benchmarks(self):
        """Run benchmarks for all iteration counts"""
        try:
            self.backup_setup_file()
            
            # Authenticate with Viya
            print("Authenticating with SAS Viya...")
            tokens = get_sas_tokens()
            access_token = tokens['access_token']
            config = get_config()
            self.client = SASJobExecutionClient(config["base_url"], access_token)
            print("Authentication successful!\n")
            
            print("="*60)
            print("SAS ENVIRONMENT PERFORMANCE BENCHMARK")
            print("Comparing: CASL on CAS vs Base SAS on Viya vs Base SAS Local")
            print(f"Testing n values: {self.n_values}")
            print(f"Iterations: {self.iteration_counts}")
            print("="*60)
            
            # Run benchmarks for each iteration count
            for n_value, iter_count in zip(self.n_values, self.iteration_counts):
                times = self.run_iteration_benchmark(iter_count, n_value)
                
                # Store results
                for env in self.environments:
                    self.results[env].append(times.get(env))
                
                # Save intermediate results
                self.save_results()
                
                # Brief pause between iteration counts
                if iter_count < self.iteration_counts[-1]:
                    time.sleep(5)
            
            print("\n" + "="*60)
            print("BENCHMARK COMPLETED")
            print("="*60)
            
        finally:
            self.executor.shutdown(wait=True)
            self.restore_setup_file()
    
    def save_results(self):
        """Save benchmark results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON
        data = {
            'timestamp': timestamp,
            'n_values': self.n_values,
            'iteration_counts': self.iteration_counts,
            'results': self.results
        }
        
        json_file = f"results/sas_environment_benchmark_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Save CSV
        df = pd.DataFrame({
            'n': self.n_values[:len(self.results['CASL_CAS'])],
            'Iterations': self.iteration_counts[:len(self.results['CASL_CAS'])],
            'CASL_CAS (s)': self.results['CASL_CAS'],
            'BASE_VIYA (s)': self.results['BASE_VIYA'],
            'BASE_LOCAL (s)': self.results['BASE_LOCAL']
        })
        
        csv_file = f"results/sas_environment_benchmark_{timestamp}.csv"
        df.to_csv(csv_file, index=False, float_format='%.2f')
        
        return json_file, csv_file
    
    def create_visualization(self):
        """Create performance comparison visualizations"""
        
        x_values = np.array(self.n_values)
        
        # Create figure with 4 subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
        
        # Color scheme for environments
        colors = {
            'CASL_CAS': '#2E86AB',    # Blue
            'BASE_VIYA': '#A23B72',    # Purple
            'BASE_LOCAL': '#F18F01'    # Orange
        }
        
        labels = {
            'CASL_CAS': 'CASL on CAS',
            'BASE_VIYA': 'Base SAS on Viya',
            'BASE_LOCAL': 'Base SAS Local'
        }
        
        # Plot 1: Execution times (linear scale)
        for env, color in colors.items():
            times = self.results[env]
            valid_indices = [i for i, t in enumerate(times) if t is not None]
            valid_x = [x_values[i] for i in valid_indices]
            valid_times = [times[i] for i in valid_indices]
            
            ax1.plot(valid_x, valid_times, '-', label=labels[env],
                    color=color, linewidth=2.5, markersize=8, marker='s')
        
        ax1.set_xlabel('n (iterations = 10^n)', fontsize=11)
        ax1.set_ylabel('Execution Time (seconds)', fontsize=11)
        ax1.set_title('Execution Time Comparison - Linear Scale', fontsize=12, fontweight='bold')
        ax1.set_xticks(x_values)
        ax1.set_xticklabels([str(n) for n in self.n_values])
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left')
        
        # Plot 2: Execution times (log scale)
        for env, color in colors.items():
            times = self.results[env]
            valid_indices = [i for i, t in enumerate(times) if t is not None and t > 0]
            valid_x = [x_values[i] for i in valid_indices]
            valid_times = [times[i] for i in valid_indices]
            
            if valid_times:
                ax2.semilogy(valid_x, valid_times, '-', label=labels[env],
                           color=color, linewidth=2.5, markersize=8, marker='s')
        
        ax2.set_xlabel('n (iterations = 10^n)', fontsize=11)
        ax2.set_ylabel('Execution Time (seconds) - Log Scale', fontsize=11)
        ax2.set_title('Execution Time Comparison - Log Scale', fontsize=12, fontweight='bold')
        ax2.set_xticks(x_values)
        ax2.set_xticklabels([str(n) for n in self.n_values])
        ax2.grid(True, alpha=0.3, which='both')
        ax2.legend(loc='upper left')
        
        # Plot 3: Relative performance (normalized to fastest)
        bar_width = 0.25
        x_positions = np.arange(len(self.n_values))
        
        for i, (iter_count, n_val) in enumerate(zip(self.iteration_counts, self.n_values)):
            times_at_iter = {
                env: self.results[env][i] 
                for env in self.environments 
                if i < len(self.results[env]) and self.results[env][i] is not None
            }
            
            if times_at_iter:
                min_time = min(times_at_iter.values())
                
                for j, env in enumerate(self.environments):
                    if env in times_at_iter:
                        rel_time = times_at_iter[env] / min_time
                        ax3.bar(x_positions[i] + (j - 1) * bar_width, 
                               rel_time, width=bar_width, 
                               label=labels[env] if i == 0 else "",
                               color=colors[env], alpha=0.8)
        
        ax3.axhline(y=1, color='red', linestyle='--', alpha=0.5)
        ax3.set_xlabel('n (iterations = 10^n)', fontsize=11)
        ax3.set_ylabel('Relative Performance (vs Fastest)', fontsize=11)
        ax3.set_title('Relative Performance Comparison', fontsize=12, fontweight='bold')
        ax3.set_xticks(x_positions)
        ax3.set_xticklabels([str(n) for n in self.n_values])
        ax3.grid(True, alpha=0.3, axis='y')
        ax3.legend(loc='upper left')
        
        # Plot 4: Performance scaling
        for env, color in colors.items():
            times = self.results[env]
            valid_indices = [i for i, t in enumerate(times) if t is not None and i > 0]
            
            if len(valid_indices) > 0:
                scaling_factors = []
                x_labels = []
                for i in valid_indices:
                    if self.results[env][i-1] is not None and self.results[env][i-1] > 0:
                        # How much slower when iterations increase by 10x
                        factor = self.results[env][i] / self.results[env][i-1]
                        scaling_factors.append(factor)
                        x_labels.append(f"{self.n_values[i-1]}→{self.n_values[i]}")
                    else:
                        scaling_factors.append(None)
                
                valid_x = [i for i, f in enumerate(scaling_factors) if f is not None]
                valid_factors = [f for f in scaling_factors if f is not None]
                
                if valid_factors:
                    ax4.plot(valid_x, valid_factors, '-', label=labels[env],
                           color=color, linewidth=2.5, markersize=8, marker='s')
        
        ax4.axhline(y=10, color='green', linestyle='--', alpha=0.5, label='Linear scaling (10x)')
        ax4.set_xlabel('Transition (n→n+1)', fontsize=11)
        ax4.set_ylabel('Scaling Factor', fontsize=11)
        ax4.set_title('Performance Scaling Analysis', fontsize=12, fontweight='bold')
        
        # Create x-axis labels for transitions
        if len(self.n_values) > 1:
            transition_labels = [f"{self.n_values[i]}→{self.n_values[i+1]}" 
                               for i in range(len(self.n_values)-1)]
            ax4.set_xticks(range(len(transition_labels)))
            ax4.set_xticklabels(transition_labels)
        
        ax4.grid(True, alpha=0.3)
        ax4.legend(loc='upper left')
        
        # Overall title
        fig.suptitle('SAS Environment Performance Comparison: CASL vs Base SAS (Viya) vs Base SAS (Local)', 
                    fontsize=14, fontweight='bold', y=1.02)
        
        plt.tight_layout()
        
        # Save figures
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        png_file = f"results/sas_environment_performance_{timestamp}.png"
        pdf_file = f"results/sas_environment_performance_{timestamp}.pdf"
        
        plt.savefig(png_file, dpi=300, bbox_inches='tight')
        plt.savefig(pdf_file, bbox_inches='tight')
        
        print(f"\n📊 Visualizations saved:")
        print(f"  - {png_file}")
        print(f"  - {pdf_file}")
        
        plt.show()
        
        return png_file
    
    def print_summary(self):
        """Print comprehensive performance summary"""
        
        print("\n" + "="*70)
        print("PERFORMANCE SUMMARY: SAS ENVIRONMENT COMPARISON")
        print("="*70)
        
        # Create summary DataFrame
        df_display = pd.DataFrame({
            'n': self.n_values,
            'Iterations': self.iteration_counts,
            'CASL on CAS (s)': [f"{t:.2f}" if t else "Failed" for t in self.results['CASL_CAS']],
            'Base SAS Viya (s)': [f"{t:.2f}" if t else "Failed" for t in self.results['BASE_VIYA']],
            'Base SAS Local (s)': [f"{t:.2f}" if t else "Failed" for t in self.results['BASE_LOCAL']]
        })
        
        print("\nExecution Times by Environment:")
        print(df_display.to_string(index=False))
        
        # Performance analysis
        print("\n" + "="*70)
        print("PERFORMANCE ANALYSIS")
        print("="*70)
        
        for i, (n_val, iter_count) in enumerate(zip(self.n_values, self.iteration_counts)):
            print(f"\n10^{n_val} = {iter_count} iterations:")
            
            times = {
                'CASL on CAS': self.results['CASL_CAS'][i] if i < len(self.results['CASL_CAS']) else None,
                'Base SAS Viya': self.results['BASE_VIYA'][i] if i < len(self.results['BASE_VIYA']) else None,
                'Base SAS Local': self.results['BASE_LOCAL'][i] if i < len(self.results['BASE_LOCAL']) else None
            }
            
            valid_times = {k: v for k, v in times.items() if v is not None}
            
            if valid_times:
                fastest = min(valid_times.items(), key=lambda x: x[1])
                slowest = max(valid_times.items(), key=lambda x: x[1])
                
                print(f"  Fastest: {fastest[0]} ({fastest[1]:.2f}s)")
                print(f"  Slowest: {slowest[0]} ({slowest[1]:.2f}s)")
                
                if fastest[1] > 0:
                    speedup = slowest[1] / fastest[1]
                    print(f"  Speed difference: {speedup:.2f}x")
                
                # Relative performance
                print(f"  Relative performance:")
                for env, time in sorted(valid_times.items(), key=lambda x: x[1]):
                    relative = time / fastest[1]
                    print(f"    {env}: {relative:.2f}x")
        
        # Overall statistics
        print("\n" + "="*70)
        print("OVERALL STATISTICS")
        print("="*70)
        
        # Calculate average performance across all iterations
        avg_times = {}
        for env in self.environments:
            valid_times = [t for t in self.results[env] if t is not None]
            if valid_times:
                avg_times[env] = sum(valid_times) / len(valid_times)
        
        if avg_times:
            fastest_avg = min(avg_times.items(), key=lambda x: x[1])
            print(f"\nAverage Performance Leader: {fastest_avg[0]}")
            print("\nAverage Relative Performance:")
            for env, avg_time in sorted(avg_times.items(), key=lambda x: x[1]):
                relative = avg_time / fastest_avg[1]
                env_label = {
                    'CASL_CAS': 'CASL on CAS',
                    'BASE_VIYA': 'Base SAS on Viya',
                    'BASE_LOCAL': 'Base SAS Local'
                }[env]
                print(f"  {env_label}: {relative:.2f}x")
        
        # Scaling analysis
        print("\n" + "="*70)
        print("SCALING CHARACTERISTICS")
        print("="*70)
        
        for env in self.environments:
            env_label = {
                'CASL_CAS': 'CASL on CAS',
                'BASE_VIYA': 'Base SAS on Viya',
                'BASE_LOCAL': 'Base SAS Local'
            }[env]
            
            print(f"\n{env_label}:")
            
            times = self.results[env]
            for i in range(1, len(times)):
                if times[i] is not None and times[i-1] is not None and times[i-1] > 0:
                    scaling = times[i] / times[i-1]
                    n_prev = self.n_values[i-1]
                    n_curr = self.n_values[i]
                    iter_prev = self.iteration_counts[i-1]
                    iter_curr = self.iteration_counts[i]
                    print(f"  10^{n_prev} → 10^{n_curr} ({iter_prev} → {iter_curr}): {scaling:.2f}x slower")


def main():
    """Main execution function"""
    print("="*70)
    print("SAS ENVIRONMENT PERFORMANCE BENCHMARK")
    print("="*70)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Comparing simulation performance across:")
    print("  1. CASL on CAS Server")
    print("  2. Base SAS on Viya Compute Server")
    print("  3. Base SAS on Local Installation")
    print("="*70)
    
    # You can also override N_VALUES here for a specific run:
    # benchmark = SASEnvironmentBenchmark(n_values=[0, 1, 2])  # Just test 1, 10, 100
    
    benchmark = SASEnvironmentBenchmark()  # Uses N_VALUES from configuration
    
    try:
        # Run benchmarks
        benchmark.run_all_benchmarks()
        
        # Print summary
        benchmark.print_summary()
        
        # Create visualizations
        benchmark.create_visualization()
        
        print("\n" + "="*70)
        print("✅ BENCHMARK COMPLETED SUCCESSFULLY")
        print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        if os.path.exists(benchmark.backup_file):
            benchmark.restore_setup_file()


if __name__ == "__main__":
    main()
