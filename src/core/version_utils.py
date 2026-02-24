"""
版本工具模块。

提供版本号解析、排序、分组等工具函数。
"""

import re
from typing import List, Dict, Any


def _parse_version(version_str: str) -> tuple:
    """
    解析版本字符串为可比较的元组。
    
    参数:
        version_str: 版本字符串
        
    返回:
        版本元组 (major, minor, patch, ...)
    """
    parts = re.findall(r'\d+', version_str)
    return tuple(int(p) for p in parts) if parts else (0,)


def sort_versions_desc(versions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    按版本号降序排列版本列表。
    
    参数:
        versions: 版本信息列表
        
    返回:
        排序后的版本列表
    """
    return sorted(
        versions,
        key=lambda v: _parse_version(v.get("version", "0")),
        reverse=True
    )


def group_versions_by_major(versions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    按主版本号分组版本列表。
    
    参数:
        versions: 版本信息列表
        
    返回:
        分组后的版本列表，每个分组包含 major_version 和 versions
    """
    sorted_versions = sort_versions_desc(versions)
    groups = {}
    
    for v in sorted_versions:
        version_str = v.get("version", "0")
        parts = version_str.split(".")
        major = parts[0] if parts else "0"
        
        if major not in groups:
            groups[major] = {
                "major_version": major,
                "versions": [],
                "has_lts": False
            }
        
        groups[major]["versions"].append(v)
        if v.get("lts"):
            groups[major]["has_lts"] = True
    
    result = list(groups.values())
    result.sort(key=lambda g: int(g["major_version"]) if g["major_version"].isdigit() else 0, reverse=True)
    
    return result
