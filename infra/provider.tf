provider "huaweicloud" {
  # 区域由变量控制（默认 cn-north-4）；访问密钥通过环境变量提供，不落盘。
  #
  # domain_id / project_id / project_name 默认留空，由 provider 自动发现。
  # 若使用的是受限 IAM 账号（无「列出账号域」的 admin 权限），自动发现会失败，
  # 此时必须在 terraform.tfvars 或 -var 中显式填入 domain_id 与 project_id。
  region       = var.region
  domain_name  = var.domain_name
  domain_id    = var.domain_id
  project_id   = var.project_id
  project_name = var.project_name
}