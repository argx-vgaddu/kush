#!/usr/bin/env python3
"""
SAS Viya Authentication and API Client Module

This module provides authentication and API client functionality for SAS Viya,
including OAuth2 authentication, token management, and job execution capabilities.
"""

import requests
import json
import time
import os
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

    def get_compute_contexts(self):
        """Get available compute contexts"""
        try:
            response = self.session.get(self.compute_contexts_endpoint, timeout=30)

            if response.status_code == 200:
                contexts = response.json()
                print(f"Found {len(contexts.get('items', []))} compute context(s)")
                return contexts.get('items', [])
            else:
                print(f"Failed to get compute contexts: {response.status_code}")
                print(f"Response: {response.text}")
                return []

        except requests.exceptions.RequestException as e:
            print(f"Error getting compute contexts: {e}")
            return []

    def get_context_id(self):
        """Get the appropriate compute context ID"""
        contexts = self.get_compute_contexts()

        if not contexts:
            print("No compute contexts found")
            return None

        # Look for specific context types in order of preference
        for preferred_name in ["Job Execution compute context", "default"]:
            for context in contexts:
                if context.get('name', '').lower() == preferred_name.lower():
                    context_id = context.get('id')
                    print(f"Using compute context: {context.get('name')} (ID: {context_id})")
                    return context_id

        # If no preferred context found, use the first available
        first_context = contexts[0]
        context_id = first_context.get('id')
        print(f"Using first available compute context: {first_context.get('name')} (ID: {context_id})")
        return context_id

    def submit_job(self, code: str, job_name: str = "SAS Job") -> dict:
        """Submit a SAS job and return job details"""
        context_id = self.get_context_id()
        if not context_id:
            raise ValueError("No compute context available for job execution")

        job_request = {
            "name": job_name,
            "description": f"Submitted job: {job_name}",
            "jobDefinition": {
                "type": "Compute",
                "parameters": [
                    {
                        "name": "_contextId",
                        "value": context_id
                    }
                ],
                "code": code
            }
        }

        try:
            print(f"Submitting job: {job_name}")
            response = self.session.post(
                self.job_requests_endpoint,
                json=job_request,
                timeout=30
            )

            if response.status_code in [200, 201, 202]:
                job_data = response.json()
                print(f"Job submitted successfully with ID: {job_data.get('id', 'unknown')}")
                return job_data
            else:
                print(f"Job submission failed: {response.status_code}")
                print(f"Response: {response.text}")
                response.raise_for_status()

        except requests.exceptions.RequestException as e:
            print(f"Error submitting job: {e}")
            raise

    def wait_for_job_completion(self, job_id: str, timeout: int = 300) -> dict:
        """Wait for job completion and return final status"""
        start_time = time.time()
        job_url = f"{self.jobs_endpoint}/{job_id}"

        print(f"Monitoring job {job_id}...")

        while time.time() - start_time < timeout:
            try:
                response = self.session.get(job_url, timeout=30)

                if response.status_code == 200:
                    job_data = response.json()
                    state = job_data.get('state', 'unknown')

                    print(f"Job state: {state}")

                    if state in ['completed', 'failed', 'canceled']:
                        print(f"Job finished with state: {state}")
                        return job_data

                    # Wait before next check
                    time.sleep(2)
                else:
                    print(f"Error checking job status: {response.status_code}")
                    break

            except requests.exceptions.RequestException as e:
                print(f"Error monitoring job: {e}")
                break

        # Timeout reached
        print(f"Job monitoring timed out after {timeout} seconds")
        response = self.session.get(job_url, timeout=30)
        return response.json() if response.status_code == 200 else {}


def get_config():
    """Get configuration from environment variables"""
    config = {
        'base_url': os.getenv('SAS_BASE_URL'),
        'client_id': os.getenv('SAS_CLIENT_ID'),
        'username': os.getenv('SAS_USERNAME'),
        'password': os.getenv('SAS_PASSWORD')
    }

    # Validate required config
    missing_vars = [k for k, v in config.items() if not v]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")

    return config


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

    # If no valid tokens, start authentication flow
    print("No valid tokens found. Starting authentication flow...")
    return auth_client.authenticate()

if __name__ == "__main__":
    print("SAS Authentication and API Client Module")
    print("=" * 70)

    try:
        # Get authenticated session
        tokens = get_sas_tokens()
        access_token = tokens['access_token']

        print(f"Authentication successful!")
        print(f"Access Token: {access_token[:50]}...")    

    except Exception as e:
        print(f"Error: {e}")


