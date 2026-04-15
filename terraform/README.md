# Terraform Infrastructure

This directory contains Terraform configuration for deploying the AI Twin infrastructure to AWS.

## File Structure

- `main.tf` - Entry point with data sources
- `variables.tf` - Input variable definitions
- `outputs.tf` - Output values
- `versions.tf` - Terraform and provider versions
- `locals.tf` - Local variables and common tags
- `s3.tf` - S3 bucket configurations
- `iam.tf` - IAM roles and policies
- `lambda.tf` - Lambda function configuration
- `api_gateway.tf` - API Gateway configuration
- `cloudfront.tf` - CloudFront distribution
- `route53.tf` - Route53 DNS and ACM certificates (optional)
- `main.tf.original` - Original monolithic configuration (for reference)

## Usage

1. Copy the example variables file:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit `terraform.tfvars` with your values:
   ```tf
   project_name = "my-ai-twin"
   environment  = "dev"
   # use_custom_domain = true
   # root_domain       = "example.com"
   ```

3. Initialize Terraform:
   ```bash
   terraform init
   ```

4. Plan the deployment:
   ```bash
   terraform plan
   ```

5. Apply the configuration:
   ```bash
   terraform apply
   ```

## Custom Domain (Optional)

To use a custom domain:

1. Set `use_custom_domain = true` in `terraform.tfvars`
2. Set `root_domain = "yourdomain.com"`
3. Ensure your domain is managed in Route53
4. Run `terraform apply`

## Outputs

After deployment, Terraform will output:
- Frontend URL (CloudFront distribution)
- API Gateway endpoint
- Lambda function name
- S3 bucket names
- CloudFront distribution ID

## Requirements

- Terraform >= 1.0
- AWS CLI configured with appropriate credentials
- AWS account with necessary permissions
