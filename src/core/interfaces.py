"""
核心模块抽象接口定义。

定义 ConfigManager、EnvManager、VersionManager 等核心模块的抽象接口。
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Callable


class IConfigManager(ABC):
    """配置管理器抽象接口。"""

    @abstractmethod
    def get_config(self) -> dict[str, Any]:
        """获取配置字典。"""
        pass

    @abstractmethod
    def save_config(self, config: dict[str, Any] | None = None) -> None:
        """保存配置到文件。"""
        pass

    @abstractmethod
    def get_settings(self) -> dict[str, Any]:
        """获取 settings 配置部分。"""
        pass

    @abstractmethod
    def get_tool_templates(self) -> dict[str, Any]:
        """获取所有工具配置模板。"""
        pass

    @abstractmethod
    def get_tool_template(self, tool: str) -> dict[str, Any]:
        """获取指定工具的配置模板。"""
        pass

    @abstractmethod
    def get_tool_root(self, tool: str) -> str:
        """获取指定工具的根目录路径。"""
        pass

    @abstractmethod
    def get_normalized_tool_root(self, tool: str) -> str:
        """获取指定工具的规范化根目录路径。"""
        pass

    @abstractmethod
    def get_version_cmd(self, tool: str) -> str:
        """获取指定工具的版本检测命令。"""
        pass

    @abstractmethod
    def get_env_rule(self, tool: str) -> dict[str, Any]:
        """获取指定工具的环境变量规则。"""
        pass

    @abstractmethod
    def get_mirror_list(self, tool: str) -> list[str]:
        """获取指定工具的镜像源列表。"""
        pass

    @abstractmethod
    def get_version_fetch_config(self, tool: str) -> dict[str, Any]:
        """获取指定工具的版本获取配置。"""
        pass

    @abstractmethod
    def get_cache_expire_time(self) -> int:
        """获取缓存过期时间配置。"""
        pass

    @abstractmethod
    def get_request_rate_limit(self) -> int:
        """获取请求频率限制配置。"""
        pass

    @abstractmethod
    def get_download_retry_count(self) -> int:
        """获取下载重试次数配置。"""
        pass

    @abstractmethod
    def get_download_speed_limit(self) -> int:
        """获取下载速度限制配置。"""
        pass

    @abstractmethod
    def get_tools(self) -> dict[str, Any]:
        """获取工具配置部分。"""
        pass

    @abstractmethod
    def get_cache(self) -> dict[str, Any]:
        """获取缓存配置部分。"""
        pass

    @abstractmethod
    def set_cache(self, key: str, value: Any) -> None:
        """设置缓存值。"""
        pass

    @abstractmethod
    def save_cache(self, cache: dict[str, Any] | None = None) -> None:
        """保存缓存到文件。"""
        pass

    @abstractmethod
    def reset_to_default(self) -> dict[str, Any]:
        """重置配置为默认配置。"""
        pass

    @abstractmethod
    def add_tool_config(self, tool_name: str) -> bool:
        """添加新工具配置。"""
        pass

    @abstractmethod
    def delete_tool_config(self, tool_name: str) -> bool:
        """删除工具配置。"""
        pass

    @abstractmethod
    def get_tool_specific_config(self, tool_name: str) -> dict[str, Any]:
        """获取工具特定配置。"""
        pass

    @abstractmethod
    def save_tool_specific_config(self, tool_name: str, tool_config: dict[str, Any]) -> bool:
        """保存工具特定配置。"""
        pass

    @abstractmethod
    def set_tool_root_config(self, tool: str, path: str) -> bool:
        """设置工具根目录配置。"""
        pass


class IEnvManager(ABC):
    """环境变量管理器抽象接口。"""

    @abstractmethod
    def get_env_var(self, name: str) -> Optional[str]:
        """获取环境变量值。"""
        pass

    @abstractmethod
    def set_env_var(self, name: str, value: str) -> bool:
        """设置环境变量值。"""
        pass

    @abstractmethod
    def delete_env_var(self, name: str) -> bool:
        """删除环境变量。"""
        pass

    @abstractmethod
    def get_path_entries(self) -> List[str]:
        """获取 PATH 环境变量的所有条目。"""
        pass

    @abstractmethod
    def add_to_path(self, entry: str) -> bool:
        """向 PATH 环境变量添加新条目。"""
        pass

    @abstractmethod
    def remove_from_path(self, entry: str) -> bool:
        """从 PATH 环境变量移除条目。"""
        pass

    @abstractmethod
    def path_contains(self, entry: str) -> bool:
        """检查 PATH 是否包含指定条目。"""
        pass

    @abstractmethod
    def broadcast_change(self) -> None:
        """广播环境变量更改消息。"""
        pass

    @abstractmethod
    def setup_tool_env(self, tool: str, home_var: str, path: str, path_entries: List[str]) -> bool:
        """设置工具的环境变量。"""
        pass

    @abstractmethod
    def get_all_env_vars(self) -> dict:
        """获取所有系统环境变量。"""
        pass


class IVersionManager(ABC):
    """版本管理器抽象接口。"""

    @abstractmethod
    def scan_local_versions(self, tool: str) -> List[Dict[str, Any]]:
        """扫描本地已安装的工具版本。"""
        pass

    @abstractmethod
    def get_remote_versions(self, tool: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        """获取远程可用的工具版本。"""
        pass

    @abstractmethod
    def download_version(
        self,
        tool: str,
        version: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        version_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """下载并安装指定版本。"""
        pass

    @abstractmethod
    def switch_version(self, tool: str, version: str) -> bool:
        """切换到指定版本。"""
        pass

    @abstractmethod
    def delete_version(self, tool: str, version: str) -> bool:
        """删除指定版本。"""
        pass

    @abstractmethod
    def get_current_version(self, tool: str) -> Optional[str]:
        """获取当前使用的版本。"""
        pass

    @abstractmethod
    def lock_version(self, tool: str, version: str, locked: bool) -> bool:
        """锁定或解锁指定版本。"""
        pass

    @abstractmethod
    def sort_versions_desc(self, versions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按版本号降序排列版本列表。"""
        pass

    @abstractmethod
    def group_versions_by_major(self, versions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按主版本号分组版本列表。"""
        pass


class ILocalManager(ABC):
    """本地版本管理器抽象接口。"""

    @abstractmethod
    def get_tool_version_by_cmd(self, tool: str, tool_path: str) -> Optional[str]:
        """通过执行版本命令获取工具版本。"""
        pass

    @abstractmethod
    def scan_local_versions(self, tool: str) -> List[Dict[str, Any]]:
        """扫描本地已安装的工具版本。"""
        pass

    @abstractmethod
    def check_and_update_system_version(self, tool: str) -> Optional[Dict[str, str]]:
        """检查并更新工具的系统版本标记。"""
        pass

    @abstractmethod
    def get_system_version_from_env(self, tool: str) -> Optional[str]:
        """从系统环境变量获取当前工具版本。"""
        pass


class IRemoteFetcher(ABC):
    """远程版本获取器抽象接口。"""

    @abstractmethod
    def get_mirror_list(self, tool: str) -> List[str]:
        """获取工具的镜像源列表。"""
        pass

    @abstractmethod
    def get_remote_versions(self, tool: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        """获取远程可用的工具版本。"""
        pass
