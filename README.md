# Mysysenv

**Mysysenv** 是一个 Windows 平台下的多工具环境变量和版本管理器，类似于 nvm（Node Version Manager），但支持 Python、Java、Node.js、Maven、Gradle 等多种开发工具。

## 功能特性

- **双模式界面**：支持图形界面（GUI）和命令行界面（CLI）
- **多工具支持**：Python、Java、Node.js、Maven、Gradle 等
- **自定义工具**：可添加自定义工具配置
- **版本管理**：快速安装、切换、卸载工具版本
- **环境变量自动化**：自动配置 HOME 变量和 PATH
- **多镜像源**：支持配置镜像源，提升下载速度
- **配置持久化**：JSON 格式配置，配置目录跟随程序

## 技术栈

- **Python 3.14+**
- **PySide6 6.8+** - Qt for Python
- **QML** - Qt 声明式语言
- **requests** - HTTP 库

## 快速开始

### 环境要求

- Windows 操作系统
- Python 3.14 或更高版本
- 管理员权限（用于修改系统环境变量）

### 安装依赖

```bash
pip install -e .
```

或

```bash
pip install PySide6 requests
```

### 运行

```bash
# GUI 模式
python src/main.py

# CLI 模式
python src/main.py --help
```

### CLI 命令示例

```bash
# 列出已安装的工具
mse list

# 列出 Python 已安装版本
mse list python

# 列出 Python 可下载版本
mse list python --remote

# 切换 Python 版本
mse use python 3.11.0

# 安装 Python 版本
mse install python 3.11.0

# 卸载 Python 版本
mse uninstall python 3.10.0

# 设置工具根目录
mse root python D:\python
```

## 配置说明

配置文件位于程序所在目录下的 `config` 文件夹：

```
项目目录/
└── config/
    ├── config.json          # 主配置文件
    ├── cache.json           # 版本缓存
    └── default_config.json  # 默认配置模板
```

### 配置结构

```json
{
  "settings": {
    "tool_templates": {
      "python": {
        "tool_root": "D:\\python",
        "mirror_list": [
          "https://www.python.org/ftp/python/",
          "https://mirrors.huaweicloud.com/python/"
        ],
        "version_cmd": "python --version",
        "env_rule": {
          "home_var": "PYTHON_HOME",
          "path_entries": ["", "Scripts"]
        }
      }
    }
  },
  "tools": {
    "python": {
      "installed_versions": [],
      "current_version": "3.11.0"
    }
  }
}
```

## 项目结构

```
mysysenv/
├── src/
│   ├── core/           # 核心业务逻辑
│   │   ├── config_manager.py    # 配置管理
│   │   ├── env_manager.py       # 环境变量管理
│   │   ├── version_manager.py   # 版本管理
│   │   ├── download_manager.py  # 下载管理
│   │   ├── local_manager.py     # 本地版本扫描
│   │   └── remote_fetcher.py   # 远程版本获取
│   ├── ui/             # 图形界面
│   │   ├── qml/        # QML 界面文件
│   │   └── viewmodels/ # 视图模型
│   ├── utils/          # 工具类
│   ├── cli.py          # 命令行接口
│   └── main.py         # 程序入口
├── docs/               # 项目文档
├── pyproject.toml      # 项目配置
└── README.md           # 本文件
```

## 开发指南

### 开发环境搭建

1. 克隆项目
2. 创建虚拟环境：`python -m venv .venv`
3. 激活虚拟环境：`.venv\Scripts\activate`
4. 安装依赖：`pip install -e .[dev]`

### 代码规范

- 遵循 PEP 8
- 使用 Black 格式化：`black src/`
- 使用 Ruff 检查：`ruff check src/`
- 使用 MyPy 类型检查：`mypy src/`

### 打包 EXE

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name mysysenv src/main.py
```

打包完成后，EXE 文件位于 `dist/mysysenv.exe`。

## 文档

详细文档请参阅 [docs](./docs/) 目录：

- 需求分析文档
- 需求规格说明书
- 技术选型方案
- 概要/详细设计说明书
- 数据库设计文档
- 接口文档
- 代码规范手册
- 开发环境搭建指南
- 部署手册
- 用户操作手册
- 版本发布日志

## 许可证

MIT License
