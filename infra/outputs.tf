# ============================================================================
# 输出
# ============================================================================

output "organization_name" {
  description = "SWR 组织（命名空间）名称"
  value       = huaweicloud_swr_organization.this.name
}

output "repository_name" {
  description = "SWR 镜像仓库名称"
  value       = huaweicloud_swr_repository.this.name
}

output "repository_full_name" {
  description = "镜像完整地址（组织/仓库）"
  value       = "${huaweicloud_swr_organization.this.name}/${huaweicloud_swr_repository.this.name}"
}

output "repository_path" {
  description = "镜像 docker pull 地址"
  value       = huaweicloud_swr_repository.this.path
}

output "login_server" {
  description = "镜像仓库登录服务器地址"
  value       = huaweicloud_swr_organization.this.login_server
}

output "docker_login_command" {
  description = "短期 docker login 命令（CI/CD 免长期密钥登录镜像仓库用）"
  value       = huaweicloud_swr_temporary_login_command.this.x_swr_docker_login
  sensitive   = true
}