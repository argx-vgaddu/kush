#!/usr/bin/env python3
"""
SAS Program Performance Comparison - CASL vs BASE SAS vs LOCAL SAS
Submits CASL, BASE SAS (via Viya), and LOCAL SAS programs to compare performance
"""

import time
import os
import subprocess
from datetime import datetime

# Import authentication and API client from separate module
from sas_auth import SASViyaAuth, SASJobExecutionClient, get_config, get_sas_tokens


def submit_casl_program(client: SASJobExecutionClient):
    """Submit CASL program for simulation processing"""

    # Read local setup file first
    setup_file = "config/setup.sas"
    try:
        with open(setup_file, 'r') as f:
            setup_code = f.read()
    except FileNotFoundError:
        print(f"Error: Could not find setup file: {setup_file}")
        raise

    # Read CASL program from external file
    casl_program_file = "programs/casl_simulation.sas"
    try:
        with open(casl_program_file, 'r') as f:
            casl_program = f.read()
    except FileNotFoundError:
        print(f"Error: Could not find CASL program file: {casl_program_file}")
        raise

    # Concatenate setup code with CASL program
    combined_program = setup_code + "\n\n" + casl_program

    print("\nSubmitting CASL Program...")
    print("=" * 50)

    # Create job definition with combined code
    job_def = client.create_job_definition(
        name="CASL Simulation Program (with local setup)",
        code=combined_program,
        job_type="Compute"
    )

    # Submit job with proper compute context
    job = client.submit_job(
        job_definition_uri=f"/jobDefinitions/definitions/{job_def['id']}",
        name="CASL_Simulation_Job"
        # Note: compute context will be added automatically by submit_job method
    )

    # Wait for completion
    final_job = client.wait_for_completion(job['id'])

    return final_job


def submit_base_sas_program(client: SASJobExecutionClient):
    """Submit BASE SAS program for simulation processing"""

    # Read local setup file first
    setup_file = "config/setup.sas"
    try:
        with open(setup_file, 'r') as f:
            setup_code = f.read()
    except FileNotFoundError:
        print(f"Error: Could not find setup file: {setup_file}")
        raise

    # Read BASE SAS program from external file
    base_sas_program_file = "programs/base_simulation.sas"
    try:
        with open(base_sas_program_file, 'r') as f:
            base_sas_program = f.read()
    except FileNotFoundError:
        print(f"Error: Could not find BASE SAS program file: {base_sas_program_file}")
        raise

    # Concatenate setup code with BASE SAS program
    combined_program = setup_code + "\n\n" + base_sas_program

    print("\nSubmitting BASE SAS Program...")
    print("=" * 50)

    # Create job definition with combined code
    job_def = client.create_job_definition(
        name="BASE SAS Simulation Program (with local setup)",
        code=combined_program,
        job_type="Compute"
    )

    # Submit job with proper compute context
    job = client.submit_job(
        job_definition_uri=f"/jobDefinitions/definitions/{job_def['id']}",
        name="BASE_SAS_Simulation_Job"
        # Note: compute context will be added automatically by submit_job method
    )

    # Wait for completion
    final_job = client.wait_for_completion(job['id'])

    return final_job


