resource "random_password" "jwt_secret" {
  length  = 32
  special = true
}

resource "aws_ssm_parameter" "jwt_secret" {
  name  = "/${var.project}/${var.env}/jwt-secret"
  type  = "SecureString"
  value = random_password.jwt_secret.result

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "openai_api_key" {
  name  = "/${var.project}/${var.env}/openai-api-key"
  type  = "SecureString"
  value = "PLACEHOLDER-update-via-cli"

  lifecycle {
    ignore_changes = [value]
  }
}
