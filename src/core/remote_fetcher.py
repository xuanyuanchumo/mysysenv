"""
远程版本获取模块。

提供从镜像源获取工具版本列表的功能。
"""

import re
import platform
from datetime import datetime
from typing import Optional, List, Dict, Any
import requests

from src.utils.logger import get_logger
from src.core.config_manager import ConfigManager
from src.utils.rate_limiter import RateLimiter
from src.core.interfaces import IRemoteFetcher

logger = get_logger()


class RemoteFetcherError(Exception):
    """远程获取错误异常。"""
    pass


class NetworkError(RemoteFetcherError):
    """网络错误异常。"""
    pass


class MirrorError(RemoteFetcherError):
    """镜像源错误异常。"""
    pass


class MirrorStatus:
    """
    镜像源状态跟踪类。
    
    记录镜像源的可用状态、失败时间和原因。
    """
    
    def __init__(self):
        self._status: dict[str, dict[str, Any]] = {}
    
    def record_success(self, mirror_url: str) -> None:
        """
        记录镜像源成功。
        
        参数:
            mirror_url: 镜像源 URL
        """
        self._status[mirror_url] = {
            "last_success": datetime.now(),
            "last_failure": None,
            "failure_reason": None,
            "consecutive_failures": 0
        }
    
    def record_failure(self, mirror_url: str, reason: str) -> None:
        """
        记录镜像源失败。
        
        参数:
            mirror_url: 镜像源 URL
            reason: 失败原因
        """
        current = self._status.get(mirror_url, {
            "last_success": None,
            "last_failure": None,
            "failure_reason": None,
            "consecutive_failures": 0
        })
        current["last_failure"] = datetime.now()
        current["failure_reason"] = reason
        current["consecutive_failures"] = current.get("consecutive_failures", 0) + 1
        self._status[mirror_url] = current
    
    def get_sorted_mirrors(self, mirror_list: List[str]) -> List[str]:
        """
        获取按优先级排序的镜像源列表。
        
        优先使用最近成功的镜像源。
        
        参数:
            mirror_list: 原始镜像源列表
            
        返回:
            排序后的镜像源列表
        """
        def get_priority(mirror_url: str) -> tuple:
            status = self._status.get(mirror_url, {})
            last_success = status.get("last_success")
            consecutive_failures = status.get("consecutive_failures", 0)
            
            if last_success is None:
                return (1, consecutive_failures, 0)
            
            return (0, consecutive_failures, -last_success.timestamp())
        
        return sorted(mirror_list, key=get_priority)
    
    def get_failure_summary(self) -> str:
        """
        获取失败摘要信息。
        
        返回:
            失败摘要字符串
        """
        summaries = []
        for mirror_url, status in self._status.items():
            if status.get("last_failure"):
                summaries.append(
                    f"{mirror_url}: {status.get('failure_reason', '未知错误')} "
                    f"(连续失败 {status.get('consecutive_failures', 0)} 次)"
                )
        return "; ".join(summaries) if summaries else "无失败记录"


