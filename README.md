# deterministic-operations-container-image-pipeline

![License](https://img.shields.io/badge/License-MIT%20No%20Attribution-blue.svg)
![Cloud](https://img.shields.io/badge/cloud-Huawei%20Cloud-orange.svg)
一个「容器镜像构建与发布」的自动化最佳实践：用 **GitHub Actions 可复用工作流 + Terraform** 声明式创建华为云容器镜像服务（SWR）仓库，并通过 **OpenID Connect（OIDC）** 实现免长期密钥访问，将「认证 → 登录 → 构建 → 推送」流水线收敛为一次触发，降低人为操作错误、缩短镜像发布周期。

## 1. 简介 / Overview

### 简介


手动构建并发布容器镜像，往往需要反复执行 `docker build`、`docker tag`、`docker push`，还要事先手工创建镜像仓库与访问令牌，步骤繁琐且容易出错。

本实践用一个 **GitHub Actions 可复用工作流** 把「认证 → 登录 → 构建 → 推送」链路自动化：触发后自动换取短期凭证、登录镜像仓库、构建并推送镜像；镜像仓库本身由 **Terraform** 以声明式方式创建（或更新），仓库配置全部以代码形式管理，可复现、可审计。

适用于：希望以「基础设施即代码 + CI/CD」方式统一管理容器镜像发布流程的研发团队。

---

## 2. 目录

- [1. 简介 / Overview](#1-简介--overview)
- [2. 目录](#2-目录)
- [3. 架构图](#3-架构图)
- [4. 方案亮点](#4-方案亮点)
- [5. 涉及云服务](#5-涉及云服务)
- [6. 前置条件](#6-前置条件)
- [7. 快速开始](#7-快速开始)
- [8. 分步部署](#8-分步部署)
- [9. 使用方法 / 验证](#9-使用方法--验证)
- [10. 清理资源](#10-清理资源)
- [11. 详细说明](#11-详细说明)
- [12. 依赖](#12-依赖)
- [13. FAQ / 故障排除](#13-faq--故障排除)
- [14. 贡献指南](#14-贡献指南)
- [15. 许可证](#15-许可证)
- [16. 联系方式 / 维护者](#16-联系方式--维护者)

---

## 3. 架构图

```
          GitHub 仓库 push / 手动触发
                          │
                          ▼
        ┌─────────────────────────────────────┐
        │   GitHub Actions 可复用工作流        │
        │   1. OIDC 免长期密钥认证             │
        │   2. 安装 SWR SDK                   │
        │   3. 登录 SWR（短期登录指令）         │
        │   4. docker build + push            │
        └─────────────────────────────────────┘
                  │                │
          ┌───────┴──────┐  ┌──────▼──────────┐
          │ OBS（状态存储）│  │ SWR（组织+仓库） │
          └──────────────┘  └─────────────────┘
```

---

## 4. 方案亮点

- **免长期密钥**：全程使用短期临时凭证（OIDC 换取的临时访问凭证 + SWR 短期登录指令），不在仓库中保存长期密钥。
- **声明式建仓**：镜像仓库、保留策略由 Terraform 声明式创建；新增仓库只需更新 `infra/main.tf` 并执行一次 `terraform apply`。
- **一键发布**：单次触发即可完成「认证 → 登录 → 构建 → 推送」。
- **镜像保留策略**：按「最近 N 个镜像 tag」自动清理旧镜像，避免版本无限膨胀。

---

## 5. 涉及云服务

| 服务 | 用途 |
|---|---|
| 容器镜像服务 SWR | 托管镜像仓库（组织 + 仓库 + 保留策略） |
| 对象存储服务 OBS | 存放 Terraform 状态文件 |
| 统一身份认证 IAM | OIDC 身份提供商、用户组与权限 |
| 资源编排服务（Terraform） | 声明式管理上述资源 |

> 使用完毕后，请按「清理资源」章节释放相关资源，避免残留。

---

## 6. 前置条件

- 一个 GitHub 账号及一个 GitHub 仓库；
- 一个已开通 SWR、OBS、IAM 的华为云账号；
- Terraform v1.5 及以上；
- 一个用于存放 Terraform 状态的 OBS 桶；
- 一个已完成 OIDC 配置的 IAM 身份提供商（见 [分步部署](#8-分步部署) 第 1 步）。

---

## 7. 快速开始

```bash
# 1. 克隆本仓库
git clone https://github.com/dgc-git/deterministic-operations-container-image-pipeline.git
cd deterministic-operations-container-image-pipeline

# 2. 进入基础设施目录并初始化
cd infra
terraform init

# 3. 应用（创建 SWR 组织 + 镜像仓库 + 保留策略）
terraform apply
```

随后在 GitHub Actions 控制台触发 `Container image build and publish` 工作流，填写组织名与区域即可。

---

## 8. 分步部署

### 第 1 步：配置 OIDC 免长期密钥接入

在华为云 IAM 控制台「身份提供商」中创建 OIDC 协议身份提供商，填写：

- 身份提供商 URL：`https://token.actions.githubusercontent.com`
- 客户端 ID（audience）：自定义字符串，用于与 GitHub 侧校验
- 签名公钥：GitHub OIDC JWKS 中的 RSA 公钥

> 也可通过 `infra/identity.tf`（设置 `create_oidc_provider = true`）声明式创建。

### 第 2 步：授予推送权限

为 OIDC 登录产生的联邦用户/用户组，在 SWR 组织管理中授予「写入」或「管理」权限。

### 第 3 步：准备状态桶

在 OBS 中创建状态桶，并使 `infra/versions.tf` 的 `backend "s3"`（指向 OBS 端点）参数与其一致。

### 第 4 步：配置 GitHub Secrets

在 GitHub 仓库 Settings → Secrets → Actions 中配置：

| Secret | 说明 |
|---|---|
| `HW_DOMAIN_NAME` | 华为云账号域名 |

### 第 5 步：部署

```bash
cd infra
terraform init
terraform plan
terraform apply
```

### 第 6 步：触发工作流

在 GitHub Actions 控制台手动触发 `Container image build and publish`，按要求填写 `organization_name`、`backend_obs_bucket`、`region` 等参数。

---

## 9. 使用方法 / 验证

### 使用方法


部署完成后，请按以下步骤验证功能是否可用：

1. 触发工作流后，在 Actions 日志中确认各步骤均成功；
2. 查看工作流的 `image_tag` 与 `full_image` 输出；
3. 手动验证镜像可被拉取：

```bash
cd infra
terraform output repository_path

docker pull <repository_path>:<image_tag>
```

4. 在 SWR 控制台确认镜像已存在，且保留策略已生效。

> 请按本节步骤自行验证，确认业务功能可用后，方可视为部署完成。

---

## 10. 清理资源

```bash
# 释放 SWR 组织及其下仓库
cd infra
terraform destroy
```

---

## 11. 详细说明

### 工作流

`.github/workflows/workflow.yaml` 定义了可复用工作流，核心步骤：

1. **OIDC 认证**：由 `vbem/configure-huawei-cloud-credentials` 动作用 GitHub 发放的短期 JWT 换取华为云临时访问凭证；
2. **安装 SWR SDK**：安装 Python 版 SWR SDK，供登录脚本使用；
3. **登录镜像仓库**：调用 `scripts/swr-docker-login.py`，通过 SWR 短期登录指令写入 Docker 登录配置；
4. **构建与推送**：`docker build` 后 `docker push` 到指定仓库。

### 镜像仓库与保留策略

镜像仓库由 Terraform 在 `infra/main.tf` 中声明（在工作流触发前完成创建）：

- `huaweicloud_swr_organization`：镜像命名空间（组织）；
- `huaweicloud_swr_repository`：私有镜像仓库；
- `huaweicloud_swr_image_retention_policy`：保留最近 N 个镜像 tag；
- `huaweicloud_swr_temporary_login_command`：生成短期登录指令。

### 配置项

`infra/variables.tf` 定义了区域、组织名、仓库名、保留数量、OIDC 相关参数等，均可按需覆盖。

---

## 12. 依赖

- Terraform v1.5+
- `huaweicloud/huaweicloud` Provider（~> 1.70）
- Docker
- Python 3（用于 `scripts/swr-docker-login.py`）

---

## 13. FAQ / 故障排除

### FAQ


**Q：为什么仓库是私有的？**
镜像仓库默认私有，仅授权身份可拉取/推送；如需公开只读，可将 `is_public` 置为 `true`。

**Q：OIDC 换取凭证失败怎么办？**
请确认：GitHub 工作流已设置 `permissions.id-token: write`；IAM 身份提供商的客户端 ID、签名公钥与 GitHub 侧一致；联邦用户/用户组已被授予 SWR 推送权限。

**Q：如何改为每次 push 都触发？**
将 `workflow.yaml` 的触发条件由 `workflow_dispatch` 改为 `push` 或 `workflow_call` 即可。

---

## 14. 贡献指南

见 [CONTRIBUTING](CONTRIBUTING.md)。

---

## 15. 许可证

本实践采用 **MIT No Attribution** 许可证，详见 [LICENSE](LICENSE)。

---

## 16. 联系方式 / 维护者
| 项 | 内容 |
|---|---|
| **创建者** | [dgc-git](https://github.com/dgc-git) |
| **维护者** | [dgc-git](https://github.com/dgc-git) |
| **联系方式** | GitHub Issues / PR（见[第 14 节](#14-贡献指南)） |
