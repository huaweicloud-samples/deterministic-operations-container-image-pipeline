# ============================================================================
# OIDC 联邦认证（GitHub Actions 免长期密钥接入，可选身份提供商 IaC）
# ============================================================================
#
# 用途：让 GitHub Actions 通过 OpenID Connect 换取华为云「临时凭证」，
# 从而避免在仓库/工作流中保存长期访问密钥。这与「在 IAM 控制台手工创建
# 身份提供商」的效果一致，此处以 IaC 形式声明（默认关闭）。
#
# 前置：OIDC 身份提供商为账号级资源，需管理员权限；且 GitHub 的 OIDC
# issuer 为 https://token.actions.githubusercontent.com。
# 手工步骤（身份提供商创建后仍需完成）：
#   1) 创建 IAM 用户组（var.federated_group_name），并为其授予 SWR 推送权限；
#   2) 将 GitHub OIDC token 的 audience（aud/客户端 ID）填写为 var.oidc_client_id；
#   3) 在 IAM「身份提供商」中配置转换规则，将 GitHub 的 sub 声明映射到虚拟用户。

resource "huaweicloud_identity_provider" "github_actions" {
  count = var.create_oidc_provider ? 1 : 0

  name        = var.oidc_provider_name
  protocol    = "oidc"
  description = "GitHub Actions OIDC identity provider"
  sso_type    = "virtual_user_sso"

  access_config {
    access_type            = "program"
    provider_url           = "https://token.actions.githubusercontent.com"
    client_id              = var.oidc_client_id
    authorization_endpoint = "https://token.actions.githubusercontent.com"
    scopes                 = ["openid"]
    signing_key            = var.oidc_signing_key
  }
}

# 转换规则：把 GitHub OIDC token 中的 sub 声明映射到华为云虚拟用户，
# 并将该虚拟用户归入指定的 IAM 用户组（该组需事先创建并授予 SWR 权限）。
resource "huaweicloud_identity_provider_conversion" "github_actions" {
  count = var.create_oidc_provider ? 1 : 0

  provider_id = huaweicloud_identity_provider.github_actions[0].id

  conversion_rules {
    local {
      username = "github-actions-federated-user"
      group    = var.federated_group_name
    }
    remote {
      attribute = "sub"
    }
  }
}