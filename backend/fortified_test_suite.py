#!/usr/bin/env python3
"""
Fortified Testing Suite for Schwab Token Management
Prevents token issues and provides comprehensive diagnostics
"""

import json
import time
import requests
import base64
from datetime import datetime, timedelta
from pathlib import Path
import structlog
from typing import Dict, List, Tuple, Optional

# Configure structured logging
logger = structlog.get_logger()

class FortifiedTestSuite:
    def __init__(self):
        self.token_file = Path("config/schwab_token.json")
        self.app_key = "Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU"
        self.app_secret = "m5YMEpTk0zluhdYz0kwFaKQ98VlOZkErxR0C1ilWyOvK6tEYxoAA7kjKKB5hk2NK"
        self.base_url = "https://api.schwabapi.com"
        
        # Test results
        self.test_results = []
        self.critical_failures = []
        self.warnings = []
    
    def add_test_result(self, test_name: str, success: bool, message: str, critical: bool = False):
        """Add a test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "critical": critical,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        if not success:
            if critical:
                self.critical_failures.append(result)
            else:
                self.warnings.append(result)
    
    def test_token_file_exists(self) -> bool:
        """Test if token file exists"""
        exists = self.token_file.exists()
        self.add_test_result(
            "Token File Exists",
            exists,
            "Token file found" if exists else "Token file not found",
            critical=True
        )
        return exists
    
    def test_token_file_readable(self) -> bool:
        """Test if token file is readable and valid JSON"""
        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
            
            self.add_test_result(
                "Token File Readable",
                True,
                "Token file is valid JSON"
            )
            return True, token_data
        except Exception as e:
            self.add_test_result(
                "Token File Readable",
                False,
                f"Token file read error: {e}",
                critical=True
            )
            return False, None
    
    def test_token_structure(self, token_data: Dict) -> bool:
        """Test token structure"""
        if not token_data:
            self.add_test_result(
                "Token Structure",
                False,
                "No token data",
                critical=True
            )
            return False
        
        issues = []
        
        # Check top-level structure
        if "token" not in token_data:
            issues.append("Missing 'token' field")
        else:
            token = token_data["token"]
            
            # Check required fields
            required_fields = ["access_token", "refresh_token", "expires_at"]
            for field in required_fields:
                if field not in token:
                    issues.append(f"Missing '{field}' field")
                elif not token[field]:
                    issues.append(f"Empty '{field}' field")
            
            # Check token type
            if token.get("token_type") != "Bearer":
                issues.append(f"Unexpected token_type: {token.get('token_type')}")
            
            # Check scope
            if token.get("scope") != "api":
                issues.append(f"Unexpected scope: {token.get('scope')}")
        
        success = len(issues) == 0
        message = "Token structure is valid" if success else f"Issues: {', '.join(issues)}"
        
        self.add_test_result(
            "Token Structure",
            success,
            message,
            critical=not success
        )
        
        return success
    
    def test_token_expiration(self, token_data: Dict) -> bool:
        """Test token expiration"""
        if not token_data or "token" not in token_data:
            return False
        
        token = token_data["token"]
        
        if "expires_at" not in token:
            self.add_test_result(
                "Token Expiration",
                False,
                "No expiration timestamp",
                critical=True
            )
            return False
        
        expires_at = token["expires_at"]
        current_time = int(time.time())
        
        if expires_at <= current_time:
            self.add_test_result(
                "Token Expiration",
                False,
                f"Token expired {current_time - expires_at} seconds ago",
                critical=True
            )
            return False
        
        time_until_expiry = expires_at - current_time
        
        if time_until_expiry < 300:  # Less than 5 minutes
            self.add_test_result(
                "Token Expiration",
                True,
                f"Token expires in {time_until_expiry} seconds (WARNING: Soon!)"
            )
        else:
            self.add_test_result(
                "Token Expiration",
                True,
                f"Token expires in {time_until_expiry} seconds"
            )
        
        return True
    
    def test_api_connectivity(self, access_token: str) -> bool:
        """Test API connectivity"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            response = requests.get(
                f"{self.base_url}/v1/accounts",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.add_test_result(
                    "API Connectivity",
                    True,
                    "API connection successful"
                )
                return True
            elif response.status_code == 401:
                self.add_test_result(
                    "API Connectivity",
                    False,
                    "Token invalid/expired",
                    critical=True
                )
                return False
            elif response.status_code == 429:
                self.add_test_result(
                    "API Connectivity",
                    False,
                    "Rate limited - too many requests",
                    critical=True
                )
                return False
            else:
                self.add_test_result(
                    "API Connectivity",
                    False,
                    f"Unexpected response: {response.status_code}",
                    critical=True
                )
                return False
                
        except requests.exceptions.Timeout:
            self.add_test_result(
                "API Connectivity",
                False,
                "Request timeout",
                critical=True
            )
            return False
        except Exception as e:
            self.add_test_result(
                "API Connectivity",
                False,
                f"Connection error: {e}",
                critical=True
            )
            return False
    
    def test_refresh_token(self, refresh_token: str) -> bool:
        """Test refresh token functionality"""
        try:
            credentials = f"{self.app_key}:{self.app_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }
            
            response = requests.post(
                f"{self.base_url}/v1/oauth/token",
                headers=headers,
                data=data,
                timeout=10
            )
            
            if response.status_code == 200:
                new_tokens = response.json()
                has_refresh = 'refresh_token' in new_tokens
                
                self.add_test_result(
                    "Refresh Token",
                    True,
                    f"Refresh successful, new refresh token: {has_refresh}"
                )
                return True
            elif response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get('error', 'Unknown error')
                
                self.add_test_result(
                    "Refresh Token",
                    False,
                    f"Refresh failed: {error_msg}",
                    critical=True
                )
                return False
            elif response.status_code == 429:
                self.add_test_result(
                    "Refresh Token",
                    False,
                    "Rate limited on refresh",
                    critical=True
                )
                return False
            else:
                self.add_test_result(
                    "Refresh Token",
                    False,
                    f"Refresh failed: {response.status_code}",
                    critical=True
                )
                return False
                
        except Exception as e:
            self.add_test_result(
                "Refresh Token",
                False,
                f"Refresh error: {e}",
                critical=True
            )
            return False
    
    def test_aws_secrets_manager(self) -> bool:
        """Test AWS Secrets Manager integration"""
        try:
            import subprocess
            result = subprocess.run([
                'aws', 'secretsmanager', 'get-secret-value',
                '--secret-id', 'schwab-api-token-prod',
                '--region', 'us-east-1',
                '--query', 'SecretString',
                '--output', 'text'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Try to parse the secret as JSON
                try:
                    secret_data = json.loads(result.stdout)
                    self.add_test_result(
                        "AWS Secrets Manager",
                        True,
                        "Secret retrieved successfully"
                    )
                    return True
                except json.JSONDecodeError:
                    self.add_test_result(
                        "AWS Secrets Manager",
                        False,
                        "Secret is not valid JSON",
                        critical=True
                    )
                    return False
            else:
                self.add_test_result(
                    "AWS Secrets Manager",
                    False,
                    f"AWS CLI error: {result.stderr}",
                    critical=True
                )
                return False
                
        except subprocess.TimeoutExpired:
            self.add_test_result(
                "AWS Secrets Manager",
                False,
                "AWS CLI timeout",
                critical=True
            )
            return False
        except Exception as e:
            self.add_test_result(
                "AWS Secrets Manager",
                False,
                f"AWS error: {e}",
                critical=True
            )
            return False
    
    def test_lambda_function(self) -> bool:
        """Test Lambda function"""
        try:
            import subprocess
            result = subprocess.run([
                'aws', 'lambda', 'invoke',
                '--function-name', 'alpha-kite-real-time-streamer',
                '--region', 'us-east-1',
                '--payload', '{}',
                'response.json'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Check the response
                try:
                    with open('response.json', 'r') as f:
                        response_data = json.load(f)
                    
                    if response_data.get('statusCode') == 200:
                        self.add_test_result(
                            "Lambda Function",
                            True,
                            "Lambda executed successfully"
                        )
                        return True
                    else:
                        self.add_test_result(
                            "Lambda Function",
                            False,
                            f"Lambda error: {response_data.get('body', 'Unknown error')}",
                            critical=True
                        )
                        return False
                except Exception as e:
                    self.add_test_result(
                        "Lambda Function",
                        False,
                        f"Error reading Lambda response: {e}",
                        critical=True
                    )
                    return False
            else:
                self.add_test_result(
                    "Lambda Function",
                    False,
                    f"AWS Lambda error: {result.stderr}",
                    critical=True
                )
                return False
                
        except subprocess.TimeoutExpired:
            self.add_test_result(
                "Lambda Function",
                False,
                "Lambda timeout",
                critical=True
            )
            return False
        except Exception as e:
            self.add_test_result(
                "Lambda Function",
                False,
                f"Lambda error: {e}",
                critical=True
            )
            return False
    
    def run_all_tests(self) -> Dict:
        """Run all tests and return comprehensive results"""
        print("🛡️  FORTIFIED TEST SUITE")
        print("=" * 60)
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Test 1: Token file exists
        if not self.test_token_file_exists():
            return self.generate_report()
        
        # Test 2: Token file readable
        readable, token_data = self.test_token_file_readable()
        if not readable:
            return self.generate_report()
        
        # Test 3: Token structure
        if not self.test_token_structure(token_data):
            return self.generate_report()
        
        # Test 4: Token expiration
        if not self.test_token_expiration(token_data):
            return self.generate_report()
        
        # Test 5: API connectivity
        access_token = token_data["token"]["access_token"]
        if not self.test_api_connectivity(access_token):
            return self.generate_report()
        
        # Test 6: Refresh token
        refresh_token = token_data["token"]["refresh_token"]
        self.test_refresh_token(refresh_token)
        
        # Test 7: AWS Secrets Manager
        self.test_aws_secrets_manager()
        
        # Test 8: Lambda function
        self.test_lambda_function()
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests
        critical_failures = len(self.critical_failures)
        
        print("📊 TEST RESULTS SUMMARY")
        print("-" * 40)
        print(f"Total tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"🔴 Critical: {critical_failures}")
        print()
        
        # Show all test results
        print("📋 DETAILED RESULTS")
        print("-" * 40)
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            critical = " (CRITICAL)" if result["critical"] else ""
            print(f"{status} {result['test']}{critical}: {result['message']}")
        
        print()
        
        # Show recommendations
        print("💡 RECOMMENDATIONS")
        print("-" * 40)
        
        if critical_failures > 0:
            print("🔴 CRITICAL ISSUES FOUND:")
            for failure in self.critical_failures:
                print(f"   • {failure['test']}: {failure['message']}")
            print()
            
            if any("refresh_token" in f["message"] for f in self.critical_failures):
                print("🔄 TOKEN REFRESH ISSUE:")
                print("   1. Run: python3 generate_auth_url.py")
                print("   2. Click the URL and authorize")
                print("   3. Run: python3 process_callback.py 'YOUR_CALLBACK_URL'")
                print()
            
            if any("Lambda" in f["test"] for f in self.critical_failures):
                print("☁️  LAMBDA ISSUE:")
                print("   1. Upload token: aws secretsmanager update-secret --secret-id schwab-api-token-prod --secret-string file://config/schwab_token.json --region us-east-1")
                print("   2. Test: aws lambda invoke --function-name alpha-kite-real-time-streamer --region us-east-1 --payload '{}' response.json")
                print()
        else:
            print("✅ All critical tests passed!")
            print("   System appears to be functioning correctly.")
        
        # Return structured results
        return {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "critical_failures": critical_failures,
                "overall_status": "PASS" if critical_failures == 0 else "FAIL"
            },
            "results": self.test_results,
            "critical_failures": self.critical_failures,
            "warnings": self.warnings
        }

def main():
    """Run the fortified test suite"""
    suite = FortifiedTestSuite()
    results = suite.run_all_tests()
    
    # Exit with appropriate code
    if results["summary"]["critical_failures"] > 0:
        exit(1)
    else:
        exit(0)

if __name__ == "__main__":
    main()
