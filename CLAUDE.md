# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a SAS environment performance benchmark suite that compares SAS simulation execution across three different environments:
- **CASL on CAS Server** - In-memory analytics using CAS Action Language
- **BASE SAS on Viya Compute** - Traditional SAS on Viya compute server
- **BASE SAS Local** - Local SAS installation

The framework focuses on adaptive clinical trial simulations with conditional power calculations, comparing performance across different execution environments. The system uses a centralized configuration approach where a local `config/setup.sas` file containing common macro definitions is automatically concatenated with server programs during execution.

## Key Commands

### Development Setup
```bash
# Install dependencies
uv sync
```

### Primary Benchmark Commands
```bash
# Quick test with minimal iterations (1, 10) - ~1 minute
py -m uv run test_benchmark.py

# Full benchmark with default configuration [1, 10, 100, 1000, 10000] iterations
py -m uv run sas_environment_benchmark.py

# Configuration presets
py -m uv run python config/benchmark_config.py quick   # 1, 10 iterations
py -m uv run python config/benchmark_config.py small   # 1, 10, 100 iterations
py -m uv run python config/benchmark_config.py medium  # 1, 10, 100, 1000 iterations
py -m uv run python config/benchmark_config.py full    # 1, 10, 100, 1000, 10000 iterations
```

### Single Comparison Commands
```bash
# Single comparison run (legacy)
py -m uv run python sas_base_casl_comparision.py

# Alternative execution methods
uv run python sas_base_casl_comparision.py
python sas_base_casl_comparision.py  # if dependencies already installed
```

### Testing Individual Components
```bash
# Run local SAS simulation standalone
"C:\Program Files\SASHome\SASFoundation\9.4\sas.exe" -sysin ./programs/base_local_simulation.sas
```

## Architecture Overview

### Core Components

**Python Framework**
- `sas_environment_benchmark.py`: Main benchmark suite with configurable iteration counts
- `sas_base_casl_comparision.py`: Single comparison tool (legacy)
- `test_benchmark.py`: Quick validation script
- `sas_auth.py`: Authentication and API client module containing:
  - `SASViyaAuth`: Handles OAuth2 authentication with automatic token refresh
  - `SASJobExecutionClient`: Manages SAS Viya job submission and monitoring
  - `get_config()`: Environment configuration management
  - `get_sas_tokens()`: Main authentication entry point
- `submit_local_sas_program()`: Executes local SAS programs via subprocess
- **Automatic Setup Integration**: Reads `config/setup.sas` and concatenates it with server programs before submission
- **Compute Context Management**: Automatically retrieves and uses SAS Viya compute contexts

**SAS Programs (programs/ directory)**
- `casl_simulation.sas`: CASL implementation using CAS-specific actions and distributed processing
- `base_simulation.sas`: BASE SAS implementation for SAS Viya execution
- `base_local_simulation.sas`: BASE SAS implementation for local execution (includes setup.sas via %include)
- All programs implement equivalent adaptive clinical trial simulation algorithms with two-stage design

**Configuration & Data**
- `config/setup.sas`: Centralized macro variable definitions (sample sizes, statistical boundaries, file paths)
- `config/benchmark_config.py`: Benchmark configuration presets (quick, small, medium, full)
- `.env`: SAS Viya credentials (SAS_BASE_URL, SAS_CLIENT_ID, SAS_USERNAME, SAS_PASSWORD)
- `data/sas_tokens.json`: Cached authentication tokens
- `data/simdata*.csv`: Input correlation structures for multivariate normal simulation

**Output Directories**
- `output/`: SAS program output files (Excel files from simulations)
- `results/`: Benchmark results (JSON, CSV, PNG, PDF visualizations and logs)

### Execution Flow

1. **Authentication**: OAuth2 flow with SAS Viya (automatic token management)
2. **Compute Context Setup**: Automatically retrieves available compute contexts from SAS Viya
3. **Program Preparation**:
   - Python script reads `config/setup.sas` containing common macro definitions
   - For CASL and BASE SAS (Viya): concatenates setup.sas with program files
   - For LOCAL SAS: program includes setup.sas via %include directive
4. **Benchmark Execution** (for benchmark suite):
   - Iterates through configured n values (iterations = 10^n)
   - Runs all three execution methods for each iteration count
   - Measures execution times and collects performance data
5. **Program Submission**:
   - CASL and BASE SAS programs submitted to SAS Viya via REST API with combined code
   - LOCAL SAS executed via subprocess
6. **Monitoring**: Real-time job status polling for Viya jobs
7. **Results Collection**: Performance metrics, output file verification, and data visualization
8. **Output Generation**: Creates JSON, CSV, PNG, and PDF reports in `results/` directory

### File Paths & Data Flow

- **Input**: CSV files from `/xar/general/biostat/jobs/gadam_ongoing_studies/prod/programs/vgaddu/CASL/data/`
- **SAS Output**: Excel files generated in `output/` directory
  - `modsum_base.xlsx` / `modsum_casl.xlsx`: Summary statistics by decision region
  - `modOC_base.xlsx` / `modOC_casl.xlsx`: Detailed simulation results
