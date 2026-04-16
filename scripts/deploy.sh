#!/bin/bash
set -e

ENVIRONMENT=${1:-dev}          # dev | test | prod
PROJECT_NAME=${2:-twin}
REBUILD=${3:-true}            # true | false

echo "🚀 Deploying ${PROJECT_NAME} to ${ENVIRONMENT}..."

# 1. Build Lambda package if requested
if [ "$REBUILD" = "true" ] || [ ! -f "../backend/lambda-deployment.zip" ]; then
  cd "$(dirname "$0")/.."        # project root
  echo "📦 Building Lambda package..."
  (cd backend && uv run deploy.py)
fi

# 2. Terraform workspace & apply
cd terraform
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${DEFAULT_AWS_REGION:-eu-central-1}

terraform init -input=false \
  -backend-config="bucket=twin-terraform-state-${AWS_ACCOUNT_ID}" \
  -backend-config="key=${ENVIRONMENT}/terraform.tfstate" \
  -backend-config="region=${AWS_REGION}" \
  -backend-config="dynamodb_table=twin-terraform-locks" \
  -backend-config="encrypt=true"

if ! terraform workspace list | grep -q "$ENVIRONMENT"; then
  terraform workspace new "$ENVIRONMENT"
else
  terraform workspace select "$ENVIRONMENT"
fi

# Build Terraform apply command
TF_APPLY_ARGS=()

# Add project and environment variables
TF_APPLY_ARGS+=("-var" "project_name=${PROJECT_NAME}")
TF_APPLY_ARGS+=("-var" "environment=${ENVIRONMENT}")

# Add OpenAI API key if provided
if [ -n "$OPENAI_API_KEY" ]; then
  TF_APPLY_ARGS+=("-var" "openai_api_key=${OPENAI_API_KEY}")
else
  echo "⚠️  Warning: OPENAI_API_KEY not set."
fi

# Check if local variables file exists
LOCAL_VARS_FILE="terraform.tfvars.local"
if [ -f "$LOCAL_VARS_FILE" ]; then
  echo "📝 Loading local variables from $LOCAL_VARS_FILE"
  TF_APPLY_ARGS+=("-var-file=$LOCAL_VARS_FILE")
else
  echo "⚠️   Warning: $LOCAL_VARS_FILE not found. Using environment variables only."
fi

# Use prod.tfvars for production environment
# if [ "$ENVIRONMENT" = "prod" ]; then
#   TF_APPLY_ARGS+=("-var-file=prod.tfvars")
# fi

# Add auto-approve flag
TF_APPLY_ARGS+=("-auto-approve")

echo "🎯 Applying Terraform..."
terraform apply "${TF_APPLY_ARGS[@]}"

API_URL=$(terraform output -raw api_gateway_url)
FRONTEND_BUCKET=$(terraform output -raw s3_frontend_bucket)
CUSTOM_URL=$(terraform output -raw custom_domain_url 2>/dev/null || true)

# 3. Build + deploy frontend
cd ../frontend

# Create production environment file with API URL
echo "📝 Setting API URL for production..."
echo "NEXT_PUBLIC_API_URL=$API_URL" > .env.production

npm install
npm run build
aws s3 sync ./out "s3://$FRONTEND_BUCKET/" --delete
cd ..

# 4. Final messages
echo -e "\n✅ Deployment complete!"
echo "🌐 CloudFront URL : $(terraform -chdir=terraform output -raw cloudfront_url)"
if [ -n "$CUSTOM_URL" ]; then
  echo "🔗 Custom domain  : $CUSTOM_URL"
fi
echo "📡 API Gateway    : $API_URL"
