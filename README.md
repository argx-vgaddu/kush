# SAS Environment Performance Benchmark

This comprehensive benchmark suite compares the performance of SAS simulations across three environments:
1. **CASL on CAS Server** - In-memory analytics using CAS Action Language
2. **Base SAS on Viya Compute** - Traditional SAS on Viya compute server
3. **Base SAS Local** - Local SAS installation

## Recent Updates

- **Improved Folder Structure**: Configuration files moved to `config/`, results to `results/`
- **Automatic Compute Context Management**: Tool now automatically retrieves and uses SAS Viya compute contexts
- **Enhanced Error Handling**: Better handling of compute context errors (Error code: 31509)
- **Organized Output**: All benchmark results and visualizations saved to `results/` directory

## Features

- **Multi-platform execution**: Run the same SAS simulation program across different environments
- **Centralized configuration**: Local `config/setup.sas` file automatically concatenated to server programs
- **Performance benchmarking**: Compare execution times between CASL, BASE SAS, and LOCAL SAS
- **Comprehensive logging**: Detailed execution statistics and output file verification
- **Error handling**: Robust error handling for all execution methods
- **Configurable benchmarking**: Multiple configuration options for different testing scenarios
- **Automated visualization**: Generate performance charts and analysis reports

## Prerequisites

### 1. Python Environment
- Python 3.8 or higher
- `uv` package manager (recommended)
- Required Python packages (automatically installed via `uv`):
  - `requests`
  - `python-dotenv`
  - `pandas`
  - `matplotlib`
  - `numpy`

### 2. SAS Environment
- **SAS Viya access** (for CASL and BASE SAS via Viya):
  - Valid SAS Viya credentials
  - Access to SAS Job Execution API
  - Compute context configured in SAS Viya
  - **Note**: The Python script automatically concatenates the local `config/setup.sas` file with the server programs
- **Local SAS installation** (for LOCAL SAS):
  - SAS 9.4 installed at: `C:\Program Files\SASHome\SASFoundation\9.4\sas.exe`
  - SAS program file: `programs/base_local_simulation.sas`

### 3. Environment Configuration
Create a `.env` file in the project root with your SAS Viya credentials:
```bash
SAS_BASE_URL=https://your-sas-viya-server.com
SAS_CLIENT_ID=your_client_id
SAS_USERNAME=your_username
SAS_PASSWORD=your_password
```

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd C:\sas\kush
   ```

2. **Install dependencies using uv:**
   ```bash
   uv sync
   ```

## Usage

### Quick Start

#### 1. Test with Small Values First
```bash
# Run a quick test with just 1 and 10 iterations
py -m uv run test_benchmark.py
```

#### 2. Run Full Benchmark
```bash
# Run with default configuration [1, 10, 100, 1000, 10000] iterations
py -m uv run sas_environment_benchmark.py
```

### Single Comparison Run

#### Option 1: Using uv directly (Recommended)

```bash
# Run the comparison script
uv run python sas_base_casl_comparision.py

# Or using the py launcher with uv
py -m uv run python sas_base_casl_comparision.py
```

#### Option 2: Using traditional Python

```bash
# If you have the dependencies installed in your environment
python sas_base_casl_comparision.py
```

#### Option 3: Using uv run with specific Python version

```bash
uv run --python 3.11 python sas_base_casl_comparision.py
```

## Configuration Options

### Method 1: Edit N_VALUES in the Script

Edit `sas_environment_benchmark.py` and modify the `N_VALUES` variable at the top:

```python
# For quick testing (1 and 10 iterations)
N_VALUES = [0, 1]  

# For small benchmark (1, 10, 100 iterations)
N_VALUES = [0, 1, 2]  

# For medium benchmark (1, 10, 100, 1000 iterations)
N_VALUES = [0, 1, 2, 3]  

# For full benchmark (1, 10, 100, 1000, 10000 iterations)
N_VALUES = [0, 1, 2, 3, 4]  

# Custom examples:
N_VALUES = [1, 2, 3]    # [10, 100, 1000] - skip single iteration
N_VALUES = [2, 3, 4]    # [100, 1000, 10000] - only larger values
N_VALUES = [0, 2, 4]    # [1, 100, 10000] - sparse sampling
```

### Method 2: Use Configuration Presets

Use the `config/benchmark_config.py` script with presets:

```bash
# Quick test (1, 10 iterations) - ~1 minute
py -m uv run python config/benchmark_config.py quick

# Small benchmark (1, 10, 100 iterations) - ~5 minutes
py -m uv run python config/benchmark_config.py small

# Medium benchmark (1, 10, 100, 1000 iterations) - ~30 minutes
py -m uv run python config/benchmark_config.py medium

# Full benchmark (1, 10, 100, 1000, 10000 iterations) - ~2 hours
py -m uv run python config/benchmark_config.py full
```

### Method 3: Programmatic Control

Create your own script:

```python
from sas_environment_benchmark import SASEnvironmentBenchmark

