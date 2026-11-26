# ============================================================================
# SWR 镜像仓库 + 保留策略 + 临时登录指令
# ============================================================================

resource "huaweicloud_swr_organization" "this" {
  name = var.organization_name
}

resource "huaweicloud_swr_repository" "this" {
  organization = huaweicloud_swr_organization.this.name
  name         = var.repository_name
  description  = var.repository_description
  category     = var.repository_category
  is_public    = false
}

# 镜像保留策略（对应镜像生命周期策略）
resource "huaweicloud_swr_image_retention_policy" "this" {
  organization = huaweicloud_swr_organization.this.name
  repository   = huaweicloud_swr_repository.this.name
  type         = "tag_rule"
  number       = var.retention_number
}

# 临时登录指令：生成短期 docker login 命令，供 CI/CD 免长期密钥登录镜像仓库。
resource "huaweicloud_swr_temporary_login_command" "this" {
  # 默认生成短期登录指令（增强模式可选）
}