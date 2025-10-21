# Terraform Outputs for Lightsail Infrastructure
# Note: Currently minimal as Lightsail deployment is handled via deploy.sh script

output "schwab_token_secret_arn" {
  description = "ARN of the Schwab token secret (optional, for AWS Secrets Manager)"
  value       = try(aws_secretsmanager_secret.schwab_token.arn, "Not configured - using .env file instead")
}

output "aws_region" {
  description = "AWS region for deployment"
  value       = var.aws_region
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

# Future: Add Lightsail instance outputs when managed via Terraform
# output "lightsail_instance_ip" {
#   description = "Public IP of Lightsail instance"
#   value       = aws_lightsail_instance.streaming_service.public_ip_address
# }
