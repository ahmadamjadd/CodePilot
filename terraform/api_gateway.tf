resource "aws_apigatewayv2_api" "codepilot_api" {
  name          = "codepilot-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "sqs_integration" {
  api_id = aws_apigatewayv2_api.codepilot_api.id

  integration_type    = "AWS_PROXY"
  integration_subtype = "SQS-SendMessage"

  credentials_arn = aws_iam_role.api_gateway_role.arn

  request_parameters = {
    QueueUrl    = aws_sqs_queue.codepilot_queue.url
    MessageBody = "$request.body"
  }

  payload_format_version = "1.0"
}

resource "aws_apigatewayv2_route" "webhook" {
  api_id = aws_apigatewayv2_api.codepilot_api.id

  route_key = "POST /webhook"

  target = "integrations/${aws_apigatewayv2_integration.sqs_integration.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.codepilot_api.id
  name        = "$default"
  auto_deploy = true
}
