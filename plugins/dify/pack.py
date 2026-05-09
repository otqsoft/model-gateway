import os
import zipfile
import yaml
from pathlib import Path

def pack_plugin():
    manifest_path = Path("manifest.yaml")
    if not manifest_path.exists():
        print("❌ manifest.yaml not found!")
        return

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    plugin_name = manifest.get("name", "plugin")
    version = manifest.get("version", "0.0.1")
    pkg_name = f"{plugin_name}_{version}.difypkg"

    files_to_pack = []

    # 根文件
    for f in ["manifest.yaml", "main.py"]:
        if Path(f).exists():
            files_to_pack.append(f)

    # 自动打包所有必需的目录
    for d in ["_assets", "provider", "models"]:
        dir_path = Path(d)
        if dir_path.exists() and dir_path.is_dir():
            for root, _, files in os.walk(dir_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    files_to_pack.append(full_path)

    with zipfile.ZipFile(pkg_name, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in files_to_pack:
            arcname = os.path.relpath(file_path, ".")
            zipf.write(file_path, arcname)
            print(f"✅ 添加：{arcname}")

    print(f"\n🎉 打包成功：{pkg_name}")
    # print("✅ 已包含：provider / models / _assets")

if __name__ == "__main__":
    pack_plugin()