def submit_local_sas_program():
    """Submit LOCAL SAS program for simulation using local SAS executable"""

    # SAS executable path and program file
    sas_exe = r"C:\Program Files\SASHome\SASFoundation\9.4\sas.exe"
    sas_program_file = "programs/base_local_simulation.sas"

    print("\nSubmitting LOCAL SAS Program...")
    print("=" * 50)

    # Check if SAS program file exists
    if not os.path.exists(sas_program_file):
        print(f"Error: Could not find LOCAL SAS program file: {sas_program_file}")
        raise FileNotFoundError(f"LOCAL SAS program file not found: {sas_program_file}")

    # Check if SAS executable exists
    if not os.path.exists(sas_exe):
        print(f"Error: Could not find SAS executable: {sas_exe}")
        raise FileNotFoundError(f"SAS executable not found: {sas_exe}")

    # Build SAS command
    cmd = [sas_exe, "-sysin", sas_program_file]

    print(f"Executing: {' '.join(cmd)}")

    # Measure execution time
    start_time = time.time()

    try:
        # Run SAS program
        result = subprocess.run(
            cmd,
            cwd=os.getcwd(),  # Run from current working directory
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout
        )

        end_time = time.time()
        elapsed_time_ms = int((end_time - start_time) * 1000)

        print(f"LOCAL SAS program completed in {elapsed_time_ms} ms")

        # Check for execution errors
        if result.returncode != 0:
            print(f"SAS execution failed with return code: {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, cmd)

        # Parse output for additional information
        stdout_lines = result.stdout.split('\n') if result.stdout else []

        # Create result dictionary similar to Viya job results
        local_result = {
            'id': 'local_sas_run',
            'state': 'completed',
            'elapsedTime': elapsed_time_ms,
            'creationTimeStamp': datetime.fromtimestamp(start_time).isoformat(),
            'endTimeStamp': datetime.fromtimestamp(end_time).isoformat(),
            'results': {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode
            }
        }

        return local_result

    except subprocess.TimeoutExpired:
        print("LOCAL SAS program timed out after 30 minutes")
        raise TimeoutError("LOCAL SAS program execution timed out")
    except subprocess.CalledProcessError as e:
        print(f"LOCAL SAS program failed: {e}")
        raise
    except Exception as e:
        print(f"Error running LOCAL SAS program: {e}")
        raise


def display_local_sas_results(local_result: dict):
    """Display LOCAL SAS execution results"""
    print(f"\nLOCAL SAS Simulation Results:")
    print("=" * 60)
    print(f"Job ID: {local_result['id']}")
    print(f"Final State: {local_result['state']}")
    print(f"Elapsed Time: {local_result.get('elapsedTime', 'N/A')} ms")
    print(f"Creation Time: {local_result.get('creationTimeStamp', 'N/A')}")
    print(f"End Time: {local_result.get('endTimeStamp', 'N/A')}")

    if local_result.get('results'):
        results = local_result['results']
        print(f"Return Code: {results.get('return_code', 'N/A')}")
        print(f"Output Length: {len(results.get('stdout', ''))} characters")

        # Check if output files were created
        output_files = [
            "output/modsum_base.xlsx",
            "output/modOC_base.xlsx"
        ]

        for output_file in output_files:
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"Output file created: {output_file} ({file_size} bytes)")
            else:
                print(f"Output file not found: {output_file}")


def display_job_results(job_type: str, job_result: dict):
    """Display job execution results"""
    print(f"\n{job_type} Simulation Results:")
    print("=" * 60)
    print(f"Job ID: {job_result['id']}")
    print(f"Final State: {job_result['state']}")
    print(f"Elapsed Time: {job_result.get('elapsedTime', 'N/A')} ms")
    print(f"Creation Time: {job_result.get('creationTimeStamp', 'N/A')}")
    print(f"End Time: {job_result.get('endTimeStamp', 'N/A')}")

    if job_result.get('results'):
        print(f"Results Available: {list(job_result['results'].keys())}")
        print(f"Number of Result Objects: {len(job_result['results'])}")


if __name__ == "__main__":
    print("SAS Program Performance Comparison: CASL vs BASE SAS vs LOCAL SAS")
    print("=" * 70)

    try:
        # Get authenticated session
        tokens = get_sas_tokens()
        access_token = tokens['access_token']

        print(f"Authentication successful!")
        print(f"Access Token: {access_token[:50]}...")

        # Create job execution client
        config = get_config()
        client = SASJobExecutionClient(config["base_url"], access_token)

        # Submit CASL program
        casl_result = submit_casl_program(client)
        display_job_results("CASL", casl_result)

        # Submit BASE SAS program
        base_sas_result = submit_base_sas_program(client)
        display_job_results("BASE SAS", base_sas_result)

        # Submit LOCAL SAS program
        local_sas_result = submit_local_sas_program()
        display_local_sas_results(local_sas_result)

        # Compare execution times
        print(f"\nPerformance Comparison:")
        print("=" * 60)
        casl_time = casl_result.get('elapsedTime', 0)
        base_sas_time = base_sas_result.get('elapsedTime', 0)
        local_sas_time = local_sas_result.get('elapsedTime', 0)

        print(f"CASL Execution Time: {casl_time} ms")
        print(f"BASE SAS Execution Time: {base_sas_time} ms")
        print(f"LOCAL SAS Execution Time: {local_sas_time} ms")

        # Compare all three
        times = [
            ("CASL", casl_time),
            ("BASE SAS", base_sas_time),
            ("LOCAL SAS", local_sas_time)
        ]

        # Filter out zero times
        valid_times = [(name, time) for name, time in times if time > 0]

        if len(valid_times) >= 2:
            # Find fastest
            fastest_name, fastest_time = min(valid_times, key=lambda x: x[1])

            print(f"\nFastest execution: {fastest_name} ({fastest_time} ms)")

            # Compare each to fastest
            for name, time in valid_times:
                if name != fastest_name:
                    diff_percent = ((time - fastest_time) / fastest_time) * 100
                    print(f"{name} was {diff_percent:.1f}% slower than {fastest_name}")
        else:
            print("Insufficient data for performance comparison")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()