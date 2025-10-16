"""Manages Schwab token refresh in AWS Secrets Manager."""

import json
import boto3
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class TokenManager:
    """Manages Schwab token refresh in AWS Secrets Manager."""
    
    def __init__(self, secret_name: str = "schwab-api-token", region: str = "us-east-1"):
        """Initialize token manager.
        
        Args:
            secret_name: Name of secret in AWS Secrets Manager
            region: AWS region
        """
        self.secret_name = secret_name
        self.region = region
        self.secrets_client = boto3.client('secretsmanager', region_name=region)
        logger.info("token_manager_initialized", secret_name=secret_name, region=region)
    
    def get_token(self) -> Optional[Dict[str, Any]]:
        """Retrieve token from AWS Secrets Manager.
        
        Returns:
            Token data as dictionary, or None if not found
        """
        try:
            response = self.secrets_client.get_secret_value(SecretId=self.secret_name)
            
            if 'SecretString' in response:
                token_data = json.loads(response['SecretString'])
                logger.info("token_retrieved_successfully", secret_name=self.secret_name)
                return token_data
            else:
                logger.error("token_not_found_in_secret", secret_name=self.secret_name)
                return None
                
        except self.secrets_client.exceptions.ResourceNotFoundException:
            logger.warning("secret_not_found", secret_name=self.secret_name)
            return None
        except Exception as e:
            logger.error("token_retrieval_error", error=str(e), secret_name=self.secret_name)
            return None
    
    def save_token(self, token_data: Dict[str, Any]) -> bool:
        """Save token to AWS Secrets Manager.
        
        Args:
            token_data: Token data to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            secret_value = json.dumps(token_data)
            
            try:
                # Try to update existing secret
                self.secrets_client.update_secret(
                    SecretId=self.secret_name,
                    SecretString=secret_value
                )
                logger.info("token_updated_successfully", secret_name=self.secret_name)
            except self.secrets_client.exceptions.ResourceNotFoundException:
                # Secret doesn't exist, create it
                self.secrets_client.create_secret(
                    Name=self.secret_name,
                    SecretString=secret_value,
                    Description="Schwab API OAuth token for alpha-kite-max"
                )
                logger.info("token_created_successfully", secret_name=self.secret_name)
            
            return True
            
        except Exception as e:
            logger.error("token_save_error", error=str(e), secret_name=self.secret_name)
            return False
    
    def refresh_token(self, schwab_client) -> bool:
        """Refresh expired token and save to Secrets Manager.
        
        Args:
            schwab_client: Authenticated Schwab client instance
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # The schwab-py library handles token refresh automatically
            # when the client is authenticated
            # We just need to save the refreshed token
            
            logger.info("attempting_token_refresh")
            
            # Re-authenticate to trigger refresh if needed
            client_instance = schwab_client.authenticate()
            
            # Check if token was refreshed by reading from token file
            # The schwab-py library saves refreshed tokens to the token_path
            token_path = schwab_client.config.token_path
            
            try:
                with open(token_path, 'r') as f:
                    token_data = json.load(f)
                
                # Save to Secrets Manager
                success = self.save_token(token_data)
                
                if success:
                    logger.info("token_refresh_successful")
                    return True
                else:
                    logger.error("token_refresh_save_failed")
                    return False
                    
            except FileNotFoundError:
                logger.error("token_file_not_found", path=token_path)
                return False
            except json.JSONDecodeError as e:
                logger.error("token_file_parse_error", error=str(e), path=token_path)
                return False
                
        except Exception as e:
            logger.error("token_refresh_error", error=str(e))
            return False
    
    def token_needs_refresh(self, token_data: Dict[str, Any]) -> bool:
        """Check if token needs to be refreshed.
        
        Args:
            token_data: Token data to check
            
        Returns:
            True if token needs refresh, False otherwise
        """
        try:
            # Check expiration time
            expires_at = token_data.get('expires_at')
            
            if not expires_at:
                logger.warning("token_missing_expiration")
                return True
            
            from datetime import datetime
            current_time = datetime.now().timestamp()
            
            # Refresh if token expires within 5 minutes
            buffer_seconds = 300
            needs_refresh = (expires_at - current_time) < buffer_seconds
            
            if needs_refresh:
                logger.info("token_needs_refresh", expires_in_seconds=expires_at - current_time)
            
            return needs_refresh
            
        except Exception as e:
            logger.error("token_check_error", error=str(e))
            return True  # Assume refresh needed on error

