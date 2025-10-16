# AWS Secrets Manager for Schwab Token
resource "aws_secretsmanager_secret" "schwab_token" {
  name        = "schwab-api-token-${var.environment}"
  description = "Schwab API OAuth token for alpha-kite-max"

  recovery_window_in_days = 7
}

# Note: The actual secret value needs to be set manually or via separate process
# after initial Schwab OAuth authentication. The Lambda function will update
# this secret when tokens are refreshed.

