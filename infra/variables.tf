# ============================================================================
# 输入变量
# ============================================================================

variable "region" {
  description = "目标区域"
  type        = string
  default     = "cn-north-4"
}

variable "organization_name" {
  description = "SWR 组织（命名空间）名称，全局唯一"
  type        = string
}

variable "repository_name" {
  description = "SWR 镜像仓库名称（小写字母、数字、点、连字符、下划线）"
  type        = string
}

variable "repository_description" {
  description = "镜像仓库描述"
  type        = string
  default     = ""
}

variable "repository_category" {
  description = "镜像仓库分类"
  type        = string
  default     = "linux"
}

variable "retention_number" {
  description = "保留策略：保留最近的镜像 tag 数量"
  type        = number
  default     = 30
}

# ----------------------------------------------------------------------------
# OIDC 联邦认证（GitHub Actions 免长期密钥）相关变量
# ----------------------------------------------------------------------------
# 这些变量仅在需要「由 Terraform 一并创建 OIDC 身份提供商」时使用；
# 若身份提供商已在 IAM 控制台手工创建，可跳过 identity.tf 中的资源。

variable "create_oidc_provider" {
  description = "是否由 Terraform 创建 OIDC 身份提供商"
  type        = bool
  default     = false
}

variable "oidc_provider_name" {
  description = "OIDC 身份提供商名称（IAM 内唯一）"
  type        = string
  default     = "github-actions"
}

variable "oidc_client_id" {
  description = "OIDC 客户端 ID（作为 GitHub OIDC token 的 audience）"
  type        = string
  default     = ""
  sensitive   = false
}

variable "oidc_signing_key" {
  description = "身份提供商签名公钥（GitHub OIDC JWKS 中的 RSA 公钥，JSON 文本）"
  type        = string
  default     = ""
}

variable "federated_group_name" {
  description = "联邦用户映射到的 IAM 用户组名（用于授予镜像推送权限）"
  type        = string
  default     = "github-actions-image-publisher"
}

# ----------------------------------------------------------------------------
# 账号域 / 项目（受限 IAM 账号需显式指定，避免自动发现失败）
# ----------------------------------------------------------------------------

variable "domain_name" {
  description = "华为云账号域名（IAM 账号域）"
  type        = string
  default     = ""
}

variable "domain_id" {
  description = "华为云账号域 ID（受限账号必须显式提供）"
  type        = string
  default     = ""
}

variable "project_id" {
  description = "目标项目 ID（受限账号必须显式提供）"
  type        = string
  default     = ""
}

variable "project_name" {
  description = "目标项目名称"
  type        = string
  default     = ""
}
