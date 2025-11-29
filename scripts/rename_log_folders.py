#!/usr/bin/env python3
"""
批量重命名包含空格的日志文件夹，将空格替换为下划线
用于修复 Windows 兼容性问题
"""

import os
import sys
from pathlib import Path

def rename_folders_with_spaces(base_dir: Path):
    """
    递归查找并重命名包含空格的文件夹

    Args:
        base_dir: 基础目录路径
    """
    renamed_count = 0
    error_count = 0

    # 查找所有包含空格的目录
    folders_to_rename = []
    for root, dirs, files in os.walk(base_dir):
        for dir_name in dirs:
            if ' ' in dir_name:
                old_path = Path(root) / dir_name
                new_name = dir_name.replace(' ', '_')
                new_path = Path(root) / new_name

                # 如果新名称已存在，跳过
                if new_path.exists():
                    print(f"⚠️  跳过: {new_path} 已存在")
                    continue

                folders_to_rename.append((old_path, new_path))

    # 按路径深度排序，先处理深层目录
    folders_to_rename.sort(key=lambda x: len(str(x[0])), reverse=True)

    print(f"📋 找到 {len(folders_to_rename)} 个需要重命名的文件夹\n")

    for old_path, new_path in folders_to_rename:
        try:
            print(f"🔄 重命名: {old_path.name} -> {new_path.name}")
            old_path.rename(new_path)
            renamed_count += 1
        except Exception as e:
            print(f"❌ 错误: 无法重命名 {old_path}: {e}")
            error_count += 1

    print(f"\n✅ 完成!")
    print(f"   - 成功重命名: {renamed_count} 个文件夹")
    if error_count > 0:
        print(f"   - 失败: {error_count} 个文件夹")

    return renamed_count, error_count


def main():
    """主函数"""
    # 获取项目根目录
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent

    # 要处理的目录列表
    target_dirs = [
        project_root / "data" / "agent_data",
        project_root / "data" / "agent_data_astock",
    ]

    total_renamed = 0
    total_errors = 0

    for target_dir in target_dirs:
        if not target_dir.exists():
            print(f"ℹ️  目录不存在，跳过: {target_dir}")
            continue

        print(f"\n{'='*60}")
        print(f"📁 处理目录: {target_dir}")
        print(f"{'='*60}")

        renamed, errors = rename_folders_with_spaces(target_dir)
        total_renamed += renamed
        total_errors += errors

    print(f"\n{'='*60}")
    print(f"📊 总计:")
    print(f"   - 成功重命名: {total_renamed} 个文件夹")
    if total_errors > 0:
        print(f"   - 失败: {total_errors} 个文件夹")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
