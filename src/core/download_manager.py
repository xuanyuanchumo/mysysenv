"""
下载管理模块。

提供工具版本的下载、解压和安装功能。
"""

import os
import re
import zipfile
import tempfile
import shutil
import platform
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
import requests

from src.utils.logger import get_logger
from src.core.config_manager import ConfigManager
from src.utils.retry import RetryHandler
from src.utils.speed_limiter import SpeedLimiter
from src.utils.download_history import DownloadHistory
from src.utils.rate_limiter import RateLimiter

logger = get_logger()


class DownloadManagerError(Exception):
    """下载管理错误异常。"""
    pass


class DownloadError(DownloadManagerError):
    """下载错误异常。"""
    pass


class ExtractionError(DownloadManagerError):
    """解压错误异常。"""
    pass


class InstallationError(DownloadManagerError):
    """安装错误异常。"""
    pass


class DownloadManager:
    """
    下载管理器类。
    
    负责工具版本的下载、解压和安装。
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        初始化下载管理器。
        
        参数:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        rate_limit = config_manager.get_request_rate_limit()
        self.rate_limiter = RateLimiter(requests_per_second=rate_limit)
        retry_count = config_manager.get_download_retry_count()
        self.retry_handler = RetryHandler(max_retries=retry_count)
        speed_limit = config_manager.get_download_speed_limit()
        self.speed_limiter = SpeedLimiter(speed_limit_bytes=speed_limit)
        self.download_history = DownloadHistory(self.config_manager.CONFIG_DIR)
    
    def _build_download_url(self, tool: str, version: str, mirror_url: str) -> str:
        """
        根据工具类型、版本号和镜像源构建下载 URL。
        
        参数:
            tool: 工具名称
            version: 版本号
            mirror_url: 镜像源 URL
            
        返回:
            下载 URL
        """
        arch = None
        if tool == "python":
            arch = "amd64" if platform.machine().endswith('64') else "win32"
            return f"{mirror_url}{version}/python-{version}-embed-{arch}.zip"
        elif tool == "node":
            arch = "x64" if platform.machine().endswith('64') else "x86"
            return f"{mirror_url}v{version}/node-v{version}-win-{arch}.zip"
        elif tool == "java":
            return f"{mirror_url}{version}/openjdk-{version}_windows-x64_bin.zip"
        elif tool == "maven":
            return f"{mirror_url}apache-maven-{version}/apache-maven-{version}-bin.zip"
        elif tool == "gradle":
            return f"{mirror_url}gradle-{version}-bin.zip"
        return ""
    
    def _get_target_dir(self, tool: str, version: str, root_path: str) -> str:
        """
        获取工具安装目标目录。
        
        参数:
            tool: 工具名称
            version: 版本号
            root_path: 根目录路径
            
        返回:
            目标目录路径
        """
        naming_patterns = {
            "python": f"python{version.replace('.', '')}",
            "java": f"jdk{version}",
            "node": f"node-v{version}",
            "maven": f"apache-maven-{version}",
            "gradle": f"gradle-{version}",
        }
        folder_name = naming_patterns.get(tool, f"{tool}-{version}")
        return os.path.join(root_path, folder_name)
    
    def _extract_archive(self, archive_path: str, target_dir: str, tool: str, version: str) -> None:
        """
        解压安装包，防止路径遍历漏洞。
        
        参数:
            archive_path: 压缩包路径
            target_dir: 目标目录
            tool: 工具名称
            version: 版本号
        """
        import os
        from pathlib import Path
        
        def _safe_join(base, path):
            base = os.path.abspath(base)
            joined = os.path.abspath(os.path.join(base, path))
            if not joined.startswith(base + os.sep):
                raise ExtractionError(f"非法文件路径: {path}")
            return joined
        
        with zipfile.ZipFile(archive_path, "r") as zf:
            names = zf.namelist()
            
            for name in names:
                if ".." in name or name.startswith("/") or name.startswith("\\"):
                    raise ExtractionError(f"压缩包包含非法路径: {name}")
            
            if names and names[0].endswith("/"):
                prefix = names[0]
                temp_extract = tempfile.mkdtemp()
                try:
                    zf.extractall(temp_extract)
                    extracted_dir = _safe_join(temp_extract, prefix.rstrip("/"))
                    if os.path.exists(target_dir):
                        shutil.rmtree(target_dir)
                    shutil.move(extracted_dir, target_dir)
                finally:
                    shutil.rmtree(temp_extract, ignore_errors=True)
            else:
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir)
                os.makedirs(target_dir, exist_ok=True)
                
                for member in zf.infolist():
                    member_path = _safe_join(target_dir, member.filename)
                    if member.is_dir():
                        os.makedirs(member_path, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(member_path), exist_ok=True)
                        with open(member_path, "wb") as f:
                            f.write(zf.read(member.filename))
    
    def _get_temp_download_path(self, tool: str, version: str) -> str:
        """
        获取临时下载文件路径，用于断点续传。
        
        参数:
            tool: 工具名称
            version: 版本号
            
        返回:
            临时文件路径
        """
        config_dir = self.config_manager.CONFIG_DIR
        temp_dir = config_dir / "temp_downloads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return str(temp_dir / f"{tool}_{version}.zip.part")
    
    def _check_and_resume_download(
        self,
        download_url: str,
        temp_path: str
    ) -> tuple[int, int]:
        """
        检查是否可以断点续传并返回已下载大小和总大小。
        
        参数:
            download_url: 下载 URL
            temp_path: 临时文件路径
            
        返回:
            (已下载大小, 总大小) 元组
        """
        downloaded = 0
        total_size = 0
        
        if os.path.exists(temp_path):
            downloaded = os.path.getsize(temp_path)
            logger.info(f"发现部分下载文件，已下载 {downloaded} 字节")
        
        self.rate_limiter.acquire()
        headers = {}
        if downloaded > 0:
            headers["Range"] = f"bytes={downloaded}-"
        
        response = requests.head(download_url, headers=headers, timeout=10, allow_redirects=True)
        
        if downloaded > 0 and response.status_code == 206:
            content_range = response.headers.get("Content-Range", "")
            if content_range:
                match = re.search(r"/(\d+)$", content_range)
                if match:
                    total_size = int(match.group(1))
            logger.info(f"服务器支持断点续传，继续下载")
        elif downloaded > 0 and response.status_code == 200:
            logger.info("服务器不支持断点续传，从头开始下载")
            downloaded = 0
            total_size = int(response.headers.get("content-length", 0))
        else:
            total_size = int(response.headers.get("content-length", 0))
        
        return downloaded, total_size
    
    def _extract_mirror_from_url(self, download_url: str, mirror_list: List[str]) -> Optional[str]:
        """
        从下载 URL 中提取对应的镜像源 URL。
        
        参数:
            download_url: 下载 URL
            mirror_list: 镜像源列表
            
        返回:
            匹配的镜像源 URL，未找到返回 None
        """
        for mirror_url in mirror_list:
            if download_url.startswith(mirror_url):
                return mirror_url
        return None
    
    def _update_installed_versions(self, tool: str, version: str, path: str) -> None:
        """
        更新配置中的已安装版本信息。
        
        参数:
            tool: 工具名称
            version: 版本号
            path: 安装路径
        """
        config = self.config_manager.get_config()
        if "tools" not in config:
            config["tools"] = {}
        if tool not in config["tools"]:
            config["tools"][tool] = {
                "installed_versions": [],
                "current_version": None
            }
        installed = config["tools"][tool]["installed_versions"]
        existing = next((v for v in installed if v["version"] == version), None)
        if existing:
            existing["path"] = path
            existing["install_date"] = datetime.now().isoformat()
        else:
            installed.append({
                "version": version,
                "path": path,
                "install_date": datetime.now().isoformat(),
                "locked": False,
                "is_system": False
            })
        self.config_manager.save_config(config)
    
    def download_version(
        self,
        tool: str,
        version: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        status_callback: Optional[Callable[[str], None]] = None,
        version_info: Optional[Dict[str, Any]] = None,
        mirror_status=None,
        mirror_list=None
    ) -> bool:
        """
        下载并安装指定版本，支持断点续传和重试。
        
        参数:
            tool: 工具名称
            version: 版本号
            progress_callback: 下载进度回调函数
            status_callback: 状态消息回调函数
            version_info: 版本信息字典（可选，包含 download_url）
            mirror_status: 镜像源状态跟踪实例
            mirror_list: 镜像源列表
            
        返回:
            成功返回 True，失败返回 False
        """
        if mirror_list is None:
            mirror_list = self._get_mirror_list(tool)
        
        if not mirror_list:
            logger.error(f"未配置 {tool} 的镜像源")
            return False
        
        root_path = self.config_manager.get_normalized_tool_root(tool)
        if not root_path:
            logger.error(f"未配置 {tool} 的根目录")
            return False
        os.makedirs(root_path, exist_ok=True)
        target_dir = self._get_target_dir(tool, version, root_path)
        temp_path = self._get_temp_download_path(tool, version)
        
        if mirror_status:
            sorted_mirrors = mirror_status.get_sorted_mirrors(mirror_list)
        else:
            sorted_mirrors = mirror_list
        
        errors = []
        
        if version_info and version_info.get("download_url"):
            download_url = version_info["download_url"]
            mirror_url = self._extract_mirror_from_url(download_url, mirror_list)
            mirrors_to_try = [mirror_url] if mirror_url else sorted_mirrors
        else:
            mirrors_to_try = sorted_mirrors
        
        for mirror_url in mirrors_to_try:
            try:
                if version_info and version_info.get("download_url"):
                    download_url = version_info["download_url"]
                else:
                    download_url = self._build_download_url(tool, version, mirror_url)
                
                if not download_url:
                    error_msg = f"无法为 {tool} {version} 构建下载 URL"
                    logger.warning(f"从镜像源 {mirror_url} 下载失败: {error_msg}")
                    if mirror_status:
                        mirror_status.record_failure(mirror_url, error_msg)
                    errors.append(f"{mirror_url}: {error_msg}")
                    continue
                
                logger.info(f"尝试从镜像源下载 {tool} {version}: {mirror_url}")
                logger.info(f"下载 URL: {download_url}")
                
                downloaded, total_size = self._check_and_resume_download(download_url, temp_path)
                
                mode = "ab" if downloaded > 0 else "wb"
                headers = {}
                if downloaded > 0:
                    headers["Range"] = f"bytes={downloaded}-"
                
                logger.info(f"正在从 {download_url} 下载 {tool} {version}")
                
                def _do_download():
                    self.rate_limiter.acquire()
                    return requests.get(download_url, headers=headers, stream=True, timeout=300)
                
                response = self.retry_handler.execute(_do_download)
                response.raise_for_status()
                
                if total_size == 0:
                    total_size = int(response.headers.get("content-length", 0)) + downloaded
                
                with open(temp_path, mode) as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            self.speed_limiter.write_with_limit(f, chunk)
                            downloaded += len(chunk)
                            if progress_callback and total_size > 0:
                                progress_callback(downloaded, total_size)
                
                logger.info(f"下载完成，正在解压到 {target_dir}")
                if status_callback:
                    status_callback("正在解压...")
                self._extract_archive(temp_path, target_dir, tool, version)
                
                try:
                    os.remove(temp_path)
                except:
                    pass
                
                self._update_installed_versions(tool, version, target_dir)
                if mirror_status:
                    mirror_status.record_success(mirror_url)
                logger.info(f"成功安装 {tool} {version}")
                
                self.download_history.add_record(
                    tool=tool,
                    version=version,
                    status="success",
                    download_url=download_url
                )
                
                return True
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"从镜像源 {mirror_url} 下载 {tool} {version} 失败: {error_msg}")
                if mirror_status:
                    mirror_status.record_failure(mirror_url, error_msg)
                errors.append(f"{mirror_url}: {error_msg}")
                continue
        
        failure_summary = mirror_status.get_failure_summary() if mirror_status else "; ".join(errors)
        logger.error(f"所有镜像源下载 {tool} {version} 失败。失败详情: {failure_summary}")
        
        self.download_history.add_record(
            tool=tool,
            version=version,
            status="failed",
            error_message=f"所有镜像源下载失败: {failure_summary}"
        )
        
        return False
    
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
