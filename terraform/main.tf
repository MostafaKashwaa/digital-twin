# Main Terraform configuration file
# This file serves as the entry point and includes data sources

# Data source to get current AWS account ID
data "aws_caller_identity" "current" {}