class RemoteFetcher(IRemoteFetcher):
    """
    远程版本获取器类。
    
    负责从镜像源获取工具的可用版本列表。
    实现 IRemoteFetcher 抽象接口。
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化远程版本获取器。
        
        参数:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        rate_limit = config_manager.get_request_rate_limit()
        self.rate_limiter = RateLimiter(requests_per_second=rate_limit)
        self._memory_cache: dict[str, dict[str, Any]] = {}
        self.mirror_status = MirrorStatus()
    
    def get_mirror_list(self, tool: str) -> List[str]:
        """
        获取工具的镜像源列表。
        
        参数:
            tool: 工具名称
            
        返回:
            镜像源 URL 列表
        """
        mirror_list = self.config_manager.get_mirror_list(tool)
        return mirror_list if mirror_list else []
    
    def _get_version_fetch_config(self, tool: str) -> Optional[Dict[str, Any]]:
        """
        从配置中获取工具的版本获取规则。
        
        参数:
            tool: 工具名称
            
        返回:
            版本获取配置字典，无配置返回 None
        """
        tool_config = self.config_manager.get_version_fetch_config(tool)
        if tool_config:
            logger.debug(f"获取到 {tool} 的版本获取配置")
        return tool_config if tool_config else None
    
    def get_remote_versions(self, tool: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        获取远程可用的工具版本。
        
        参数:
            tool: 工具名称
            use_cache: 是否使用缓存
            
        返回:
            远程版本信息列表
        """
        cache_key = f"{tool}_versions"
        cache_expire_time = self.config_manager.get_cache_expire_time()
        
        if use_cache and cache_key in self._memory_cache:
            cached = self._memory_cache[cache_key]
            last_update = datetime.fromisoformat(cached.get("last_update", "2000-01-01"))
            if (datetime.now() - last_update).total_seconds() < cache_expire_time:
                logger.info(f"使用内存缓存的 {tool} 版本信息")
                return cached.get("versions", [])
        
        cache = self.config_manager.get_cache()
        if use_cache and cache_key in cache:
            cached = cache[cache_key]
            last_update = datetime.fromisoformat(cached.get("last_update", "2000-01-01"))
            if (datetime.now() - last_update).total_seconds() < cache_expire_time:
                logger.info(f"使用本地缓存的 {tool} 版本信息")
                self._memory_cache[cache_key] = cached
                return cached.get("versions", [])
        
        mirror_list = self.get_mirror_list(tool)
        if not mirror_list:
            logger.warning(f"未配置 {tool} 的镜像 URL")
            if use_cache and cache_key in cache:
                logger.info(f"网络错误，使用缓存的 {tool} 版本信息")
                self._memory_cache[cache_key] = cache[cache_key]
                return cache[cache_key].get("versions", [])
            return []
        
        sorted_mirrors = self.mirror_status.get_sorted_mirrors(mirror_list)
        errors = []
        
        for mirror_url in sorted_mirrors:
            try:
                logger.info(f"尝试从镜像源获取 {tool} 版本: {mirror_url}")
                versions = self._fetch_versions_from_mirror(tool, mirror_url)
                
                if not versions:
                    error_msg = f"镜像源返回空版本列表"
                    logger.warning(f"从镜像源 {mirror_url} 获取 {tool} 版本失败: {error_msg}")
                    self.mirror_status.record_failure(mirror_url, error_msg)
                    errors.append(f"{mirror_url}: {error_msg}")
                    continue
                
                validated_versions = self._validate_version_list(versions, tool, mirror_url)
                if not validated_versions:
                    error_msg = f"版本列表验证失败，无有效版本"
                    logger.warning(f"从镜像源 {mirror_url} 获取 {tool} 版本失败: {error_msg}")
                    self.mirror_status.record_failure(mirror_url, error_msg)
                    errors.append(f"{mirror_url}: {error_msg}")
                    continue
                
                self.mirror_status.record_success(mirror_url)
                self._update_cache(tool, validated_versions)
                logger.info(f"成功从镜像源 {mirror_url} 获取 {len(validated_versions)} 个 {tool} 版本")
                return validated_versions
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"从镜像源 {mirror_url} 获取 {tool} 版本失败: {error_msg}")
                self.mirror_status.record_failure(mirror_url, error_msg)
                errors.append(f"{mirror_url}: {error_msg}")
                continue
        
        failure_summary = self.mirror_status.get_failure_summary()
        logger.error(f"所有镜像源获取 {tool} 版本失败。失败详情: {failure_summary}")
        
        if use_cache and cache_key in cache:
            logger.info(f"网络错误，使用缓存的 {tool} 版本信息")
            self._memory_cache[cache_key] = cache[cache_key]
            return cache[cache_key].get("versions", [])
        return []
    
    def _validate_version_list(self, versions: List[Dict[str, Any]], tool: str, mirror_url: str) -> List[Dict[str, Any]]:
        """
        验证版本列表的有效性。
        
        参数:
            versions: 版本列表
            tool: 工具名称
            mirror_url: 镜像源 URL
            
        返回:
            验证后的有效版本列表
        """
        validated = []
        for v in versions:
            if not isinstance(v, dict):
                continue
            if "version" not in v:
                continue
            if "download_url" not in v or not v["download_url"]:
                continue
            validated.append(v)
        
        if len(validated) != len(versions):
            logger.warning(
                f"镜像源 {mirror_url} 返回的 {tool} 版本列表中 "
                f"有 {len(versions) - len(validated)} 个无效项被过滤"
            )
        
        return validated
    
    def _fetch_versions_from_mirror(self, tool: str, mirror_url: str) -> List[Dict[str, Any]]:
        """
        从镜像源获取版本列表。
        
        优先使用通用配置获取版本，无配置时回退到专用方法。
        
        参数:
            tool: 工具名称
            mirror_url: 镜像源 URL
            
        返回:
            版本信息列表
        """
        fetch_config = self._get_version_fetch_config(tool)
        if fetch_config:
            logger.info(f"使用通用配置获取 {tool} 版本")
            return self._fetch_generic_versions(tool, mirror_url, fetch_config)
        
        if tool == "python":
            return self._fetch_python_versions(mirror_url)
        elif tool == "node":
            return self._fetch_node_versions(mirror_url)
        elif tool == "java":
            return self._fetch_java_versions(mirror_url)
        elif tool == "maven":
            return self._fetch_maven_versions(mirror_url)
        elif tool == "gradle":
            return self._fetch_gradle_versions(mirror_url)
        return []
    
    def _fetch_generic_versions(
        self, 
        tool: str, 
        mirror_url: str, 
        config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        基于配置动态解析版本列表。
        
        支持的配置项：
        - version_pattern: 正则表达式匹配版本号
        - download_url_template: URL 模板，支持变量替换
        - arch_map: 架构映射
        - index_file: 索引文件（如 Node.js 的 index.json）
        - version_field: 从 JSON 中提取版本的字段名
        - lts_field: 从 JSON 中提取 LTS 标记的字段名
        
        参数:
            tool: 工具名称
            mirror_url: 镜像源 URL
            config: 版本获取配置
            
        返回:
            版本信息列表
        """
        versions = []
        try:
            index_file = config.get("index_file")
            version_pattern = config.get("version_pattern")
            download_url_template = config.get("download_url_template", "")
            arch_map = config.get("arch_map", {})
            version_field = config.get("version_field", "version")
            lts_field = config.get("lts_field")
            
            arch = self._get_current_arch(arch_map)
            
            if index_file:
                versions = self._fetch_versions_from_index(
                    mirror_url, index_file, download_url_template, 
                    arch, arch_map, version_field, lts_field
                )
            elif version_pattern:
                versions = self._fetch_versions_from_html(
                    mirror_url, version_pattern, download_url_template,
                    arch, arch_map
                )
            else:
                logger.warning(f"{tool} 的版本获取配置缺少 version_pattern 或 index_file")
                
        except Exception as e:
            logger.error(f"使用通用配置获取 {tool} 版本失败: {e}")
        
        return versions
    
    def _get_current_arch(self, arch_map: Dict[str, str]) -> str:
        """
        获取当前系统架构对应的名称。
        
        参数:
            arch_map: 架构映射字典
            
        返回:
            架构名称
        """
        is_64bit = platform.machine().endswith('64')
        if is_64bit:
            return arch_map.get("x64", "x64")
        return arch_map.get("x86", "x86")
    
    def _fetch_versions_from_index(
        self,
        mirror_url: str,
        index_file: str,
        download_url_template: str,
        arch: str,
        arch_map: Dict[str, str],
        version_field: str,
        lts_field: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        从索引文件（如 JSON）获取版本列表。
        
        参数:
            mirror_url: 镜像源 URL
            index_file: 索引文件名
            download_url_template: 下载 URL 模板
            arch: 当前架构名称
            arch_map: 架构映射
            version_field: 版本字段名
            lts_field: LTS 字段名
            
        返回:
            版本信息列表
        """
        versions = []
        try:
            self.rate_limiter.acquire()
            index_url = mirror_url.rstrip("/") + "/" + index_file
            logger.debug(f"获取索引文件: {index_url}")
            
            response = requests.get(index_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("versions", [data])
            else:
                logger.warning(f"索引文件格式不支持: {type(data)}")
                return versions
            
            for item in items:
                if not isinstance(item, dict):
                    continue
                    
                version = item.get(version_field, "")
                if not version:
                    continue
                
                version = version.lstrip("v")
                
                version_info = self._build_version_info(
                    version, mirror_url, download_url_template, arch, arch_map, item
                )
                
                if lts_field and lts_field in item:
                    version_info["lts"] = bool(item[lts_field])
                
                if "date" in item:
                    version_info["release_date"] = item["date"]
                    
                versions.append(version_info)
                
        except Exception as e:
            logger.error(f"从索引文件获取版本失败: {e}")
            
        return versions
    
    def _fetch_versions_from_html(
        self,
        mirror_url: str,
        version_pattern: str,
        download_url_template: str,
        arch: str,
        arch_map: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        从 HTML 页面解析版本列表。
        
        参数:
            mirror_url: 镜像源 URL
            version_pattern: 版本号正则表达式
            download_url_template: 下载 URL 模板
            arch: 当前架构名称
            arch_map: 架构映射
            
        返回:
            版本信息列表
        """
        versions = []
        seen = set()
        
        try:
            self.rate_limiter.acquire()
            logger.debug(f"获取 HTML 页面: {mirror_url}")
            
            response = requests.get(mirror_url, timeout=10)
            response.raise_for_status()
            content = response.text
            
            matches = re.findall(version_pattern, content)
            
            for version in matches:
                if version in seen:
                    continue
                seen.add(version)
                
                version_info = self._build_version_info(
                    version, mirror_url, download_url_template, arch, arch_map, None
                )
                versions.append(version_info)
                
        except Exception as e:
            logger.error(f"从 HTML 页面获取版本失败: {e}")
            
        return versions
    
    def _build_version_info(
        self,
        version: str,
        mirror_url: str,
        download_url_template: str,
        arch: str,
        arch_map: Dict[str, str],
        extra_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        构建版本信息字典。
        
        参数:
            version: 版本号
            mirror_url: 镜像源 URL
            download_url_template: 下载 URL 模板
            arch: 当前架构名称
            arch_map: 架构映射
            extra_data: 额外数据（来自 JSON 索引）
            
        返回:
            版本信息字典
        """
        version_parts = self._parse_version_parts(version)
        
        template_vars = {
            "mirror": mirror_url,
            "version": version,
            "arch": arch,
            "major": version_parts.get("major", ""),
            "minor": version_parts.get("minor", ""),
            "patch": version_parts.get("patch", "")
        }
        
        download_url = self._render_url_template(download_url_template, template_vars)
        
        return {
            "version": version,
            "release_date": None,
            "download_url": download_url
        }
    
    def _parse_version_parts(self, version: str) -> Dict[str, str]:
        """
        解析版本号的各个部分。
        
        参数:
            version: 版本字符串
            
        返回:
            包含 major, minor, patch 的字典
        """
        parts = version.split(".")
        result = {
            "major": parts[0] if len(parts) > 0 else "",
            "minor": parts[1] if len(parts) > 1 else "",
            "patch": parts[2] if len(parts) > 2 else ""
        }
        return result
    
    def _render_url_template(self, template: str, variables: Dict[str, str]) -> str:
        """
        渲染 URL 模板，替换变量占位符。
        
        参数:
            template: URL 模板字符串
            variables: 变量字典
            
        返回:
            渲染后的 URL
        """
        result = template
        for key, value in variables.items():
            placeholder = "{" + key + "}"
            result = result.replace(placeholder, value)
        return result
    
    def _fetch_python_versions(self, mirror_url: str) -> List[Dict[str, Any]]:
        """
        从镜像源获取 Python 版本列表。
        
        参数:
            mirror_url: Python 镜像源 URL
            
        返回:
            Python 版本信息列表
        """
        versions = []
        try:
            self.rate_limiter.acquire()
            response = requests.get(mirror_url, timeout=10)
            response.raise_for_status()
            content = response.text
            pattern = r'href="(\d+\.\d+\.\d+)/"'
            matches = re.findall(pattern, content)
            seen = set()
            for version in matches:
                if version not in seen:
                    seen.add(version)
                    arch = "amd64" if platform.machine().endswith('64') else "win32"
                    download_url = f"{mirror_url}{version}/python-{version}-embed-{arch}.zip"
                    versions.append({
                        "version": version,
                        "release_date": None,
                        "download_url": download_url
                    })
        except Exception as e:
            logger.error(f"获取 Python 版本失败: {e}")
        return versions
    
    def _fetch_node_versions(self, mirror_url: str) -> List[Dict[str, Any]]:
        """
        从镜像源获取 Node.js 版本列表。
        
        参数:
            mirror_url: Node.js 镜像源 URL
            
        返回:
            Node.js 版本信息列表
        """
        versions = []
        try:
            self.rate_limiter.acquire()
            index_url = mirror_url.rstrip("/") + "/index.json"
            response = requests.get(index_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            for item in data:
                version = item.get("version", "").lstrip("v")
                arch = "x64" if platform.machine().endswith('64') else "x86"
                download_url = f"{mirror_url}v{version}/node-v{version}-win-{arch}.zip"
                lts = item.get("lts", False)
                versions.append({
                    "version": version,
                    "release_date": item.get("date"),
                    "download_url": download_url,
                    "lts": bool(lts)
                })
        except Exception as e:
            logger.error(f"获取 Node.js 版本失败: {e}")
        return versions
    
    def _fetch_java_versions(self, mirror_url: str) -> List[Dict[str, Any]]:
        """
        从镜像源获取 Java 版本列表。
        
        参数:
            mirror_url: Java 镜像源 URL
            
        返回:
            Java 版本信息列表
        """
        versions = []
        try:
            self.rate_limiter.acquire()
            response = requests.get(mirror_url, timeout=10)
            response.raise_for_status()
            content = response.text
            pattern = r'href="(\d+(?:\.\d+)*)/"'
            matches = re.findall(pattern, content)
            seen = set()
            for version in matches:
                if version not in seen:
                    seen.add(version)
                    download_url = f"{mirror_url}{version}/openjdk-{version}_windows-x64_bin.zip"
                    versions.append({
                        "version": version,
                        "release_date": None,
                        "download_url": download_url
                    })
        except Exception as e:
            logger.error(f"获取 Java 版本失败: {e}")
        return versions
    
    def _fetch_maven_versions(self, mirror_url: str) -> List[Dict[str, Any]]:
        """
        从镜像源获取 Maven 版本列表。
        
        参数:
            mirror_url: Maven 镜像源 URL
            
        返回:
            Maven 版本信息列表
        """
        versions = []
        try:
            self.rate_limiter.acquire()
            response = requests.get(mirror_url, timeout=10)
            response.raise_for_status()
            content = response.text
            pattern = r'href="apache-maven-(\d+\.\d+\.\d+)/"'
            matches = re.findall(pattern, content)
            for version in matches:
                download_url = f"{mirror_url}apache-maven-{version}/apache-maven-{version}-bin.zip"
                versions.append({
                    "version": version,
                    "release_date": None,
                    "download_url": download_url
                })
        except Exception as e:
            logger.error(f"获取 Maven 版本失败: {e}")
        return versions
    
    def _fetch_gradle_versions(self, mirror_url: str) -> List[Dict[str, Any]]:
        """
        从镜像源获取 Gradle 版本列表。
        
        参数:
            mirror_url: Gradle 镜像源 URL
            
        返回:
            Gradle 版本信息列表
        """
        versions = []
        try:
            self.rate_limiter.acquire()
            response = requests.get(mirror_url, timeout=10)
            response.raise_for_status()
            content = response.text
            pattern = r'href="gradle-(\d+\.\d+(?:\.\d+)?)-bin\.zip"'
            matches = re.findall(pattern, content)
            seen = set()
            for version in matches:
                if version not in seen:
                    seen.add(version)
                    download_url = f"{mirror_url}gradle-{version}-bin.zip"
                    versions.append({
                        "version": version,
                        "release_date": None,
                        "download_url": download_url
                    })
        except Exception as e:
            logger.error(f"获取 Gradle 版本失败: {e}")
        return versions
    
    def _update_cache(self, tool: str, versions: List[Dict[str, Any]]) -> None:
        """
        更新版本缓存。
        
        参数:
            tool: 工具名称
            versions: 版本信息列表
        """
        cache_key = f"{tool}_versions"
        cache_data = {
            "last_update": datetime.now().isoformat(),
            "versions": versions
        }
        self._memory_cache[cache_key] = cache_data
        self.config_manager.set_cache(cache_key, cache_data)
        self.config_manager.save_cache()
