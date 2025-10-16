#!/usr/bin/env python3
"""
Lambda function for refreshing Schwab tokens via admin panel
Handles token refresh and AWS Secrets Manager update
"""

import json
import time
import requests
import base64
import boto3
import structlog
from datetime import datetime

# Configure structured logging
logger = structlog.get_logger()

def lambda_handler(event, context):
    """Lambda handler for token refresh"""
    try:
        logger.info("token_refresh_lambda_invoked", 
                   lambda_event=event,
                   request_id=context.aws_request_id)
        
        # Parse the event
        if 'httpMethod' in event:
            # API Gateway event
            if event['httpMethod'] != 'POST':
                return {
                    'statusCode': 405,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Method not allowed'})
                }
            
            try:
                body = json.loads(event.get('body', '{}'))
            except json.JSONDecodeError:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Invalid JSON body'})
                }
        else:
            # Direct Lambda invocation
            body = event
        
        # Get action from body
        action = body.get('action')
        
        if action == 'refresh_token':
            return handle_token_refresh()
        elif action == 'check_token_status':
            return handle_token_status_check()
        else:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid action. Use "refresh_token" or "check_token_status"'})
            }
    
    except Exception as e:
        logger.error("token_refresh_lambda_error", error=str(e))
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }

def handle_token_refresh():
    """Handle token refresh request"""
    try:
        # Get current token from AWS Secrets Manager
        current_token = get_token_from_secrets_manager()
        if not current_token:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'No token found in AWS Secrets Manager'})
            }
        
        # Check if we have a refresh token
        if 'token' not in current_token or 'refresh_token' not in current_token['token']:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'No refresh token available',
                    'message': 'Token needs to be re-authenticated manually'
                })
            }
        
        # Refresh the token
        success, message, new_tokens = refresh_token(current_token['token']['refresh_token'])
        
        if success and new_tokens:
            # Update AWS Secrets Manager
            update_success = update_token_in_secrets_manager(new_tokens)
            
            if update_success:
                logger.info("token_refresh_success")
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        'success': True,
                        'message': 'Token refreshed successfully',
                        'expires_at': new_tokens.get('expires_at'),
                        'expires_in': new_tokens.get('expires_in')
                    })
                }
            else:
                return {
                    'statusCode': 500,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Token refreshed but failed to update AWS Secrets Manager'})
                }
        else:
            logger.error("token_refresh_failed", error=message)
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'error': 'Token refresh failed',
                    'message': message
                })
            }
    
    except Exception as e:
        logger.error("token_refresh_handler_error", error=str(e))
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }

def handle_token_status_check():
    """Handle token status check request"""
    try:
        # Get current token from AWS Secrets Manager
        current_token = get_token_from_secrets_manager()
        if not current_token:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'has_token': False,
                    'message': 'No token found'
                })
            }
        
        # Check token structure and expiration
        if 'token' not in current_token:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'has_token': True,
                    'has_access_token': False,
                    'has_refresh_token': False,
                    'message': 'Invalid token structure'
                })
            }
        
        token = current_token['token']
        has_access = 'access_token' in token and token['access_token']
        has_refresh = 'refresh_token' in token and token['refresh_token']
        
        # Check expiration
        expires_at = token.get('expires_at', 0)
        current_time = int(time.time())
        
        if expires_at <= current_time:
            expires_status = 'expired'
            time_until_expiry = 0
        else:
            time_until_expiry = expires_at - current_time
            if time_until_expiry < 3600:  # Less than 1 hour
                expires_status = 'expires_soon'
            else:
                expires_status = 'valid'
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'has_token': True,
                'has_access_token': has_access,
                'has_refresh_token': has_refresh,
                'expires_status': expires_status,
                'expires_at': expires_at,
                'time_until_expiry': time_until_expiry,
                'can_refresh': has_refresh and expires_status != 'expired'
            })
        }
    
    except Exception as e:
        logger.error("token_status_check_error", error=str(e))
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }

def get_token_from_secrets_manager():
    """Get token from AWS Secrets Manager"""
    try:
        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        
        response = secrets_client.get_secret_value(
            SecretId='schwab-api-token-prod'
        )
        
        token_data = json.loads(response['SecretString'])
        logger.info("token_retrieved_from_secrets_manager")
        return token_data
    
    except Exception as e:
        logger.error("token_retrieval_error", error=str(e))
        return None

def update_token_in_secrets_manager(token_data):
    """Update token in AWS Secrets Manager"""
    try:
        secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
        
        # Convert to our expected format
        current_time = int(time.time())
        formatted_token = {
            "creation_timestamp": current_time,
            "token": {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token", ""),
                "expires_in": str(token_data["expires_in"]),
                "token_type": token_data["token_type"],
                "scope": token_data.get("scope", "api"),
                "expires_at": current_time + token_data["expires_in"]
            }
        }
        
        secrets_client.update_secret(
            SecretId='schwab-api-token-prod',
            SecretString=json.dumps(formatted_token)
        )
        
        logger.info("token_updated_in_secrets_manager")
        return True
    
    except Exception as e:
        logger.error("token_update_error", error=str(e))
        return False

def refresh_token(refresh_token):
    """Refresh the Schwab token"""
    try:
        # App credentials
        app_key = "Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU"
        app_secret = "m5YMEpTk0zluhdYz0kwFaKQ98VlOZkErxR0C1ilWyOvK6tEYxoAA7kjKKB5hk2NK"
        
        # Prepare Basic Auth header
        credentials = f"{app_key}:{app_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
        
        # Make refresh request
        response = requests.post(
            'https://api.schwabapi.com/v1/oauth/token',
            headers=headers,
            data=data,
            timeout=10
        )
        
        logger.info("refresh_request_sent", status_code=response.status_code)
        
        if response.status_code == 200:
            new_tokens = response.json()
            return True, "Token refreshed successfully", new_tokens
        elif response.status_code == 400:
            error_data = response.json()
            error_msg = error_data.get('error', 'Unknown error')
            return False, f"Refresh failed: {error_msg}", None
        elif response.status_code == 429:
            return False, "Rate limited - too many refresh attempts", None
        else:
            return False, f"Refresh failed: {response.status_code}", None
    
    except Exception as e:
        logger.error("refresh_token_error", error=str(e))
        return False, f"Refresh error: {e}", None
