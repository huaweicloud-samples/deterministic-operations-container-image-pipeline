# deterministic-operations-container-image-pipeline

![License](https://img.shields.io/badge/License-MIT%20No%20Attribution-blue.svg)
![Cloud](https://img.shields.io/badge/cloud-Huawei%20Cloud-orange.svg)
A container image build-and-publish automation practice: a **reusable GitHub Actions workflow + Terraform** declaratively creates a Software Repository for Container (SWR) repository on Huawei Cloud, and uses **OpenID Connect (OIDC)** for credential-less access, collapsing the "auth → login → build → push" pipeline into a single trigger that reduces manual errors and shortens the image release cycle.

## 1. Overview

### Introduction

Manually building and publishing container images often requires repeatedly running `docker build`, `docker tag`, and `docker push`, as well as manually creating an image repository and access token in advance; the process is cumbersome and error-prone.

This practice automates the "auth → login → build → push" chain with a **reusable GitHub Actions workflow**: once triggered, it automatically obtains short-term credentials, logs in to the image repository, and builds and pushes the image; the repository itself is created (or updated) declaratively by **Terraform**, and all repository configuration is managed as code, making it reproducible and auditable.

Ideal for: R&D teams that want to manage the container image release process in a unified way with "infrastructure as code + CI/CD".

---

## 2. Table of Contents

- [1. Overview](#1-overview)
- [2. Table of Contents](#2-table-of-contents)
- [3. Architecture Diagram](#3-architecture-diagram)
- [4. Highlights](#4-highlights)
- [5. Cloud Services Used](#5-cloud-services-used)
- [6. Prerequisites](#6-prerequisites)
- [7. Quick Start](#7-quick-start)
- [8. Step-by-Step Deployment](#8-step-by-step-deployment)
- [9. Usage / Verification](#9-usage--verification)
- [10. Cleanup](#10-cleanup)
- [11. Detailed Explanation](#11-detailed-explanation)
- [12. Dependencies](#12-dependencies)
- [13. FAQ / Troubleshooting](#13-faq--troubleshooting)
- [14. Contributing](#14-contributing)
- [15. License](#15-license)
- [16. Contact / Maintainers](#16-contact--maintainers)

---

## 3. Architecture Diagram

```
          GitHub repository push / manual trigger
                          │
                          ▼
        ┌─────────────────────────────────────┐
        │   Reusable GitHub Actions Workflow  │
        │   1. OIDC credential-less auth      │
        │   2. Install SWR SDK                │
        │   3. Log in to SWR (short-term cmd) │
        │   4. docker build + push            │
        └─────────────────────────────────────┘
                  │                │
          ┌───────┴──────┐  ┌──────▼──────────┐
          │ OBS (state)  │  │ SWR (org + repo)│
          └──────────────┘  └─────────────────┘
```

---

## 4. Highlights

- **No long-term keys**: Short-term temporary credentials are used throughout (temporary access credentials obtained via OIDC + a short-term SWR login command), and no long-term keys are stored in the repository.
- **Declarative repository creation**: Image repositories and retention policies are created declaratively by Terraform; adding a repository only requires updating `infra/main.tf` and running `terraform apply` once.
- **One-click publication**: A single trigger completes the whole "auth → login → build → push" flow.
- **Image retention policy**: Old images are automatically cleaned up by "the most recent N image tags", preventing unbounded version growth.

---

## 5. Cloud Services Used

| Service | Purpose |
|---|---|
| Software Repository for Container (SWR) | Hosts image repositories (organization + repository + retention policy) |
| Object Storage Service (OBS) | Stores Terraform state files |
| Identity and Access Management (IAM) | OIDC identity provider, user groups, and permissions |
| Resource Formation Service (Terraform) | Declaratively manages the above resources |

> After use, release the related resources per the Cleanup section to avoid leftovers.

---

## 6. Prerequisites

- A GitHub account and a GitHub repository;
- A Huawei Cloud account with SWR, OBS, and IAM enabled;
- Terraform v1.5 or later;
- An OBS bucket for storing Terraform state;
- An IAM identity provider with OIDC already configured (see Step 1 in [Step-by-Step Deployment](#8-step-by-step-deployment)).

---

## 7. Quick Start

```bash
# 1. Clone this repository
git clone https://github.com/dgc-git/deterministic-operations-container-image-pipeline.git
cd deterministic-operations-container-image-pipeline

# 2. Enter the infrastructure directory and initialize
cd infra
terraform init

# 3. Apply (create SWR organization + repository + retention policy)
terraform apply
```

Then trigger the `Container image build and publish` workflow in the GitHub Actions console and fill in the organization name and region.

---

## 8. Step-by-Step Deployment

### Step 1: Configure OIDC Credential-less Access

In the Huawei Cloud IAM console, create an OIDC protocol identity provider under "Identity Providers" and fill in:

- Identity provider URL: `https://token.actions.githubusercontent.com`
- Client ID (audience): a custom string used for validation against the GitHub side
- Signing public key: the RSA public key in the GitHub OIDC JWKS

> It can also be created declaratively through `infra/identity.tf` (set `create_oidc_provider = true`).

### Step 2: Grant Push Permissions

For the federated user/user group generated by OIDC login, grant "Write" or "Manage" permissions in SWR organization management.

### Step 3: Prepare the State Bucket

Create a state bucket in OBS and make the `backend "s3"` parameters in `infra/versions.tf` (pointing to the OBS endpoint) consistent with it.

### Step 4: Configure GitHub Secrets

Configure in the GitHub repository Settings → Secrets → Actions:

| Secret | Description |
|---|---|
| `HW_DOMAIN_NAME` | Huawei Cloud account domain name |

### Step 5: Deploy

```bash
cd infra
terraform init
terraform plan
terraform apply
```

### Step 6: Trigger the Workflow

Manually trigger `Container image build and publish` in the GitHub Actions console and fill in parameters such as `organization_name`, `backend_obs_bucket`, and `region` as required.

---

## 9. Usage / Verification

### Usage

After deployment, follow the steps below to verify that the functionality works:

1. After triggering the workflow, confirm in the Actions logs that all steps succeeded;
2. Check the workflow outputs `image_tag` and `full_image`;
3. Manually verify that the image can be pulled:

```bash
cd infra
terraform output repository_path

docker pull <repository_path>:<image_tag>
```

4. In the SWR console, confirm that the image exists and the retention policy is in effect.

> After deployment, follow these steps to verify that the business functionality works before considering the delivery complete.

---

## 10. Cleanup

```bash
# Release the SWR organization and its repositories
cd infra
terraform destroy
```

---

## 11. Detailed Explanation

### Workflow

`.github/workflows/workflow.yaml` defines the reusable workflow. Core steps:

1. **OIDC authentication**: The `vbem/configure-huawei-cloud-credentials` action exchanges the short-lived JWT issued by GitHub for temporary Huawei Cloud access credentials;
2. **Install SWR SDK**: Installs the Python SWR SDK for use by the login script;
3. **Log in to the image repository**: Calls `scripts/swr-docker-login.py` to write the Docker login configuration using the SWR short-term login command;
4. **Build and push**: `docker build` followed by `docker push` to the specified repository.

### Image Repository and Retention Policy

The image repository is declared by Terraform in `infra/main.tf` (created before the workflow is triggered):

- `huaweicloud_swr_organization`: image namespace (organization);
- `huaweicloud_swr_repository`: private image repository;
- `huaweicloud_swr_image_retention_policy`: retains the most recent N image tags;
- `huaweicloud_swr_temporary_login_command`: generates a short-term login command.

### Configuration Items

`infra/variables.tf` defines the region, organization name, repository name, retention count, OIDC-related parameters, etc., all of which can be overridden as needed.

---

## 12. Dependencies

- Terraform v1.5+
- `huaweicloud/huaweicloud` Provider (~> 1.70)
- Docker
- Python 3 (for `scripts/swr-docker-login.py`)

---

## 13. FAQ / Troubleshooting

### FAQ

**Q: Why is the repository private?**
Image repositories are private by default, and only authorized identities can pull/push; for public read-only access, set `is_public` to `true`.

**Q: What if OIDC credential exchange fails?**
Confirm that: the GitHub workflow has `permissions.id-token: write` set; the client ID and signing public key of the IAM identity provider match those on the GitHub side; the federated user/user group has been granted SWR push permissions.

**Q: How to trigger on every push instead?**
Change the trigger condition in `workflow.yaml` from `workflow_dispatch` to `push` or `workflow_call`.

---

## 14. Contributing

See [CONTRIBUTING](CONTRIBUTING.md).

---

## 15. License

This practice is licensed under **MIT No Attribution**; see [LICENSE](LICENSE).

---

## 16. Contact / Maintainers
| Item | Content |
|---|---|
| **Creator** | [dgc-git](https://github.com/dgc-git) |
| **Maintainer** | [dgc-git](https://github.com/dgc-git) |
| **Contact** | GitHub Issues / PR (see [Section 14](#14-contributing)) |
