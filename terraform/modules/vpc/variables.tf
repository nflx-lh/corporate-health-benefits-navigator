variable "project" {
  description = "Project name prefix"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "enable_private_subnets" {
  description = "Create private subnets (for RDS). No NAT gateway."
  type        = bool
  default     = false
}
