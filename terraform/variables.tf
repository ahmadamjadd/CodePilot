variable "aws_region" {
  description = "AWS region where resources will be created."
  type        = string
}

variable "lambda_function_name" {
  type = string
}

variable "groq_api_key" {
  type      = string
  sensitive = true
}

variable "github_token" {
  type      = string
  sensitive = true
}

variable "sqs_queue_name" {
  type = string
}