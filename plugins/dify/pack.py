import os
import zipfile
import yaml
from pathlib import Path

# 必须排除的目录和文件后缀，否则 plugin_daemon 解码会失败 (PluginDecodeResponse)
EXCLUDE_DIRS = {"__pycache__", ".git", ".venv", "venv", ".idea", ".vscode", "node_modules"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".pyd", ".swp", ".DS_Store"}
EXCLUDE_FILES = {"pack.py", ".gitignore", ".env", ".env.example"}

def should_exclude(file_path: str) -> bool:
    parts = Path(file_path).parts
    for part in parts:
        if part in EXCLUDE_DIRS:
            return True
    if Path(file_path).suffix in EXCLUDE_SUFFIXES:
        return True
    if Path(file_path).name in EXCLUDE_FILES:
        return True
    return False

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
    for f in ["manifest.yaml", "main.py", "pyproject.toml", "requirements.txt", "README.md"]:
        if Path(f).exists():
            files_to_pack.append(f)

    # 自动打包所有必需的目录
    for d in ["_assets", "provider", "models"]:
        dir_path = Path(d)
        if dir_path.exists() and dir_path.is_dir():
            for root, dirs, files in os.walk(dir_path):
                # 原地修改 dirs 以跳过排除目录（阻止 os.walk 继续遍历）
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
                for file in files:
                    full_path = os.path.join(root, file)
                    if not should_exclude(full_path):
                        files_to_pack.append(full_path)

    with zipfile.ZipFile(pkg_name, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in files_to_pack:
            arcname = os.path.relpath(file_path, ".")
            zipf.write(file_path, arcname)
            print(f"✅ 添加：{arcname}")

    print(f"\n🎉 打包成功：{pkg_name}")

if __name__ == "__main__":
    pack_plugin()