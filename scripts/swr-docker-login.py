#!/usr/bin/env python3
"""
使用 OIDC 换取的华为云临时凭证登录 SWR，为 docker push 做准备。

读取 vbem/configure-huawei-cloud-credentials 导出的临时凭据
（HUAWEICLOUD_SDK_AK / HUAWEICLOUD_SDK_SK / HUAWEICLOUD_SDK_SECURITY_TOKEN），
调用 SWR 的 create_authorization_token 换取短期 docker 登录令牌，
写入 ~/.docker/config.json，供 docker push 使用。
"""

import json
import os

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkswr.v2 import CreateAuthorizationTokenRequest, SwrClient
from huaweicloudsdkswr.v2.region.swr_region import SwrRegion


def main() -> None:
    ak = os.environ["HUAWEICLOUD_SDK_AK"]
    sk = os.environ["HUAWEICLOUD_SDK_SK"]
    st = os.environ.get("HUAWEICLOUD_SDK_SECURITY_TOKEN", "")
    region = os.environ.get("HW_REGION", os.environ.get("HW_REGION_NAME", "cn-north-4"))

    cred = BasicCredentials(ak, sk)
    if st:
        cred = cred.with_security_token(st)
    cred = cred.with_iam_endpoint(f"https://iam.{region}.myhuaweicloud.com")

    client = (
        SwrClient.new_builder()
        .with_credentials(cred)
        .with_region(SwrRegion.value_of(region))
        .build()
    )

    resp = client.create_authorization_token(CreateAuthorizationTokenRequest())
    auths = resp.to_dict().get("auths", {})

    docker_dir = os.path.expanduser("~/.docker")
    os.makedirs(docker_dir, exist_ok=True)
    cfg_path = os.path.join(docker_dir, "config.json")
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump({"auths": auths}, f)
    print(f"SWR docker login config written to {cfg_path}")


if __name__ == "__main__":
    main()