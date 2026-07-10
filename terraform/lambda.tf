resource "aws_lambda_function" "codepilot" {
  function_name = var.lambda_function_name

  role    = aws_iam_role.lambda_execution_role.arn
  handler = "lambda_handler.lambda_handler"
  runtime = "python3.12"

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  timeout     = 300
  memory_size = 128

  environment {
    variables = {
      GROQ_API_KEY = var.groq_api_key
      GITHUB_TOKEN = var.github_token
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution
  ]
}