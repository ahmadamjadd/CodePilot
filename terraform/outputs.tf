output "api_id" {
  value       = aws_apigatewayv2_api.codepilot_api.id
  description = "The ID of the API Gateway."
}

output "webhook_url" {
  value       = "${aws_apigatewayv2_stage.default.invoke_url}webhook"
  description = "The HTTP POST URL where you should configure your GitHub Webhook."
}