"""
Dify 插件签名工具

复刻 dify-plugin-daemon 的 withkey.SignPluginWithPrivateKey 算法:
1. 遍历 zip 中所有文件（按 zip 顺序），计算每个文件 SHA-256 并拼接
2. 追加 .verification.dify.json 的 SHA-256
3. 追加当前 Unix 时间戳的十进制字符串
4. 对拼接后的 data 做 SHA-256，再用 RSA PKCS#1 v1.5 签名
5. 将签名 base64 编码后放入 zip comment: {"signature":"...","time":123}

用法:
    python sign.py <input.difypkg> <private.pem> [output.signed.difypkg]
"""
import sys
import json
import time
import hashlib
import base64
import zipfile
import io
from typing import Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.backends import default_backend


VERIFICATION_FILE = ".verification.dify.json"
VERIFICATION_JSON = json.dumps({"authorized_category": "langgenius"}, separators=(",", ":"))


def sign_plugin(input_path: str, private_key_path: str, output_path: Optional[str] = None):
    # 读取私钥
    with open(private_key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(), password=None, backend=default_backend()
        )

    # 读取原始包
    with open(input_path, "rb") as f:
        original_bytes = f.read()

    src_zip = zipfile.ZipFile(io.BytesIO(original_bytes))

    # 创建新 zip
    out_buf = io.BytesIO()
    out_zip = zipfile.ZipFile(out_buf, "w", zipfile.ZIP_DEFLATED)

    # data buffer: 依次拼接每个文件的 SHA-256
    data = bytearray()

    # 遍历原始包中的文件，按 zip 顺序
    for info in src_zip.infolist():
        file_bytes = src_zip.read(info.filename)
        # 计算 SHA-256 并追加到 data
        data.extend(hashlib.sha256(file_bytes).digest())
        # 写入新 zip
        out_zip.writestr(info.filename, file_bytes)

    # 写入 .verification.dify.json
    verification_bytes = VERIFICATION_JSON.encode("utf-8")
    out_zip.writestr(VERIFICATION_FILE, verification_bytes)
    # 追加 verification 的 SHA-256 到 data
    data.extend(hashlib.sha256(verification_bytes).digest())

    # 追加时间戳字符串
    now = int(time.time())
    data.extend(str(now).encode("ascii"))

    # 签名: SHA-256(data) -> RSA PKCS#1 v1.5
    # 与 Go 的 sha256.Sum256(data) + rsa.SignPKCS1v15 完全一致
    data_bytes = bytes(data)
    hashed = hashlib.sha256(data_bytes).digest()
    signature = private_key.sign(
        hashed,
        padding.PKCS1v15(),
        Prehashed(SHA256()),
    )

    # 设置 zip comment
    comment = json.dumps(
        {"signature": base64.b64encode(signature).decode("ascii"), "time": now},
        separators=(",", ":"),
    )
    out_zip.comment = comment.encode("utf-8")
    out_zip.close()

    # 确定输出路径
    if output_path is None:
        if input_path.endswith(".difypkg"):
            base = input_path[:-8]
            output_path = f"{base}.signed.difypkg"
        else:
            output_path = input_path + ".signed"

    with open(output_path, "wb") as f:
        f.write(out_buf.getvalue())

    print(f"✅ 签名成功: {output_path}")
    print(f"   时间戳: {now}")
    print(f"   签名长度: {len(signature)} bytes")
    print(f"   文件数: {len(src_zip.infolist())} + 1 (verification)")
    return output_path


def verify_plugin(signed_path: str, public_key_path: str):
    """验证签名（用公钥）"""
    with open(public_key_path, "rb") as f:
        public_key = serialization.load_pem_public_key(f.read(), backend=default_backend())

    z = zipfile.ZipFile(signed_path)
    comment = json.loads(z.comment)
    signature = base64.b64decode(comment["signature"])
    ts = comment["time"]

    # 重建 data buffer
    data = bytearray()
    for info in z.infolist():
        file_bytes = z.read(info.filename)
        data.extend(hashlib.sha256(file_bytes).digest())

    data.extend(str(ts).encode("ascii"))

    # 验证: SHA-256(data) -> RSA PKCS#1 v1.5 (prehashed)
    data_bytes = bytes(data)
    hashed = hashlib.sha256(data_bytes).digest()
    public_key.verify(
        signature,
        hashed,
        padding.PKCS1v15(),
        Prehashed(SHA256()),
    )
    print(f"✅ 验证通过: {signed_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python sign.py <input.difypkg> <private.pem> [output.signed.difypkg]")
        sys.exit(1)

    input_pkg = sys.argv[1]
    key_path = sys.argv[2]
    output_pkg = sys.argv[3] if len(sys.argv) > 3 else None

    signed = sign_plugin(input_pkg, key_path, output_pkg)

    # 自动验证
    pub_path = key_path.replace("private.pem", "public.pem")
    try:
        verify_plugin(signed, pub_path)
    except Exception as e:
        print(f"⚠️ 自动验证失败 (公钥可能不在同目录): {e}")
