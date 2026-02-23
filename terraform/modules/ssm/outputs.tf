output "param_arns" {
  description = "List of SSM parameter ARNs"
  value = [
    aws_ssm_parameter.jwt_secret.arn,
    aws_ssm_parameter.openai_api_key.arn,
  ]
}

output "jwt_secret_arn" {
  value = aws_ssm_parameter.jwt_secret.arn
}

output "openai_api_key_arn" {
  value = aws_ssm_parameter.openai_api_key.arn
}
