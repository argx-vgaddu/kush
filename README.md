# SAS Program Performance Comparison Tool

This tool compares the performance of different SAS program execution methods:
- **CASL** (Cloud Analytic Services Language) via SAS Viya
- **BASE SAS** via SAS Viya
- **LOCAL SAS** using local SAS installation

## Features

- **Multi-platform execution**: Run the same SAS simulation program across different environments
- **Centralized configuration**: Local `setup.sas` file automatically concatenated to server programs
- **Performance benchmarking**: Compare execution times between CASL, BASE SAS, and LOCAL SAS
- **Comprehensive logging**: Detailed execution statistics and output file verification
- **Error handling**: Robust error handling for all execution methods

## Prerequisites

### 1. Python Environment
- Python 3.8 or higher
- `uv` package manager (recommended)
- Required Python packages (automatically installed via `uv`):
  - `requests`
  - `python-dotenv`

### 2. SAS Environment
- **SAS Viya access** (for CASL and BASE SAS via Viya):
  - Valid SAS Viya credentials
  - Access to SAS Job Execution API
  - **Note**: The Python script automatically concatenates the local `setup.sas` file with the server programs
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

### Option 1: Using uv directly (Recommended)

```bash
# Run the comparison script
uv run python sas_base_casl_comparision.py

# Or using the py launcher with uv
py -m uv run python sas_base_casl_comparision.py
```

### Option 2: Using traditional Python

```bash
# If you have the dependencies installed in your environment
python sas_base_casl_comparision.py
```

### Option 3: Using uv run with specific Python version

```bash
uv run --python 3.11 python sas_base_casl_comparision.py
```

## What the Tool Does

1. **Authentication**: Connects to SAS Viya using OAuth2 flow
2. **Program Preparation**:
   - Automatically concatenates local `setup.sas` with server programs
   - Prepares combined code for SAS Viya submission
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

The SAS programs generate the following output files in the `output/` directory:
- `modsum_base.xlsx` - Summary statistics by decision region
- `modOC_base.xlsx` - Detailed simulation results

## Troubleshooting

### Common Issues

1. **SAS Viya Authentication Failed**
   - Verify your credentials in the `.env` file
   - Ensure your SAS Viya server URL is correct
   - Check network connectivity to SAS Viya

2. **Local SAS Not Found**
   - Verify SAS 9.4 is installed at the specified path
   - Check if `sas.exe` exists in `C:\Program Files\SASHome\SASFoundation\9.4\`

3. **Permission Errors**
   - Ensure the current user has execute permissions for SAS
   - Check write permissions for the `output/` directory

4. **Python Dependencies**
   - Run `uv sync` to install all required packages
   - Ensure `uv` is properly installed and in your PATH

### Debug Mode

To enable verbose logging, set the environment variable:
```bash
export DEBUG=1
```

## Project Structure

```
c:\sas\kush\
├── data\                    # Input data and SAS tokens
│   └── sas_tokens.json     # Cached SAS Viya authentication tokens
├── programs\               # SAS program files
│   ├── casl_simulation.sas     # CASL simulation program
│   ├── base_simulation.sas     # BASE SAS simulation program (Viya)
│   └── base_local_simulation.sas # BASE SAS simulation program (Local)
├── output\                 # Generated output files
│   ├── modsum_base.xlsx    # Summary statistics
│   └── modOC_base.xlsx     # Detailed results
├── sas_base_casl_comparision.py # Main Python comparison tool
├── setup.sas               # Common SAS macro definitions
├── pyproject.toml          # uv project configuration
└── README.md              # This file
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify all prerequisites are met
3. Ensure all file paths are correct for your environment
4. Check the SAS logs for detailed error messages
