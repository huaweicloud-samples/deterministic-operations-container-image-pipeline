# 部署指导书

本指导书介绍如何在本仓库上部署并验证「容器镜像构建与发布」工作流。

## 前置条件

| 项目 | 说明 |
|---|---|
| GitHub 账号 | 一个已创建的 GitHub 仓库 |
| 华为云账号 | 已开通 SWR 容器镜像服务、OBS 对象存储服务、IAM 统一身份认证 |
| Terraform | v1.5 及以上 |
| OBS 状态桶 | 一个用于存放 Terraform 状态文件的 OBS 桶（与 `versions.tf` 中的配置一致） |
| OIDC 身份提供商 | 见下方「配置 OIDC 免长期密钥接入」 |
| IAM 用户组 | 一个用于授予镜像推送权限的 IAM 用户组 |

## 1. 配置 OIDC 免长期密钥接入

GitHub Actions 通过 OpenID Connect 向华为云换取短期临时凭证，全程无需保存长期密钥。

### 1.1 创建 OIDC 身份提供商

在华为云 IAM 控制台「身份提供商」中创建 **OIDC 协议** 的身份提供商：

- **身份提供商 URL**：`https://token.actions.githubusercontent.com`
- **授权端点**：`https://token.actions.githubusercontent.com`
- **客户端 ID（audience）**：自定义一个字符串（例如 `swr-image-pipeline`），后续用于 GitHub 侧验证
- **签名公钥**：从 GitHub OIDC 的 JWKS 端点获取

> 也可以通过在 `infra/identity.tf` 中开启 `create_oidc_provider = true` 由 Terraform 完成声明式创建（需管理员权限），并配合 IAM「身份转换规则」将 GitHub 的 `sub` 声明映射到虚拟用户。

### 1.2 授予推送权限

为 OIDC 登录产生的联邦用户/用户组，授予 SWR 组织的「写入」或「管理」权限（在 SWR 控制台的「组织管理 → 权限」中分配），使工作流能够向其推送镜像。

## 2. 准备 Terraform 状态桶

在 OBS 中创建一个状态桶（示例名 `container-image-pipeline-tfstate`），并确保 `infra/versions.tf` 中的 `backend "s3"`（指向 OBS 端点）参数与其一致。

> **受限 IAM 账号注意**：若你的账号没有「列出账号域」的权限，provider 自动发现会报 `List domains failed`。此时请在 `terraform plan`/`apply` 时显式传入账号域与项目：
>
> ```bash
> terraform apply \
>   -var 'domain_name=<账号域名>' \
>   -var 'domain_id=<账号域 ID>' \
>   -var 'project_id=<项目 ID>' \
>   -var 'project_name=<区域>'
> ```
>
> 这些值可在 IAM「我的凭证」或控制台地址栏中查到。

## 3. 配置 GitHub 仓库

### 3.1 Secrets

在 GitHub 仓库的 Settings → Secrets → Actions 中配置：

| Secret | 说明 |
|---|---|
| `HW_DOMAIN_NAME` | 华为云账号域名（IAM 账号域） |

工作流运行时的临时凭证由 OIDC 动态换取，无需配置长期访问密钥。

### 3.2 工作流触发

本工作流支持手动触发（`workflow_dispatch`），触发时需填写：

- `organization_name`：SWR 组织（命名空间）名称
- `backend_obs_bucket`：Terraform 状态 OBS 桶名
- `region`：目标区域（默认 `cn-north-4`）
- `image_tag`：镜像 tag（默认 `snapshot-artifact`）

若需在每次 push 时自动触发，可将 `workflow.yaml` 中的触发方式改为 `push` 或 `workflow_call`。

## 4. 部署步骤

```bash
# 进入基础设施目录
cd infra

# 初始化（使用 OBS 远程后端）
terraform init

# 校验（可选，正式应用前确认无误）
terraform plan

# 应用：创建 SWR 组织 + 镜像仓库 + 保留策略 + 临时登录指令
terraform apply
```

随后在 GitHub Actions 控制台触发 `Container image build and publish` 工作流。

## 5. 验证

工作流成功结束后，可看到镜像已推送到 SWR：

```bash
# 使用 Terraform 输出查看镜像地址
cd infra
terraform output repository_path

# 拉取验证
docker pull <repository_path>:<image_tag>
```

工作流结束时应输出 `image_tag` 与 `full_image`，二者的值与实际推送的镜像地址一致。