data "archive_file" "lambda_zip" {

  depends_on = [
    null_resource.build_lambda
  ]

  type        = "zip"
  source_dir  = "${path.module}/build"
  output_path = "${path.module}/lambda.zip"

}