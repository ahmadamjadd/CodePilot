resource "aws_lambda_event_source_mapping" "codepilot_sqs_trigger" {
  event_source_arn = aws_sqs_queue.codepilot_queue.arn

  function_name = aws_lambda_function.codepilot.arn

  batch_size = 1

  enabled = true
}