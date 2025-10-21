# AWS Secrets Manager for Schwab Token (Optional)
# 
# Note: For Lightsail deployment, credentials are stored in .env file on the instance.
# This Secrets Manager resource is optional and can be used for enhanced security.

resource "aws_secretsmanager_secret" "schwab_token" {
  name        = "schwab-api-token-${var.environment}"
  description = "Schwab API OAuth token for alpha-kite-max (optional, not required for Lightsail)"

  recovery_window_in_days = 7
}

# The actual secret value is managed separately:
# - For Lightsail: Set in .env file during deployment
# - For AWS Secrets Manager: Set manually after OAuth authentication