- **Benchmark Output**: Generated in `results/` directory
  - `sas_environment_benchmark_YYYYMMDD_HHMMSS.json`: Raw benchmark data
  - `sas_environment_benchmark_YYYYMMDD_HHMMSS.csv`: Tabular results
  - `sas_environment_performance_YYYYMMDD_HHMMSS.png`: High-resolution charts
  - `sas_environment_performance_YYYYMMDD_HHMMSS.pdf`: Publication-quality PDFs
- **Logs**: SAS execution logs captured for all three execution methods

## Configuration Requirements

### Environment Variables (.env file)
```
SAS_BASE_URL=https://your-sas-viya-server.com
SAS_CLIENT_ID=your_client_id
SAS_USERNAME=your_username
SAS_PASSWORD=your_password
```

### System Dependencies
- Python 3.8+ with `uv` package manager
- SAS 9.4 installed at `C:\Program Files\SASHome\SASFoundation\9.4\sas.exe` (for LOCAL SAS execution)
- Network access to SAS Viya server
- Write permissions to `output/` directory

## Benchmark Configuration

### N Values and Iteration Mapping
The benchmark uses `n` values where iterations = 10^n:

| n value | Iterations | Typical Runtime |
|---------|------------|-----------------|
| 0       | 1          | ~1 second       |
| 1       | 10         | ~3 seconds      |
| 2       | 100        | ~30 seconds     |
| 3       | 1000       | ~5 minutes      |
| 4       | 10000      | ~50 minutes     |

### Configuration Presets
- `QUICK_TEST = [0, 1]`: Fast validation (1, 10 iterations)
- `SMALL_BENCHMARK = [0, 1, 2]`: Small test (1, 10, 100 iterations)
- `MEDIUM_BENCHMARK = [0, 1, 2, 3]`: Medium test (1, 10, 100, 1000 iterations)
- `FULL_BENCHMARK = [0, 1, 2, 3, 4]`: Complete test (1, 10, 100, 1000, 10000 iterations)

## Program Expansion Guidelines

When adding complexity to SAS programs:

1. **Centralized Configuration**: Add new macro variables to `config/setup.sas` rather than duplicating across programs
2. **Maintain Separation**: Keep CASL, BASE SAS (Viya), and LOCAL SAS implementations in separate files
3. **Consistent Algorithm**: Ensure all three implementations produce equivalent statistical results
4. **Environment-Specific Adaptations**:
   - CASL programs use CAS actions (table.loadTable, proc cas, caslib references)
   - BASE SAS programs use traditional procedures (proc import, work library)
   - LOCAL SAS includes config/setup.sas via %include directive
5. **Output Standardization**: All programs should generate comparable output files for verification
6. **Setup Integration**: Remember that Viya programs automatically get config/setup.sas prepended by Python framework

## Performance Considerations

- CASL programs leverage CAS (Cloud Analytic Services) for distributed processing
- BASE SAS programs use traditional SAS procedures
- LOCAL SAS provides baseline performance comparison
- The framework measures end-to-end execution time including job submission overhead for Viya-based methods

## Key Implementation Details

### Adaptive Clinical Trial Simulation
The programs implement a two-stage adaptive design with:
- **Stage 1**: Fixed sample size with interim analysis
- **Conditional Power**: Calculation to determine next steps (futile, unfavorable, promising, favorable, efficacious zones)
- **Stage 2**: Potentially adapted sample size based on interim results
- **Final Analysis**: Combined test statistic using Hwang-Shih-DeCani boundaries

### Setup.sas Integration
- Contains simulation parameters (sample sizes, statistical boundaries, random seeds)
- Python framework automatically concatenates `config/setup.sas` with Viya programs
- Local SAS programs include via `%include "config/setup.sas";`
- Ensures consistent parameterization across all execution methods

## Common Workflows

### Quick Validation Workflow
1. Run quick test: `py -m uv run test_benchmark.py`
2. Verify all three execution methods work correctly
3. Check output files are generated in `output/` and `results/`

### Benchmark Analysis Workflow
1. Choose appropriate benchmark size based on time constraints
2. Run benchmark: `py -m uv run python config/benchmark_config.py [quick|small|medium|full]`
3. Review generated visualizations in `results/` directory
4. Analyze performance scaling across iteration counts

### Development Workflow
1. Modify simulation parameters in `config/setup.sas` for consistent changes across all methods
2. Update SAS programs in `programs/` directory for algorithm changes
3. Update input data in `data/` directory if required
4. Test changes with quick benchmark: `py -m uv run test_benchmark.py`
5. Run full analysis when ready: `py -m uv run sas_environment_benchmark.py`

### Legacy Single Comparison
1. Run single comparison: `py -m uv run python sas_base_casl_comparision.py`
2. Review console output for immediate performance comparison