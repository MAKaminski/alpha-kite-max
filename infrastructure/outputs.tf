output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.real_time_streamer.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.real_time_streamer.arn
}

output "lambda_role_arn" {
  description = "ARN of the Lambda IAM role"
  value       = aws_iam_role.lambda_role.arn
}

output "schwab_token_secret_arn" {
  description = "ARN of the Schwab token secret"
  value       = aws_secretsmanager_secret.schwab_token.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for Lambda"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "eventbridge_rules" {
  description = "EventBridge rules for scheduling"
  value = {
    market_open   = aws_cloudwatch_event_rule.market_hours_tick.name
    market_midday = aws_cloudwatch_event_rule.market_hours_tick_10_to_15.name
    market_close  = aws_cloudwatch_event_rule.market_hours_tick_close.name
  }
}

