terraform {
  backend "s3" {
    bucket = "chbn-tfstate"
    key    = "demo/terraform.tfstate"
    region = "ap-southeast-1"
  }
}
