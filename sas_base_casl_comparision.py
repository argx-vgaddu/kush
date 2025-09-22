#!/usr/bin/env python3
"""
SAS Program Performance Comparison - CASL vs BASE SAS vs LOCAL SAS
Submits CASL, BASE SAS (via Viya), and LOCAL SAS programs to compare performance
"""

import requests
import json
import time
import os
import subprocess
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SASViyaAuth:
    """Minimal SAS Viya authentication with automatic token management"""

    def __init__(self, base_url, client_id, client_secret, username=None):
        self.base_url = base_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret  # OAuth client secret
        self.password = client_secret  # Keep for backward compatibility
        self.username = username  # Optional: actual user credentials if needed
        self.tokens = {}

        # OAuth endpoints
        self.auth_url = f"{self.base_url}/SASLogon/oauth/authorize"
        self.token_url = f"{self.base_url}/SASLogon/oauth/token"

    def authenticate(self, save_tokens=True):
        """Complete OAuth flow and return access token"""
        try:
            # Get authorization code via browser
            auth_code = self._get_authorization_code()

            # Exchange for tokens
            tokens = self._exchange_code_for_tokens(auth_code)

            # Save tokens if requested
            if save_tokens:
                self._save_tokens()

            return self.tokens

        except Exception as e:
            print(f"Authentication failed: {e}")
            raise

    def _get_authorization_code(self):
        """Get authorization code via browser (manual URL capture)"""
        import urllib.parse
        import webbrowser

        print("Starting OAuth authorization flow...")

        # Build authorization URL
        auth_params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'scope': 'openid'
        }

        auth_url = f"{self.auth_url}?{urllib.parse.urlencode(auth_params)}"

        print(f"Authorization URL: {auth_url}")
        print("Opening browser for authorization...")
        webbrowser.open(auth_url)

        print("\n" + "="*60)
        print("MANUAL STEP REQUIRED:")
        print("1. Complete the login process in your browser")
        print("2. After login, you'll be redirected to an error page")
        print("3. Look at the URL in your browser - it will contain 'code=...'")
        print("4. Copy the authorization code from the URL")
        print("="*60 + "\n")

        # Prompt user to enter the authorization code manually
        while True:
            try:
                auth_code = input("Please paste the authorization code from the URL: ").strip()

                if not auth_code:
                    print("Please enter a valid authorization code")
                    continue

                # Basic validation
                if len(auth_code) < 10:
                    print("Authorization code seems too short. Please check and try again.")
                    continue

                print(f"Authorization code received: {auth_code[:20]}...")
                return auth_code

            except KeyboardInterrupt:
                print("\nAuthorization cancelled by user")
                raise
            except Exception as e:
                print(f"Error reading authorization code: {e}")
                continue

    def _exchange_code_for_tokens(self, authorization_code):
        """Exchange authorization code for tokens"""
        print("Exchanging authorization code for tokens...")

        token_data = {
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'client_id': self.client_id
        }

        # Use actual user credentials for HTTP Basic Auth
        auth = (self.username, self.password)

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        try:
            response = requests.post(
                self.token_url,
                data=token_data,
                auth=auth,
                headers=headers,
                timeout=30
            )

            print(f"Token request status: {response.status_code}")

            if response.status_code == 200:
                self.tokens = response.json()

                # Add expiration times
                now = datetime.now()
                if 'expires_in' in self.tokens:
                    self.tokens['expires_at'] = (now + timedelta(seconds=self.tokens['expires_in'])).isoformat()
                if 'refresh_expires_in' in self.tokens:
                    self.tokens['refresh_expires_at'] = (now + timedelta(seconds=self.tokens['refresh_expires_in'])).isoformat()

                print("Tokens received successfully!")
                return self.tokens
            else:
                print(f"Token request failed: {response.status_code}")
                print(f"Response: {response.text}")
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            print(f"Error during token exchange: {e}")
            raise

    def get_valid_access_token(self):
        """Get a valid access token, refreshing if necessary"""
        if not self.tokens:
            return None

        # Check if token is expired
        if 'expires_at' in self.tokens:
            expires_at = datetime.fromisoformat(self.tokens['expires_at'])
            if datetime.now() >= expires_at - timedelta(minutes=5):  # Refresh 5 minutes before expiry
                try:
                    self._refresh_access_token()
                except Exception as e:
                    print(f"Failed to refresh token: {e}")
                    return None

        return self.tokens.get('access_token')

    def _refresh_access_token(self):
        """Refresh the access token using refresh token"""
        if not self.tokens or 'refresh_token' not in self.tokens:
            raise ValueError("No refresh token available")

        print("Refreshing access token...")

        refresh_data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.tokens['refresh_token'],
            'client_id': self.client_id
        }

        # Use actual user credentials for HTTP Basic Auth
        auth = (self.username, self.password)

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        try:
            response = requests.post(
                self.token_url,
                data=refresh_data,
                auth=auth,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                new_tokens = response.json()

                # Update tokens
                self.tokens.update(new_tokens)

                # Update expiration times
                now = datetime.now()
                if 'expires_in' in new_tokens:
                    self.tokens['expires_at'] = (now + timedelta(seconds=new_tokens['expires_in'])).isoformat()

                print("Access token refreshed successfully!")
                self._save_tokens()  # Save the refreshed tokens to file
                return self.tokens
            else:
                print(f"Token refresh failed: {response.status_code}")
                print(f"Response: {response.text}")
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            print(f"Error during token refresh: {e}")
            raise

    def _save_tokens(self, filename='data/sas_tokens.json'):
        """Save tokens to file"""
        # Ensure data directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        if self.tokens:
            with open(filename, 'w') as f:
                json.dump(self.tokens, f, indent=2)
            print(f"Tokens saved to {filename}")

    def load_tokens(self, filename='data/sas_tokens.json'):
        """Load tokens from file"""
        try:
            with open(filename, 'r') as f:
                self.tokens = json.load(f)
            print(f"Tokens loaded from {filename}")
            return True
        except FileNotFoundError:
            print(f"No saved tokens found at {filename}")
            return False
        except Exception as e:
            print(f"Error loading tokens: {e}")
            return False


class SASJobExecutionClient:
    """Minimal client for SAS Viya Job Execution API"""

    def __init__(self, base_url: str, access_token: str):
        """Initialize the Job Execution client"""
        self.base_url = base_url.rstrip('/')
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

        # API endpoints
        self.job_execution_base = f"{self.base_url}/jobExecution"
        self.jobs_endpoint = f"{self.job_execution_base}/jobs"
        self.job_requests_endpoint = f"{self.job_execution_base}/jobRequests"
        self.job_definitions_endpoint = f"{self.base_url}/jobDefinitions/definitions"
        self.compute_contexts_endpoint = f"{self.base_url}/compute/contexts"
        
        # Cache for compute context
        self._compute_context_id = None

    def create_job_definition(self, name: str, code: str, job_type: str = "Compute",
                            parameters: list = None) -> dict:
        """Create a job definition"""
        if parameters is None:
            parameters = []

        job_definition = {
            "version": 1,
            "name": name,
            "type": job_type,
            "parameters": parameters,
            "code": code
        }

        try:
            response = self.session.post(
                self.job_definitions_endpoint,
                json=job_definition,
                headers={
                    'Content-Type': 'application/vnd.sas.job.definition+json',
                    'Accept': 'application/vnd.sas.job.definition+json'
                }
            )
            response.raise_for_status()

            created_definition = response.json()
            print(f"Job definition created with ID: {created_definition.get('id')}")
            return created_definition

        except requests.exceptions.RequestException as e:
            print(f"Failed to create job definition: {e}")
            raise
    
    def get_compute_contexts(self):
        """Get available compute contexts"""
        try:
            response = self.session.get(
                self.compute_contexts_endpoint,
                headers={'Accept': 'application/vnd.sas.collection+json'}
            )
            
            if response.status_code == 200:
                contexts = response.json()
                return contexts.get('items', [])
            else:
                print(f"Failed to get compute contexts: {response.status_code}")
                return []
        except Exception as e:
            print(f"Error getting compute contexts: {e}")
            return []
    
    def get_default_compute_context(self):
        """Get the default compute context ID"""
        if self._compute_context_id:
            return self._compute_context_id
            
        contexts = self.get_compute_contexts()
        
        # Look for SAS Job Execution context or default context
        for context in contexts:
            context_name = context.get('name', '')
            if 'job execution' in context_name.lower() or 'default' in context_name.lower():
                self._compute_context_id = context.get('id')
                print(f"Using compute context: {context_name} (ID: {self._compute_context_id})")
                return self._compute_context_id
        
        # If no default found, use the first available context
        if contexts:
            self._compute_context_id = contexts[0].get('id')
            print(f"Using first available compute context: {contexts[0].get('name')} (ID: {self._compute_context_id})")
            return self._compute_context_id
        
        print("Warning: No compute contexts found")
        return None

    def submit_job(self, job_definition_uri: str = None, job_definition: dict = None,
                   name: str = None, arguments: dict = None) -> dict:
        """Submit a job for execution"""
        # Build job request
        job_request = {}

        if name:
            job_request["name"] = name

        # Ensure we have compute context in arguments
        if arguments is None:
            arguments = {}
        
        # Add compute context if not already present
        if '_contextId' not in arguments and '_contextName' not in arguments and '_sessionId' not in arguments:
            context_id = self.get_default_compute_context()
            if context_id:
                arguments['_contextId'] = context_id
            else:
                # Fallback to context name if ID not available
                arguments['_contextName'] = 'SAS Job Execution compute context'
        
        if arguments:
            job_request["arguments"] = arguments

        # Either use job definition URI or embed definition
        if job_definition_uri:
            job_request["jobDefinitionUri"] = job_definition_uri
        elif job_definition:
            job_request["jobDefinition"] = job_definition
        else:
            raise ValueError("Must provide either job_definition_uri or job_definition")

        try:
            response = self.session.post(
                self.jobs_endpoint,
                json=job_request,
                headers={
                    'Content-Type': 'application/vnd.sas.job.execution.job.request+json',
                    'Accept': 'application/vnd.sas.job.execution.job+json'
                }
            )

            if response.status_code not in [201, 200]:
                print(f"Job submission failed with status {response.status_code}")
                print(f"Response text: {response.text}")
                response.raise_for_status()

            job = response.json()
            job_id = job.get('id')
            print(f"Job submitted successfully with ID: {job_id}")
            print(f"Job state: {job.get('state')}")

            return job

        except requests.exceptions.RequestException as e:
            print(f"Failed to submit job: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response text: {e.response.text}")
            raise

    def wait_for_completion(self, job_id: str, timeout: int = 300, poll_interval: int = 5) -> dict:
        """Wait for job completion with polling"""
        print(f"Monitoring job {job_id} for completion...")

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                state = self.get_job_state(job_id)
                print(f"Job {job_id} state: {state}")

                if state in ['completed', 'failed', 'cancelled']:
                    # Get final job details
                    job = self.get_job_details(job_id)

                    if state == 'completed':
                        print(f"Job {job_id} completed successfully")
                    elif state == 'failed':
                        print(f"Job {job_id} failed")
                    else:
                        print(f"Job {job_id} was cancelled")

                    return job

                time.sleep(poll_interval)

            except Exception as e:
                print(f"Error checking job status: {e}")
                time.sleep(poll_interval)

        # Timeout reached
        print(f"Timeout waiting for job {job_id} to complete")
        raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")

    def get_job_state(self, job_id: str) -> str:
        """Get the current state of a job"""
        try:
            response = self.session.get(
                f"{self.jobs_endpoint}/{job_id}/state",
                headers={'Accept': 'text/plain'}
            )
            response.raise_for_status()

            state = response.text.strip()
            return state

        except requests.exceptions.RequestException as e:
            print(f"Failed to get job state: {e}")
            raise

    def get_job_details(self, job_id: str) -> dict:
        """Get complete job details"""
        try:
            response = self.session.get(
                f"{self.jobs_endpoint}/{job_id}",
                headers={'Accept': 'application/vnd.sas.job.execution.job+json'}
            )
            response.raise_for_status()

            job = response.json()
            return job

        except requests.exceptions.RequestException as e:
            print(f"Failed to get job details: {e}")
            raise


def get_config():
    """Get SAS configuration from environment variables"""
    return {
        "base_url": os.getenv("SAS_BASE_URL", "https://xarprodviya.ondemand.sas.com"),
        "client_id": os.getenv("SAS_CLIENT_ID", "xar_api"),
        "username": os.getenv("SAS_USERNAME"),
        "password": os.getenv("SAS_PASSWORD"),
        "scope": os.getenv("SAS_SCOPE", "openid"),
        "token_file": os.getenv("SAS_TOKEN_FILE", "data/sas_tokens.json")
    }


def get_sas_tokens():
    """Get SAS tokens with automatic refresh - main entry point"""
    config = get_config()

    auth_client = SASViyaAuth(
        base_url=config["base_url"],
        client_id=config["client_id"],
        client_secret=config["password"],
        username=config["username"]
    )

    # Try to load existing tokens first
    if auth_client.load_tokens():
        access_token = auth_client.get_valid_access_token()
        if access_token:
            return auth_client.tokens

    # If no valid tokens, start fresh authentication
    return auth_client.authenticate()


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