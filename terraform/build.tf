resource "null_resource" "build_lambda" {

  provisioner "local-exec" {

    command = <<EOT
rm -rf ${path.module}/build
mkdir -p ${path.module}/build

cp ${path.module}/../src/lambda_handler.py ${path.module}/build/
cp -r ${path.module}/../src/codepilot_review ${path.module}/build/

pip install \
    -r ${path.module}/../requirements.txt \
    -t ${path.module}/build
EOT

  }

  triggers = {
    always = timestamp()
  }
}