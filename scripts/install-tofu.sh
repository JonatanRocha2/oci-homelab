#!/usr/bin/env bash
set -euo pipefail
version="1.13.9"
file="tofu_${version}_linux_amd64.zip"
checksum="bc44eb6b06446ba83bd4072114891987f590f66cca712737a7f1147c50c539ce"
curl -fsSL -o "${file}" "https://github.com/opentofu/opentofu/releases/download/v${version}/${file}"
echo "${checksum}  ${file}" | sha256sum -c -
sudo unzip -o -d /usr/local/bin "${file}" tofu
rm -f "${file}"
tofu version
