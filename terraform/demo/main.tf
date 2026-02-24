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

# --- VPC ---

module "vpc" {
  source                 = "../modules/vpc"
  project                = var.project
  enable_private_subnets = var.enable_rds
}

# --- ALB ---

module "alb" {
  source     = "../modules/alb"
  project    = var.project
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.public_subnet_ids
}

# --- ECS ---

module "ecs" {
  source = "../modules/ecs"

  project            = var.project
  aws_region         = var.aws_region
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.public_subnet_ids
  alb_sg_id          = module.alb.alb_sg_id
  execution_role_arn = var.ecs_exec_role_arn

  api_image          = var.api_image
  web_image          = var.web_image
  jwt_secret_arn     = var.jwt_secret_arn
  openai_api_key_arn = var.openai_api_key_arn

  api_target_group_arn = module.alb.api_target_group_arn
  web_target_group_arn = module.alb.web_target_group_arn

  # RDS integration
  enable_rds   = var.enable_rds
  database_url = var.enable_rds ? module.rds[0].database_url : ""
}

# --- RDS (conditional) ---

module "rds" {
  source = "../modules/rds"
  count  = var.enable_rds ? 1 : 0

  project            = var.project
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  ecs_sg_id          = module.ecs.ecs_sg_id
}
