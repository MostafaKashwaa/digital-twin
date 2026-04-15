locals {
  aliases = var.use_custom_domain && var.root_domain != "" ? [
    var.root_domain,
    "www.${var.root_domain}"
  ] : []

  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}