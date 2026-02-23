terraform {
  backend "s3" {
    bucket = "chbn-tfstate"
    key    = "persistent/terraform.tfstate"
    region = "ap-southeast-1"
  }
}
