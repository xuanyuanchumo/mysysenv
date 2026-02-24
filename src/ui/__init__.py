"""
Mysysenv 图形界面模块。

提供基于 PySide6 的图形用户界面功能。
"""

import argparse
import sys


def run_gui(args: argparse.Namespace = None) -> int:
    """
    运行图形界面模式。
    
    参数:
        args: 解析后的命令行参数
        
    返回:
        退出码（0 表示成功）
    """
    try:
        from src.ui.backend import run_gui as _run_gui
        return _run_gui()
    except ImportError as e:
        print(f"错误：图形界面模式需要安装 PySide6。{e}")
        print("请使用以下命令安装：pip install PySide6>=6.8")
        return 1
