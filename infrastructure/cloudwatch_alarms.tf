# CloudWatch Alarms for Token Expiration Detection

# SNS Topic for alerts
resource "aws_sns_topic" "lambda_alerts" {
  name = "alpha-kite-lambda-alerts"
  
  tags = {
    Project = "AlphaKiteMax"
    Purpose = "Lambda error notifications"
  }
}

# SNS Email Subscription (you'll receive confirmation email)
resource "aws_sns_topic_subscription" "lambda_email_alert" {
  topic_arn = aws_sns_topic.lambda_alerts.arn
  protocol  = "email"
  endpoint  = "your-email@example.com"  # CHANGE THIS to your email
}

# Alarm: Lambda Errors (Token Invalid)
resource "aws_cloudwatch_metric_alarm" "lambda_token_errors" {
  alarm_name          = "alpha-kite-lambda-token-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300  # 5 minutes
  statistic           = "Sum"
  threshold           = 5    # Alert after 5 errors in 15 minutes
  alarm_description   = "Lambda function failing - likely token expired"
  alarm_actions       = [aws_sns_topic.lambda_alerts.arn]
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    FunctionName = "alpha-kite-real-time-streamer"
  }
  
  tags = {
    Project = "AlphaKiteMax"
    AlertType = "TokenExpiration"
  }
}

# Alarm: No Data for 2 Hours
resource "aws_cloudwatch_metric_alarm" "no_data_uploaded" {
  alarm_name          = "alpha-kite-no-data-uploaded"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Invocations"
  namespace           = "AWS/Lambda"
  period              = 7200  # 2 hours
  statistic           = "Sum"
  threshold           = 100   # Should have ~120 invocations in 2 hours during market
  alarm_description   = "No Lambda invocations - data not being uploaded"
  alarm_actions       = [aws_sns_topic.lambda_alerts.arn]
  
  dimensions = {
    FunctionName = "alpha-kite-real-time-streamer"
  }
  
  tags = {
    Project = "AlphaKiteMax"
    AlertType = "DataGap"
  }
}

# Output the SNS topic ARN
output "alerts_topic_arn" {
  value       = aws_sns_topic.lambda_alerts.arn
  description = "SNS topic ARN for Lambda alerts"
}

