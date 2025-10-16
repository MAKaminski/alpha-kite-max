variable "supabase_url" {
  description = "Supabase project URL"
  type        = string
  sensitive   = true
}

variable "supabase_key" {
  description = "Supabase service role key"
  type        = string
  sensitive   = true
}

variable "schwab_app_key" {
  description = "Schwab API app key"
  type        = string
  sensitive   = true
}

variable "schwab_secret" {
  description = "Schwab API app secret"
  type        = string
  sensitive   = true
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "default_ticker" {
  description = "Default stock ticker to stream"
  type        = string
  default     = "QQQ"
}