# Define your custom n values
my_n_values = [0, 2, 3]  # This gives [1, 100, 1000] iterations

# Run benchmark
benchmark = SASEnvironmentBenchmark(n_values=my_n_values)
benchmark.run_all_benchmarks()
benchmark.print_summary()
benchmark.create_visualization()
```

### Method 4: Import Configurations

```python
import sys
sys.path.append('config')
from benchmark_config import QUICK_TEST, SMALL_BENCHMARK, FULL_BENCHMARK
from sas_environment_benchmark import SASEnvironmentBenchmark

# Use a predefined configuration
benchmark = SASEnvironmentBenchmark(n_values=SMALL_BENCHMARK)
benchmark.run_all_benchmarks()
benchmark.print_summary()
benchmark.create_visualization()
```

## Understanding n Values

The benchmark uses `n` values where iterations = 10^n:

| n value | Iterations | Typical Runtime |
|---------|------------|-----------------|
| 0       | 1          | ~1 second       |
| 1       | 10         | ~3 seconds      |
| 2       | 100        | ~30 seconds     |
| 3       | 1000       | ~5 minutes      |
| 4       | 10000      | ~50 minutes     |

## What the Tool Does

1. **Authentication**: Connects to SAS Viya using OAuth2 flow
   - Automatically retrieves available compute contexts from SAS Viya
   - Selects appropriate compute context (looks for "Job Execution" or "default")
   - Caches context ID for efficient reuse
2. **Program Preparation**:
   - Automatically concatenates local `config/setup.sas` with server programs
   - Prepares combined code for SAS Viya submission
   - Configures compute context for job execution
3. **Program Execution**:
   - Submits combined CASL simulation program to SAS Viya
   - Submits combined BASE SAS simulation program to SAS Viya
   - Executes LOCAL SAS simulation program using local SAS installation
4. **Performance Comparison**: Measures and compares execution times
5. **Results Display**: Shows detailed execution statistics for each method

## Expected Output

The tool will display:
- Execution time for each SAS program type
- Job status and completion details
- Performance comparison with percentage differences
- Output file verification (Excel files created by SAS programs)

Example output:
```
SAS Program Performance Comparison: CASL vs BASE SAS vs LOCAL SAS
======================================================================

Submitting CASL Program...
==========================
Job submitted successfully with ID: job_12345
CASL Simulation Results:
==================================================
Job ID: job_12345
Final State: completed
Elapsed Time: 1250 ms
Creation Time: 2025-01-20T10:30:00Z
End Time: 2025-01-20T10:30:01Z

Submitting BASE SAS Program...
==============================
Job submitted successfully with ID: job_12346
BASE SAS Simulation Results:
==================================================
Job ID: job_12346
Final State: completed
Elapsed Time: 1450 ms

Submitting LOCAL SAS Program...
==============================
Executing: C:\Program Files\SASHome\SASFoundation\9.4\sas.exe -sysin ./programs/base_local_simulation.sas
LOCAL SAS program completed in 980 ms
LOCAL SAS Simulation Results:
==================================================
Job ID: local_sas_run
Final State: completed
Elapsed Time: 980 ms
Creation Time: 2025-01-20T10:30:01Z
End Time: 2025-01-20T10:30:02Z

Performance Comparison:
==================================================
CASL Execution Time: 1250 ms
BASE SAS Execution Time: 1450 ms
LOCAL SAS Execution Time: 980 ms

Fastest execution: LOCAL SAS (980 ms)
CASL was 27.6% slower than LOCAL SAS
BASE SAS was 48.0% slower than LOCAL SAS
```

## Output Files

### SAS Program Output
The SAS programs generate the following output files in the `output/` directory:
- `modsum_base.xlsx` - Summary statistics by decision region
- `modOC_base.xlsx` - Detailed simulation results

### Benchmark Output
The benchmark creates several output files in the `results/` directory:

1. **JSON Results**: `sas_environment_benchmark_YYYYMMDD_HHMMSS.json`
   - Raw benchmark data
   - All timing information
   - Can be loaded for further analysis

2. **CSV Results**: `sas_environment_benchmark_YYYYMMDD_HHMMSS.csv`
   - Tabular format
   - Easy to import into Excel
   - Contains n values, iterations, and execution times

3. **Visualizations**:
   - `sas_environment_performance_YYYYMMDD_HHMMSS.png` - High-resolution graphs
   - `sas_environment_performance_YYYYMMDD_HHMMSS.pdf` - Publication-quality PDF

## Sample Usage Scenarios

### Scenario 1: Quick Validation
Test that everything works with minimal time investment:
```bash
py -m uv run python config/benchmark_config.py quick
```

### Scenario 2: Performance Testing
Get meaningful performance data without waiting hours:
```bash
py -m uv run python config/benchmark_config.py small
```

### Scenario 3: Full Analysis
Complete benchmark for presentation or documentation:
```bash
py -m uv run python config/benchmark_config.py full
```

### Scenario 4: Custom Analysis
Focus on specific iteration ranges:
```python
from sas_environment_benchmark import SASEnvironmentBenchmark

