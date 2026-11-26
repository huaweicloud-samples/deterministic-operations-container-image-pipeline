#!/usr/bin/env python3
"""
GitHub Actions OIDC → 华为云临时凭证 交换助手

用途：在 GitHub Actions 工作流中，用 GitHub 提供的 OIDC id_token（短期 JWT）
换取华为云 IAM 联邦认证的临时访问密钥与安全令牌（SecurityToken），避免在仓库中
保存长期密钥。相当于「使用短期身份凭证完成一次免长期密钥的登录」。

使用前提：
  1) 工作流设置 permissions.id-token: write，GitHub 会注入
     ACTIONS_ID_TOKEN_REQUEST_URL / ACTIONS_ID_TOKEN_REQUEST_TOKEN；
  2) 已在华为云 IAM 配置好 OIDC 身份提供商（协议 oidc），并将 GitHub 的
     OIDC issuer/aud 与签名公钥登记（可参考 infra/identity.tf）。

输出：向 $GITHUB_ENV 写入 HW_ACCESS_KEY / HW_SECRET_KEY / HW_SECURITY_TOKEN，
供后续 terraform / docker 步骤读取。

⚠️ 注意：华为云 IAM「OIDC 联邦认证换取临时凭证」的精确 API 端点与请求字段
会随 IAM API 版本演进，下方端点为最佳努力实现（2026 年口径）。上线前请以
华为云 IAM「联邦身份认证」API 参考为准核对，并在真实账号下实测一次。
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request

IAM_ENDPOINT = "iam.{region}.myhuaweicloud.com"


def _get_github_id_token(aud: str | None) -> str:
    """通过 GitHub Actions 的 id-token 端点获取 OIDC JWT。"""
    request_url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    request_token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    if not request_url or not request_token:
        raise RuntimeError(
            "缺少 ACTIONS_ID_TOKEN_REQUEST_URL / ACTIONS_ID_TOKEN_REQUEST_TOKEN，"
            "请确认工作流已设置 permissions.id-token: write"
        )

    query = urllib.parse.urlencode({"audience": aud}) if aud else ""
    url = f"{request_url}{'&' if '?' in request_url else '?'}{query}" if query else request_url
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {request_token}",
        "Accept": "application/json; api-version=2.0",
    })
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["value"]


def _http_post_json(url: str, payload: dict, headers: dict | None = None) -> tuple[dict, dict]:
    data = json.dumps(payload).encode("utf-8")
    h = {"Content-Type": "application/json;charset=utf8"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            resp_headers = dict(resp.headers)
            body = json.loads(resp.read().decode("utf-8"))
            return body, resp_headers
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"IAM 请求失败 HTTP {exc.code}: {detail}") from exc


def exchange_id_token_for_credentials(
    id_token: str,
    domain_name: str,
    idp_id: str,
    region: str,
    duration_seconds: int = 900,
) -> dict:
    """用外部 OIDC id_token 换取华为云临时访问密钥。

    正确链路（对应 IAM API）：
      1) CreateTokenWithIdToken : POST /v3.0/OS-AUTH/id-token/tokens
         （头 X-Idp-Id 传身份提供商 ID；体 auth.id_token.id + auth.scope）
      2) CreateTemporaryAccessKeyByToken : POST /v3.0/OS-CREDENTIAL/securitytokens
         （头 X-Auth-Token 传上一步的 scoped token）
    """
    base = IAM_ENDPOINT.format(region=region)

    # 第一步：OIDC id_token -> 华为云 scoped token
    fed_body = {
        "auth": {
            "id_token": {"id": id_token},
            "scope": {"domain": {"name": domain_name}},
        }
    }
    _, fed_headers = _http_post_json(
        f"https://{base}/v3.0/OS-AUTH/id-token/tokens",
        fed_body,
        headers={"X-Idp-Id": idp_id},
    )
    subject_token = fed_headers.get("X-Subject-Token")
    if not subject_token:
        raise RuntimeError("联邦认证未返回 scoped token（X-Subject-Token）")

    # 第二步：scoped token -> 临时访问密钥 + 安全令牌
    sts_body = {
        "auth": {
            "identity": {
                "methods": ["token"],
                "token": {"duration-seconds": duration_seconds},
            }
        }
    }
    body, _ = _http_post_json(
        f"https://{base}/v3.0/OS-CREDENTIAL/securitytokens",
        sts_body,
        headers={"X-Auth-Token": subject_token},
    )
    credential = body.get("credential", body)
    if not credential.get("access"):
        raise RuntimeError(f"未从响应中解析到临时凭证: {body}")
    return credential


def main() -> None:
    id_token = _get_github_id_token(aud=os.environ.get("HW_OIDC_AUD") or None)
    credential = exchange_id_token_for_credentials(
        id_token=id_token,
        domain_name=os.environ["HW_DOMAIN_NAME"],
        idp_id=os.environ["HW_OIDC_IDP"],
        region=os.environ.get("HW_REGION", "cn-north-4"),
    )

    # 将临时凭证写入 GitHub Actions 环境（供后续 step 使用）
    gh_env = os.environ.get("GITHUB_ENV")
    if gh_env:
        with open(gh_env, "a", encoding="utf-8") as f:
            f.write(f"HW_ACCESS_KEY={credential['access']}\n")
            f.write(f"HW_SECRET_KEY={credential['secret']}\n")
            f.write(f"HW_SECURITY_TOKEN={credential.get('securitytoken', '')}\n")
    else:
        # 本地调试：打印到 stdout（不进入文件）
        for k in ("access", "secret", "securitytoken"):
            print(f"{k}={credential.get(k, '')}")

    print("✅ 已获取华为云临时凭证（OIDC 免长期密钥）")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"❌ {exc}", file=sys.stderr)
        sys.exit(1)