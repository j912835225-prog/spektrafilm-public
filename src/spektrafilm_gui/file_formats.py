"""
统一的文件格式扩展名常量。

供 widget_sections（导入对话框）、controller（批量保存、RAW 重处理）共用，
避免多处定义不同步。所有扩展名不带点，比对前用 .lstrip('.').lower() 归一。
"""
from __future__ import annotations

# RAW 扩展名（rawpy 支持的格式）
RAW_EXTS = frozenset({
    'arw', 'cr2', 'cr3', 'nef', 'nrw', 'orf', 'rw2', 'pef', 'srw',
    'dng', 'raf', 'raw', 'rwl', '3fr', 'mef', 'mrw', 'x3f', 'kdc',
    'dcr', 'erf', 'fff', 'iiq', 'mos', 'ptx', 'r3d', 'rwz', 'sr2',
})

# RGB 图像扩展名
RGB_EXTS = frozenset({'jpg', 'jpeg', 'png', 'tif', 'tiff', 'exr'})

# 全部支持的扩展名
SUPPORTED_EXTS = RAW_EXTS | RGB_EXTS