# Only test larger workloads
benchmark = SASEnvironmentBenchmark(n_values=[3, 4])  # 1000 and 10000 iterations
benchmark.run_all_benchmarks()
benchmark.print_summary()
benchmark.create_visualization()
```

## Interpreting Results

The benchmark provides:

1. **Execution Times**: Raw timing for each environment at each iteration count
2. **Relative Performance**: How much slower each environment is compared to the fastest
3. **Scaling Analysis**: How performance changes as iterations increase
4. **Visual Comparisons**: 
   - Linear and log scale plots
   - Relative performance bars
   - Scaling factor analysis

## Tips for Best Results

1. **Start Small**: Always test with `[0, 1]` first to ensure everything works
2. **Close Other Programs**: Minimize system load during benchmarking
3. **Multiple Runs**: Consider running benchmarks multiple times for consistency
4. **Monitor Resources**: Watch CPU and memory usage during execution
5. **Save Results**: All results are automatically saved with timestamps

## Troubleshooting

### Common Issues

1. **SAS Viya Authentication Failed**
   - Verify your credentials in the `.env` file
   - Ensure your SAS Viya server URL is correct
   - Check network connectivity to SAS Viya

2. **Compute Context Errors (Error code: 31509)**
   - The tool automatically retrieves available compute contexts
   - Ensures proper `_contextId` is included in job submissions
   - If issues persist, verify compute contexts are configured in SAS Viya

3. **Local SAS Not Found**
   - Verify SAS 9.4 is installed at the specified path
   - Check if `sas.exe` exists in `C:\Program Files\SASHome\SASFoundation\9.4\`
   - The script searches common SAS installation paths
   - If SAS is installed elsewhere, update the paths in the script

4. **Permission Errors**
   - Ensure the current user has execute permissions for SAS
   - Check write permissions for the `output/` and `results/` directories

5. **Python Dependencies**
   - Run `uv sync` to install all required packages
   - Ensure `uv` is properly installed and in your PATH

### Authentication Issues
- Ensure `data/sas_tokens.json` exists and is valid
- Re-authenticate if tokens have expired

### Timeout Issues
- Large iteration counts (10000+) may take >30 minutes
- Consider running overnight for full benchmarks
- Use smaller n values for initial testing

### Debug Mode

To enable verbose logging, set the environment variable:
```bash
export DEBUG=1
```

## Example Benchmark Output

```
==============================================================
Benchmarking 10^2 = 100 iterations
==============================================================
Testing with 100 iterations
✓ BASE_LOCAL: 9.87 seconds
✓ CASL_CAS: 10.56 seconds
✓ BASE_VIYA: 12.34 seconds

Fastest for 100 iterations: BASE_LOCAL (9.87s)
  CASL_CAS is 7.0% slower
  BASE_VIYA is 25.0% slower
```

## Project Structure

```
c:\sas\kush\
├── config/                 # Configuration files
│   ├── benchmark_config.py # Benchmark configuration presets
│   └── setup.sas          # Common SAS macro definitions
├── data/                   # Input data and authentication
│   ├── sas_tokens.json    # Cached SAS Viya authentication tokens
│   ├── simdata1.csv       # Simulation input data
│   └── simdata2.csv       # Simulation input data
├── programs/              # SAS program files
│   ├── casl_simulation.sas     # CASL simulation program
│   ├── base_simulation.sas     # BASE SAS simulation program (Viya)
│   └── base_local_simulation.sas # BASE SAS simulation program (Local)
├── output/                # Generated SAS output files
│   ├── modsum_base.xlsx   # Summary statistics
│   └── modOC_base.xlsx    # Detailed results
├── results/               # Benchmark results and visualizations
│   ├── sas_environment_benchmark_*.json # Raw benchmark data
│   ├── sas_environment_benchmark_*.csv  # Tabular results
│   ├── sas_environment_performance_*.png # High-resolution charts
│   ├── sas_environment_performance_*.pdf # Publication-quality PDFs
│   ├── base_local_simulation.log # SAS execution logs
│   └── base_local_simulation.lst # SAS listing output
├── sas_base_casl_comparision.py # Single comparison tool
├── sas_environment_benchmark.py # Comprehensive benchmark suite
├── test_benchmark.py      # Quick test script
├── pyproject.toml         # uv project configuration
└── README.md             # This comprehensive guide
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify all prerequisites are met
3. Ensure all file paths are correct for your environment
4. Check the SAS logs for detailed error messages
5. Start with quick tests before running full benchmarks
