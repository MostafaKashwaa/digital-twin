project_name = "twin"
environment  = "dev"

# Optional: Custom domain configuration
# use_custom_domain = true
# root_domain       = "example.com"

# Bedrock model
bedrock_model_id = "amazon.nova-micro-v1:0"

# Lambda configuration
lambda_timeout = 60

# API Gateway throttling
api_throttle_burst_limit = 10
api_throttle_rate_limit  = 5

use_custom_domain = false
root_domain = ""

# Sensitive variables should be set in terraform.tfvars.local
# Copy terraform.tfvars.local.example to terraform.tfvars.local and add your secrets
# openai_api_key = "your-openai-api-key-here"