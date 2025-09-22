# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a SAS program performance comparison framework that benchmarks execution between three different SAS execution methods:
- **CASL** (Cloud Analytic Services Language) via SAS Viya
- **BASE SAS** via SAS Viya
- **LOCAL SAS** using local SAS installation

The framework focuses on adaptive clinical trial simulations with conditional power calculations, comparing performance across different execution environments. The system uses a centralized configuration approach where a local `setup.sas` file containing common macro definitions is automatically concatenated with server programs during execution.

## Key Commands

### Development Setup
```bash
# Install dependencies
uv sync

# Run the performance comparison (primary command)
py -m uv run python sas_base_casl_comparision.py

# Alternative execution methods
uv run python sas_base_casl_comparision.py
python sas_base_casl_comparision.py  # if dependencies already installed
```

### Testing Individual Components
```bash
# Test SAS Viya connection only
py -m uv run sas_viya_test.py

# Run local SAS simulation standalone
"C:\Program Files\SASHome\SASFoundation\9.4\sas.exe" -sysin ./programs/base_local_simulation.sas
```

## Architecture Overview

### Core Components

**Python Framework (`sas_base_casl_comparision.py`)**
- `SASViyaAuth`: Handles OAuth2 authentication with automatic token refresh
- `SASJobExecutionClient`: Manages SAS Viya job submission and monitoring
- `submit_local_sas_program()`: Executes local SAS programs via subprocess
- **Automatic Setup Integration**: Reads `setup.sas` and concatenates it with server programs before submission

**SAS Programs (programs/ directory)**
- `casl_simulation.sas`: CASL implementation using CAS-specific actions and distributed processing
- `base_simulation.sas`: BASE SAS implementation for SAS Viya execution
- `base_local_simulation.sas`: BASE SAS implementation for local execution (includes setup.sas via %include)
- All programs implement equivalent adaptive clinical trial simulation algorithms with two-stage design

**Configuration & Data**
- `.env`: SAS Viya credentials (SAS_BASE_URL, SAS_CLIENT_ID, SAS_USERNAME, SAS_PASSWORD)
- `data/sas_tokens.json`: Cached authentication tokens
- `data/simdata*.csv`: Input correlation structures for multivariate normal simulation
- `setup.sas`: Centralized macro variable definitions (sample sizes, statistical boundaries, file paths)

### Execution Flow

1. **Authentication**: OAuth2 flow with SAS Viya (automatic token management)
2. **Program Preparation**:
   - Python script reads `setup.sas` containing common macro definitions
   - For CASL and BASE SAS (Viya): concatenates setup.sas with program files
   - For LOCAL SAS: program includes setup.sas via %include directive
3. **Program Submission**:
   - CASL and BASE SAS programs submitted to SAS Viya via REST API with combined code
   - LOCAL SAS executed via subprocess
4. **Monitoring**: Real-time job status polling for Viya jobs
5. **Results Collection**: Performance metrics and output file verification
6. **Comparison**: Side-by-side performance analysis across all three execution methods

### File Paths & Data Flow

- **Input**: CSV files from `/xar/general/biostat/jobs/gadam_ongoing_studies/prod/programs/vgaddu/CASL/data/`
- **Output**: Excel files generated in `output/` directory
  - `modsum_base.xlsx` / `modsum_casl.xlsx`: Summary statistics by decision region
  - `modOC_base.xlsx` / `modOC_casl.xlsx`: Detailed simulation results
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

## Program Expansion Guidelines

When adding complexity to SAS programs:

1. **Centralized Configuration**: Add new macro variables to `setup.sas` rather than duplicating across programs
2. **Maintain Separation**: Keep CASL, BASE SAS (Viya), and LOCAL SAS implementations in separate files
3. **Consistent Algorithm**: Ensure all three implementations produce equivalent statistical results
4. **Environment-Specific Adaptations**:
   - CASL programs use CAS actions (table.loadTable, proc cas, caslib references)
   - BASE SAS programs use traditional procedures (proc import, work library)
   - LOCAL SAS includes setup.sas via %include directive
5. **Output Standardization**: All programs should generate comparable output files for verification
6. **Setup Integration**: Remember that Viya programs automatically get setup.sas prepended by Python framework

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
- Python framework automatically concatenates this with Viya programs
- Local SAS programs include via `%include "setup.sas";`
- Ensures consistent parameterization across all execution methods

## Common Workflow

1. Modify simulation parameters in `setup.sas` for consistent changes across all methods
2. Update SAS programs in `programs/` directory for algorithm changes
3. Update input data in `data/` directory if required
4. Run performance comparison: `py -m uv run python sas_base_casl_comparision.py`
5. Review results and generated output files in `output/`
6. Analyze performance differences between execution methods