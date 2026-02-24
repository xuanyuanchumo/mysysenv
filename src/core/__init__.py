"""
Mysysenv 核心模块。

提供配置管理、环境变量管理和版本管理功能。
"""

from .interfaces import IConfigManager, IEnvManager, IVersionManager, ILocalManager, IRemoteFetcher
from .config_manager import ConfigManager, ConfigValidationError, ConfigLoadError, ConfigSaveError
from .env_manager import EnvManager, EnvManagerError, RegistryAccessError
from .version_manager import VersionManager, VersionManagerError, VersionNotFoundError, VersionLockedError, SwitchVersionError, DeleteVersionError
from .remote_fetcher import RemoteFetcher, RemoteFetcherError, NetworkError, MirrorError, MirrorStatus
from .local_manager import LocalManager, LocalManagerError, ToolNotFoundError, VersionScanError
from .download_manager import DownloadManager, DownloadManagerError, DownloadError, ExtractionError, InstallationError
from . import version_utils

__all__ = [
    "IConfigManager", "IEnvManager", "IVersionManager", "ILocalManager", "IRemoteFetcher",
    "ConfigManager", "ConfigValidationError", "ConfigLoadError", "ConfigSaveError",
    "EnvManager", "EnvManagerError", "RegistryAccessError",
    "VersionManager", "VersionManagerError", "VersionNotFoundError", "VersionLockedError", "SwitchVersionError", "DeleteVersionError",
    "RemoteFetcher", "RemoteFetcherError", "NetworkError", "MirrorError", "MirrorStatus",
    "LocalManager", "LocalManagerError", "ToolNotFoundError", "VersionScanError",
    "DownloadManager", "DownloadManagerError", "DownloadError", "ExtractionError", "InstallationError",
    "version_utils",
]
