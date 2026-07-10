resource "aws_sqs_queue" "codepilot_queue" {
  name = var.sqs_queue_name

  visibility_timeout_seconds = 310
  message_retention_seconds  = 345600

  receive_wait_time_seconds = 20

  sqs_managed_sse_enabled = true
}