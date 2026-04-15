terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0, <= 6.0"
    }
  }
}

provider "aws" {
  # region = var.aws_region
}

provider "aws" {
  alias  = "eu-central-1"
  region = "eu-central-1"
}

# ACM certificates must be created in us-east-1 for CloudFront
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}
