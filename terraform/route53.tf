# Optional: Custom domain configuration (only created when use_custom_domain = true)
data "aws_route53_zone" "root" {
  count        = var.use_custom_domain ? 1 : 0
  name         = var.root_domain
  private_zone = false
}

resource "aws_acm_certificate" "site" {
  count                     = var.use_custom_domain ? 1 : 0
  provider                  = aws.us_east_1
  domain_name               = var.root_domain
  subject_alternative_names = ["www.${var.root_domain}"]
  validation_method         = "DNS"
  lifecycle { create_before_destroy = true }
  tags = local.common_tags
}

resource "aws_route53_record" "site_validation" {
  for_each = var.use_custom_domain ? {
    for dvo in aws_acm_certificate.site[0].domain_validation_options :
    dvo.domain_name => dvo
  } : {}

  zone_id = data.aws_route53_zone.root[0].zone_id
  name    = each.value.resource_record_name
  type    = each.value.resource_record_type
  ttl     = 300
  records = [each.value.resource_record_value]
}

resource "aws_acm_certificate_validation" "site" {
  count           = var.use_custom_domain ? 1 : 0
  provider        = aws.us_east_1
  certificate_arn = aws_acm_certificate.site[0].arn
  validation_record_fqdns = [
    for r in aws_route53_record.site_validation : r.fqdn
  ]
}

resource "aws_route53_record" "alias_root" {
  count   = var.use_custom_domain ? 1 : 0
  zone_id = data.aws_route53_zone.root[0].zone_id
  name    = var.root_domain
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "alias_root_ipv6" {
  count   = var.use_custom_domain ? 1 : 0
  zone_id = data.aws_route53_zone.root[0].zone_id
  name    = var.root_domain
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "alias_www" {
  count   = var.use_custom_domain ? 1 : 0
  zone_id = data.aws_route53_zone.root[0].zone_id
  name    = "www.${var.root_domain}"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "alias_www_ipv6" {
  count   = var.use_custom_domain ? 1 : 0
  zone_id = data.aws_route53_zone.root[0].zone_id
  name    = "www.${var.root_domain}"
  type    = "AAAA"

  alias {
    name                   = aws_cloudfront_distribution.main.domain_name
    zone_id                = aws_cloudfront_distribution.main.hosted_zone_id
    evaluate_target_health = false
  }
}