terraform {
  required_version = ">= 1.5"

  required_providers {
    huaweicloud = {
      source  = "huaweicloud/huaweicloud"
      version = "~> 1.70"
    }
  }

  # 状态文件存放于 OBS 对象存储，通过 Terraform 远程后端访问；
  # OBS 使用默认的 virtual-host 寻址，且不支持远程状态锁。
  backend "s3" {
    endpoint = "https://obs.cn-north-4.myhuaweicloud.com"
    bucket   = "container-image-pipeline-tfstate"
    key      = "container-image-pipeline/terraform.tfstate"
    region   = "cn-north-4"

    skip_region_validation      = true
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_requesting_account_id  = true
  }
}