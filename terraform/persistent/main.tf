terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# --- ECR Repositories ---

module "ecr" {
  source     = "../modules/ecr"
  repo_names = ["${var.project}-api", "${var.project}-web"]
}

# --- SSM Parameters ---

module "ssm" {
  source  = "../modules/ssm"
  project = var.project
  env     = var.env
}

# --- IAM Roles ---

module "iam" {
  source             = "../modules/iam"
  project            = var.project
  ssm_param_arns     = module.ssm.param_arns
  ecr_repo_arns      = values(module.ecr.repository_arns)
  github_repo        = var.github_repo
  create_github_oidc = var.create_github_oidc
}
