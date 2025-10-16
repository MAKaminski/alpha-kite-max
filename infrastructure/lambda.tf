# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "alpha-kite-real-time-streamer-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for Lambda
resource "aws_iam_role_policy" "lambda_policy" {
  name = "alpha-kite-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:PutSecretValue",
          "secretsmanager:UpdateSecret",
          "secretsmanager:CreateSecret"
        ]
        Resource = aws_secretsmanager_secret.schwab_token.arn
      },
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

# Lambda function
resource "aws_lambda_function" "real_time_streamer" {
  filename      = "${path.module}/../backend/lambda/lambda_deployment.zip"
  function_name = "alpha-kite-real-time-streamer"
  role          = aws_iam_role.lambda_role.arn
  handler       = "real_time_streamer.lambda_handler"
  runtime       = "python3.10"
  timeout       = 60
  memory_size   = 256

  source_code_hash = fileexists("${path.module}/../backend/lambda/lambda_deployment.zip") ? filebase64sha256("${path.module}/../backend/lambda/lambda_deployment.zip") : null

  environment {
    variables = {
      SUPABASE_URL              = var.supabase_url
      SUPABASE_SERVICE_ROLE_KEY = var.supabase_key
      SCHWAB_APP_KEY            = var.schwab_app_key
      SCHWAB_APP_SECRET         = var.schwab_secret
      DEFAULT_TICKER            = var.default_ticker
      SCHWAB_TOKEN_SECRET       = aws_secretsmanager_secret.schwab_token.name
      AWS_REGION                = var.aws_region
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_policy
  ]
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.real_time_streamer.function_name}"
  retention_in_days = 14
}

# EventBridge rule: every minute during market hours (9:30 AM - 4:00 PM ET)
# Note: EventBridge uses UTC, so we need to convert:
# 9:30 AM ET = 1:30 PM UTC (EST) or 2:30 PM UTC (EDT)
# 4:00 PM ET = 8:00 PM UTC (EST) or 9:00 PM UTC (EDT)
# Using EDT (daylight savings) which is UTC-4

resource "aws_cloudwatch_event_rule" "market_hours_tick" {
  name                = "alpha-kite-market-hours-every-minute"
  description         = "Trigger every minute during market hours (9:30 AM - 4:00 PM ET)"
  schedule_expression = "cron(30-59 13 ? * MON-FRI *)"  # 9:30-9:59 AM ET
}

resource "aws_cloudwatch_event_rule" "market_hours_tick_10_to_15" {
  name                = "alpha-kite-market-hours-10-to-15"
  description         = "Trigger every minute 10 AM - 3:59 PM ET"
  schedule_expression = "cron(* 14-19 ? * MON-FRI *)"  # 10:00 AM - 3:59 PM ET
}

resource "aws_cloudwatch_event_rule" "market_hours_tick_close" {
  name                = "alpha-kite-market-hours-close"
  description         = "Trigger every minute 4:00 PM ET until close"
  schedule_expression = "cron(0-0 20 ? * MON-FRI *)"  # 4:00 PM ET
}

# EventBridge targets
resource "aws_cloudwatch_event_target" "lambda_target_open" {
  rule      = aws_cloudwatch_event_rule.market_hours_tick.name
  target_id = "RealTimeStreamerOpen"
  arn       = aws_lambda_function.real_time_streamer.arn
}

resource "aws_cloudwatch_event_target" "lambda_target_midday" {
  rule      = aws_cloudwatch_event_rule.market_hours_tick_10_to_15.name
  target_id = "RealTimeStreamerMidDay"
  arn       = aws_lambda_function.real_time_streamer.arn
}

resource "aws_cloudwatch_event_target" "lambda_target_close" {
  rule      = aws_cloudwatch_event_rule.market_hours_tick_close.name
  target_id = "RealTimeStreamerClose"
  arn       = aws_lambda_function.real_time_streamer.arn
}

# Lambda permissions for EventBridge
resource "aws_lambda_permission" "allow_eventbridge_open" {
  statement_id  = "AllowExecutionFromEventBridgeOpen"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.real_time_streamer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.market_hours_tick.arn
}

resource "aws_lambda_permission" "allow_eventbridge_midday" {
  statement_id  = "AllowExecutionFromEventBridgeMidDay"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.real_time_streamer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.market_hours_tick_10_to_15.arn
}

resource "aws_lambda_permission" "allow_eventbridge_close" {
  statement_id  = "AllowExecutionFromEventBridgeClose"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.real_time_streamer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.market_hours_tick_close.arn
}

