# Schwab API Authentication Documentation

## Overview

This document contains comprehensive information about Schwab API authentication based on official documentation from schwab-py and community resources.

## Table of Contents

1. [OAuth 2.0 Flow Overview](#oauth-20-flow-overview)
2. [Application Registration](#application-registration)
3. [Authorization URL Construction](#authorization-url-construction)
4. [Token Exchange Process](#token-exchange-process)
5. [Token Management](#token-management)
6. [Common Issues and Solutions](#common-issues-and-solutions)
7. [Implementation Examples](#implementation-examples)
8. [Troubleshooting Guide](#troubleshooting-guide)

---

## OAuth 2.0 Flow Overview

The Schwab API uses OAuth 2.0 Authorization Code Grant flow with the following steps:

1. **Authorization Request**: Direct user to Schwab's authorization endpoint
2. **User Authentication**: User logs in to Schwab (if not already logged in)
3. **Consent Granting**: User grants permission to your application
4. **Authorization Code**: Schwab redirects with authorization code
5. **Token Exchange**: Exchange code for access and refresh tokens
6. **API Access**: Use access token for API calls
7. **Token Refresh**: Use refresh token to get new access tokens

---

## Application Registration

### Required Information

- **Client ID (App Key)**: Unique identifier for your application
- **Client Secret (App Secret)**: Secret key for authentication
- **Callback URL (Redirect URI)**: Where Schwab redirects after authorization
- **API Products**: Must subscribe to required APIs (e.g., "Accounts and Trading Production")

### Registration Steps

1. Go to [Schwab Developer Portal](https://developer.schwab.com/)
2. Create new application
3. Configure callback URL (must be HTTPS for production)
4. Subscribe to required API products
5. Submit for approval
6. Wait for "Ready For Use" status

### Important Notes

- **Callback URL must match exactly** (including trailing slashes)
- **Production vs Sandbox**: Use production environment for live data
- **HTTPS Required**: All callback URLs must use HTTPS
- **Approval Required**: Apps must be approved before use

---

## Authorization URL Construction

### Base URL
```
https://api.schwabapi.com/v1/oauth/authorize
```

### Required Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `client_id` | Your application's Client ID | `Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU` |
| `redirect_uri` | Registered callback URL | `https://127.0.0.1:8182` |
| `response_type` | Must be "code" | `code` |

### Optional Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `state` | CSRF protection (recommended) | `iJyLTOjsZvBU8Lzz23Tmx30Yp9j_EK4zFoP9P_7vaho` |
| `scope` | Requested permissions | `api` |

### Example URLs

**Basic OAuth URL:**
```
https://api.schwabapi.com/v1/oauth/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=https%3A//127.0.0.1%3A8182&response_type=code
```

**With State Parameter:**
```
https://api.schwabapi.com/v1/oauth/authorize?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=https%3A//127.0.0.1%3A8182&state=UNIQUE_STATE_STRING
```

**With Scope:**
```
https://api.schwabapi.com/v1/oauth/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=https%3A//127.0.0.1%3A8182&response_type=code&scope=api
```

---

## Token Exchange Process

### Token Endpoint
```
https://api.schwabapi.com/v1/oauth/token
```

### Request Format

**Method**: POST  
**Content-Type**: `application/x-www-form-urlencoded`  
**Authorization**: `Basic {base64(client_id:client_secret)}`

### Request Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `grant_type` | Must be "authorization_code" | `authorization_code` |
| `code` | Authorization code from callback | `ABC123...` |
| `redirect_uri` | Must match authorization request | `https://127.0.0.1:8182` |

### Response Format

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "dGhpc2lzYXJlZnJlc2h0b2t...",
  "expires_in": 1800,
  "token_type": "Bearer",
  "scope": "api",
  "id_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Example Implementation

```python
import base64
import requests

def exchange_code_for_tokens(code, client_id, client_secret, redirect_uri):
    token_url = "https://api.schwabapi.com/v1/oauth/token"
    
    # Basic authentication
    basic_auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    headers = {
        "Authorization": f"Basic {basic_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri
    }
    
    response = requests.post(token_url, headers=headers, data=data)
    return response.json()
```

---

## Token Management

### Token Lifespans

- **Access Token**: 30 minutes
- **Refresh Token**: 7 days
- **ID Token**: Varies (JWT format)

### Refresh Token Process

**Endpoint**: `https://api.schwabapi.com/v1/oauth/token`

**Request Parameters**:
- `grant_type`: `refresh_token`
- `refresh_token`: Current refresh token

**Example**:
```python
def refresh_access_token(refresh_token, client_id, client_secret):
    token_url = "https://api.schwabapi.com/v1/oauth/token"
    
    basic_auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    headers = {
        "Authorization": f"Basic {basic_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    
    response = requests.post(token_url, headers=headers, data=data)
    return response.json()
```

### Token Storage Best Practices

1. **Encrypt tokens** before storing
2. **Store securely** (AWS Secrets Manager, Azure Key Vault, etc.)
3. **Implement rotation** before expiration
4. **Handle refresh failures** gracefully
5. **Log token events** for debugging

---

## Common Issues and Solutions

### 1. Invalid Client Error

**Symptoms**: `invalid_client` error in OAuth response

**Causes**:
- Incorrect client_id or client_secret
- App not approved for production
- Wrong environment (sandbox vs production)

**Solutions**:
- Verify credentials in Developer Portal
- Ensure app status is "Ready For Use"
- Check environment settings

### 2. Redirect URI Mismatch

**Symptoms**: `invalid_request` or `redirect_uri_mismatch` error

**Causes**:
- Callback URL doesn't match registered URL
- Trailing slash differences
- Protocol mismatch (http vs https)

**Solutions**:
- Ensure exact match including trailing slashes
- Use HTTPS for production
- Check URL encoding

### 3. Login Page Issues

**Symptoms**: OAuth URL leads to non-functional login page

**Causes**:
- App not properly configured
- Missing required parameters
- Session/cookie issues

**Solutions**:
- Verify app configuration
- Add state parameter
- Try incognito/private browsing
- Ensure logged into Schwab.com

### 4. 500 Internal Server Error

**Symptoms**: HTTP 500 error from OAuth endpoint

**Causes**:
- Malformed request parameters
- Server-side issues
- Rate limiting

**Solutions**:
- Check parameter format
- Verify URL encoding
- Add state parameter
- Retry with exponential backoff

---

## Implementation Examples

### Python with schwab-py Library

```python
from schwab import auth

# Create client with automatic OAuth flow
client = auth.easy_client(
    api_key="YOUR_CLIENT_ID",
    app_secret="YOUR_CLIENT_SECRET",
    callback_url="https://127.0.0.1:8182",
    token_path="tokens.json"
)

# Use client for API calls
accounts = client.get_account_numbers()
```

### Manual OAuth Implementation

```python
import urllib.parse
import secrets
import requests
import base64

class SchwabOAuth:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.base_url = "https://api.schwabapi.com/v1/oauth"
    
    def get_authorization_url(self, state=None):
        if state is None:
            state = secrets.token_urlsafe(32)
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state
        }
        
        query_string = urllib.parse.urlencode(params)
        return f"{self.base_url}/authorize?{query_string}"
    
    def exchange_code_for_tokens(self, code):
        token_url = f"{self.base_url}/token"
        
        basic_auth = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        
        headers = {
            "Authorization": f"Basic {basic_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        
        response = requests.post(token_url, headers=headers, data=data)
        return response.json()
    
    def refresh_tokens(self, refresh_token):
        token_url = f"{self.base_url}/token"
        
        basic_auth = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        
        headers = {
            "Authorization": f"Basic {basic_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        response = requests.post(token_url, headers=headers, data=data)
        return response.json()
```

---

## Troubleshooting Guide

### Step-by-Step Debugging

1. **Verify App Configuration**
   - Check Developer Portal settings
   - Confirm callback URL matches exactly
   - Verify app is approved and active

2. **Test OAuth URL**
   - Use correct base URL (`api.schwabapi.com`)
   - Include all required parameters
   - Add state parameter for security

3. **Check Network Issues**
   - Test with curl or Postman
   - Verify HTTPS connectivity
   - Check for firewall/proxy issues

4. **Validate Token Exchange**
   - Ensure code is URL-decoded
   - Verify request format
   - Check response for error details

5. **Monitor Token Lifecycle**
   - Implement proper refresh logic
   - Handle expiration gracefully
   - Log all token events

### Common Error Codes

| Error Code | Description | Solution |
|------------|-------------|----------|
| `invalid_client` | Client credentials invalid | Check client_id and client_secret |
| `invalid_request` | Malformed request | Verify parameter format |
| `invalid_grant` | Authorization code invalid | Ensure code is fresh and correct |
| `unauthorized_client` | Client not authorized | Check app approval status |
| `unsupported_grant_type` | Wrong grant type | Use "authorization_code" or "refresh_token" |

### Debugging Tools

1. **Browser Developer Tools**: Check network requests and responses
2. **OAuth Debugger**: Use online tools to validate URLs
3. **Logging**: Implement detailed logging for all OAuth steps
4. **Testing Tools**: Use Postman or curl for manual testing

---

## Best Practices

### Security

1. **Never expose client_secret** in client-side code
2. **Use HTTPS** for all communications
3. **Implement state parameter** for CSRF protection
4. **Store tokens securely** with encryption
5. **Implement proper token rotation**

### Error Handling

1. **Handle all error cases** gracefully
2. **Implement retry logic** with exponential backoff
3. **Log errors** for debugging
4. **Provide user-friendly messages**
5. **Monitor token expiration**

### Performance

1. **Cache tokens** appropriately
2. **Implement connection pooling**
3. **Use async operations** where possible
4. **Monitor API rate limits**
5. **Implement proper timeouts**

---

## Resources

- [Schwab Developer Portal](https://developer.schwab.com/)
- [schwab-py Documentation](https://schwab-py.readthedocs.io/)
- [schwab-py GitHub Repository](https://github.com/alexgolec/schwab-py)
- [OAuth 2.0 RFC](https://tools.ietf.org/html/rfc6749)
- [Schwab API OAuth2 Example](https://gist.github.com/greytoc/3f8faf1ea50bfaf19d2ba5b31b66b1f6)

---

**Last Updated**: October 18, 2025  
**Version**: 1.0  
**Source**: schwab-py documentation, GitHub repository, and community resources
