from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from qtpy import QtCore, QtWidgets

from spektrafilm_gui import controller_persistence as persistence_actions
from spektrafilm_gui import controller_profile_sync as profile_sync
from spektrafilm_gui import controller_runtime as runtime
from spektrafilm_gui.controller_layers import (
    INPUT_LAYER_NAME,
    INPUT_PREVIEW_LAYER_NAME,
    OUTPUT_LAYER_NAME,
    ViewerLayerService,
)
from spektrafilm_gui.persistence import (
    clear_saved_default_gui_state,
    load_dialog_dir,
    load_gui_state_from_path,
    save_default_gui_state,
    save_dialog_dir,
    save_gui_state_to_path,
)
from spektrafilm_gui.state import PROJECT_DEFAULT_GUI_STATE, digest_after_selection, gui_state_from_params
from spektrafilm_gui.napari_layout import dialog_parent, reset_viewer_camera, set_canvas_background, set_status
from spektrafilm_gui.params_mapper import build_params_from_state
from spektrafilm_gui.state_bridge import apply_gui_state, collect_gui_state
from spektrafilm_gui.widgets import WidgetBundle
from spektrafilm_gui.file_formats import RAW_EXTS, SUPPORTED_EXTS

OUTPUT_FLOAT_DATA_KEY = 'pipeline_float_output'
OUTPUT_COLOR_SPACE_KEY = 'pipeline_output_color_space'
OUTPUT_CCTF_ENCODING_KEY = 'pipeline_output_cctf_encoding'
OUTPUT_DISPLAY_TRANSFORM_KEY = 'pipeline_use_display_transform'
OUTPUT_IS_FULL_RESOLUTION_KEY = 'pipeline_is_full_resolution'
PROFILE_SYNC_FIELDS = profile_sync.PROFILE_SYNC_FIELDS
if TYPE_CHECKING:
    import napari
    from napari.layers import Image as NapariImageLayer


QThreadPool = getattr(QtCore, 'QThreadPool')
QTimer = getattr(QtCore, 'QTimer')
QFileDialog = QtWidgets.QFileDialog
QMessageBox = QtWidgets.QMessageBox
SimulationRequest = runtime.SimulationRequest
SimulationResult = runtime.SimulationResult
STARTUP_PREVIEW_ASPECT_RATIO = (3, 2)


class _DirMemoryDialog:
    """Wraps QFileDialog to open in the last-used directory via QSettings."""

    def __init__(self, key: str) -> None:
        self._key = key

    def get_save_file_name(self, parent, title, filename, file_filter):
        last_dir = load_dialog_dir(self._key)
        initial = str(Path(last_dir) / Path(filename).name) if last_dir else filename
        path, fmt = QFileDialog.getSaveFileName(parent, title, initial, file_filter)
        if path:
            save_dialog_dir(self._key, str(Path(path).parent))
        return path, fmt

    def get_open_file_name(self, parent, title, _initial, file_filter):
        path, fmt = QFileDialog.getOpenFileName(
            parent, title, load_dialog_dir(self._key), file_filter
        )
        if path:
            save_dialog_dir(self._key, str(Path(path).parent))
        return path, fmt


class _LazyModuleProxy:
    def __init__(self, loader):
        self._loader = loader
        self._module = None

    def _load(self):
        if self._module is None:
            self._module = self._loader()
        return self._module

    def __getattr__(self, name: str):
        return getattr(self._load(), name)


def _import_colour_module():
    return import_module('colour')


def _import_pil_image_module():
    return import_module('PIL.Image')


def _import_imagecms_module():
    return import_module('PIL.ImageCms')


def runtime_simulator(*args, **kwargs):
    return import_module('spektrafilm.runtime.api').Simulator(*args, **kwargs)


def digest_params(*args, **kwargs):
    return import_module('spektrafilm.runtime.api').digest_params(*args, **kwargs)


def load_image_oiio(*args, **kwargs):
    return import_module('spektrafilm.utils.io').load_image_oiio(*args, **kwargs)


def save_image_oiio(*args, **kwargs):
    return import_module("spektrafilm.utils.io").save_image_oiio(*args, **kwargs)


def read_image_metadata(*args, **kwargs):
    return import_module("spektrafilm.utils.io").read_image_metadata(*args, **kwargs)


def write_image_metadata(*args, **kwargs):
    return import_module("spektrafilm.utils.io").write_image_metadata(*args, **kwargs)


def load_and_process_raw_file(*args, **kwargs):
    return import_module('spektrafilm.utils.raw_file_processor').load_and_process_raw_file(*args, **kwargs)


def resize_for_preview(*args, **kwargs):
    return import_module('spektrafilm.utils.preview').resize_for_preview(*args, **kwargs)


colour = _LazyModuleProxy(_import_colour_module)
PILImage = _LazyModuleProxy(_import_pil_image_module)
ImageCms = _LazyModuleProxy(_import_imagecms_module)


class GuiController:
    def __init__(self, *, viewer: napari.Viewer, widgets: WidgetBundle):
        self._viewer = viewer
        self._widgets = widgets
        self._layers = ViewerLayerService(
            viewer=viewer,
            output_float_data_key=OUTPUT_FLOAT_DATA_KEY,
            output_color_space_key=OUTPUT_COLOR_SPACE_KEY,
            output_cctf_encoding_key=OUTPUT_CCTF_ENCODING_KEY,
            output_display_transform_key=OUTPUT_DISPLAY_TRANSFORM_KEY,
            output_is_full_resolution_key=OUTPUT_IS_FULL_RESOLUTION_KEY,
        )
        self._thread_pool = QThreadPool.globalInstance()
        self._active_simulation_worker: runtime.SimulationWorker | None = None
        self._active_simulation_label: str | None = None
        self._runtime_simulator = None
        self._next_runtime_digest_applies_stock_specifics = True
        self._current_input_image: np.ndarray | None = None
        self._current_input_path: str | None = None
        self._current_preview_image: np.ndarray | None = None
        self._auto_preview_scheduled = False
        self._pending_auto_preview = False
        self._active_simulation_reports_status = True
        self._raw_reprocess_scheduled = False
        # 中间结果缓存
        self._expose_cache: dict | None = None   # {'key': str, 'img_prep': array, 'log_raw': array, 'pipeline': pipeline}
        self._develop_cache: dict | None = None  # {'key': str, 'cmy_film': array}
        # 颗粒裁剪预览（独立控制器，不依赖主扫描状态）
        from spektrafilm_gui.controller_grain_preview import GrainCropPreviewController
        preview_widget = getattr(widgets, 'grain_crop_preview', None)
        self._grain_preview: GrainCropPreviewController | None = (
            GrainCropPreviewController(
                preview_widget=preview_widget,
                get_input_image=lambda: self._current_input_image,
                get_gui_state=lambda: collect_gui_state(widgets=self._widgets),
                is_main_scanning=lambda: self._active_simulation_worker is not None,
                prepare_display_fn=self._prepare_output_display_image,
            )
            if preview_widget is not None else None
        )
        # 对比模式状态：True 时画布显示 input_preview（原图），False 显示 output（模拟图）
        self._compare_mode_active: bool = False

    def show_startup_placeholder(self) -> None:
        if self._white_border_layer() is not None:
            return

        state = collect_gui_state(widgets=self._widgets)
        preview_height = max(int(state.display.preview_max_size), 1)
        preview_width = max(
            int(round(preview_height * STARTUP_PREVIEW_ASPECT_RATIO[1] / STARTUP_PREVIEW_ASPECT_RATIO[0])),
            1,
        )
        # 占位图必须是 float32，与 prepare_input_color_preview_image 返回的真图 dtype 一致；
        # 否则 napari 会用 uint8 范围 (0, 255) 锁 contrast_limits，
        # 后续替换成 float32 ∈ [0, 1] 时图像会被渲染成纯黑（按 Y 进对比模式才会暴露）。
        placeholder_preview = np.zeros((preview_height, preview_width, 3), dtype=np.float32)
        self._layers.set_or_add_input_preview_layer(
            placeholder_preview,
            watermark_source_size=(preview_height, preview_width),
            white_padding=state.display.white_padding,
            hide_output=True,
            set_active=True,
        )
        self._home_input_stack()

    def load_input_image(self, path: str) -> None:
        image = load_image_oiio(path)[..., :3]
        self._current_input_path = path
        self._expose_cache = None
        self._develop_cache = None
        if self._grain_preview is not None:
            self._grain_preview.reset()
        self._set_or_add_input_stack(image)
        self._request_auto_preview_if_enabled()
        self._schedule_expose_precompute()

    def load_raw_image(self, path: str) -> None:
        gui_state = collect_gui_state(widgets=self._widgets)
        set_status(self._viewer, "正在加载 RAW...", timeout_ms=0)
        lens_info: dict[str, str] = {}
        try:
            image = load_and_process_raw_file(
                path,
                white_balance=gui_state.load_raw.white_balance,
                temperature=gui_state.load_raw.temperature,
                tint=gui_state.load_raw.tint,
                lens_correction=gui_state.load_raw.lens_correction,
                output_colorspace=gui_state.input_image.input_color_space,
                output_cctf_encoding=gui_state.input_image.apply_cctf_decoding,
                lens_info_out=lens_info,
            )
        except (OSError, ValueError) as exc:
            QMessageBox.critical(dialog_parent(self._viewer), '加载 RAW', f'加载 RAW 图像失败。\n\n{exc}')
            set_status(self._viewer, '加载 RAW 失败')
            return

        self._current_input_path = path
        self._expose_cache = None
        self._develop_cache = None
        self._set_or_add_input_stack(image)

        lens_summary = lens_info.get('summary')
        if lens_summary:
            set_status(
                self._viewer,
                f"已加载 RAW 并应用镜头校正：{lens_summary}",
            )
        elif gui_state.load_raw.lens_correction:
            set_status(self._viewer, "已加载 RAW，镜头校正未应用")
        else:
            set_status(self._viewer, "已加载 RAW")
        self._request_auto_preview_if_enabled()
        self._schedule_expose_precompute()

    def refresh_preview_cache(self, *_args) -> None:
        input_image = self._current_input_image
        if input_image is None:
            return
        self._update_preview_cache(
            input_image,
            home_input_stack=False,
            hide_output=False,
        )

    def rotate_input_image_clockwise(self) -> None:
        self._rotate_input_image(quarter_turns=-1)

    def rotate_input_image_counterclockwise(self) -> None:
        self._rotate_input_image(quarter_turns=1)

    def _rotate_input_image(self, *, quarter_turns: int) -> None:
        input_image = self._current_input_image
        if input_image is None:
            return

        rotated_image = np.rot90(np.asarray(input_image), k=int(quarter_turns))
        self._update_preview_cache(
            rotated_image,
            home_input_stack=True,
            hide_output=True,
        )
        self._request_auto_preview_if_enabled()

    def apply_profile_defaults(self, _selected_value: str) -> None:
        state = collect_gui_state(widgets=self._widgets)
        if not state.simulation.film_stock or not state.simulation.print_paper:
            return

        params = build_params_from_state(state)
        synced_state = gui_state_from_params(
            digest_after_selection(params),
            film_stock=state.simulation.film_stock,
            print_paper=state.simulation.print_paper,
        )
        self._apply_profile_sync_state(synced_state)
        self._next_runtime_digest_applies_stock_specifics = True

    def _apply_profile_sync_state(self, synced_state) -> None:
        profile_sync.apply_profile_sync_state(
            widgets=self._widgets,
            synced_state=synced_state,
            profile_sync_fields=PROFILE_SYNC_FIELDS,
        )

    def run_preview(self) -> None:
        self._run_preview(report_status=True)

    def _run_preview(self, *, report_status: bool) -> None:
        self._start_simulation(
            source_layer_name=INPUT_PREVIEW_LAYER_NAME,
            mode_label='预览',
            report_status=report_status,
        )

    def run_scan(self) -> None:
        self._start_simulation(source_layer_name=INPUT_LAYER_NAME, mode_label='扫描')

    def request_auto_preview(self, *_args) -> None:
        if self._auto_preview_scheduled:
            return
        self._auto_preview_scheduled = True
        QTimer.singleShot(0, self._run_scheduled_auto_preview)

    def report_default_restored(self, value: float, *, label: str | None = None) -> None:
        """滑块双击归零时由控件触发，状态栏给一条提示。"""
        # 默认值小数位按规模自适应：≥10 显示整数，1-10 一位小数，<1 两位小数
        abs_v = abs(value)
        if abs_v >= 10:
            text = f'{value:.0f}'
        elif abs_v >= 1:
            text = f'{value:.1f}'
        else:
            text = f'{value:.2f}'
        prefix = f'{label}：' if label else ''
        set_status(self._viewer, f'{prefix}已恢复默认值 {text}')

    def request_auto_scan(self, *_args) -> None:
        """颗粒参数改变时，debounce 1200ms 后自动跑全分辨率扫描。"""
        if self._current_input_image is None:
            return
        if self._auto_preview_scheduled:
            return
        self._auto_preview_scheduled = True
        QTimer.singleShot(1200, self._run_scheduled_auto_scan)

    def _run_scheduled_auto_scan(self) -> None:
        self._auto_preview_scheduled = False
        if self._current_input_image is None:
            return
        if self._active_simulation_worker is not None:
            self._pending_auto_preview = True
            return
        set_status(self._viewer, '正在扫描，图像越大耗时越长，请稍候...', timeout_ms=0)
        self._start_simulation(source_layer_name=INPUT_LAYER_NAME, mode_label='扫描', report_status=False)

    def request_raw_reprocess(self, *_args) -> None:
        """RAW 参数改变时，debounce 800ms 后自动重新处理 RAW。"""
        if self._raw_reprocess_scheduled:
            return
        # 只有当前加载的是 RAW 文件时才触发
        if self._current_input_path is None:
            return
        ext = self._current_input_path.rsplit('.', 1)[-1].lower()
        if ext not in RAW_EXTS:
            return
        self._raw_reprocess_scheduled = True
        QTimer.singleShot(800, self._run_scheduled_raw_reprocess)

    def _run_scheduled_raw_reprocess(self) -> None:
        self._raw_reprocess_scheduled = False
        if self._current_input_path is None:
            return
        self.load_raw_image(self._current_input_path)

    def _request_auto_preview_if_enabled(self) -> None:
        if not self._auto_preview_enabled() or self._current_preview_image is None:
            return
        self.request_auto_preview()

    def report_display_transform_status(self, enabled: bool) -> None:
        if enabled and not self.sync_display_transform_availability(report_status=True):
            return
        set_status(self._viewer, runtime.display_transform_status_message(enabled, imagecms_module=ImageCms))

    def set_gray_18_canvas_enabled(self, enabled: bool) -> None:
        set_canvas_background(self._viewer, gray_18_canvas=enabled)

    def set_output_interpolation_mode(self, mode: str) -> None:
        output_layer = self._output_layer()
        if output_layer is None:
            return
        self._layers.set_output_layer_interpolation(output_layer, mode)

    def sync_display_transform_availability(self, *, report_status: bool) -> bool:
        if runtime.display_profile_available(imagecms_module=ImageCms):
            return True

        self._set_display_transform_checked(False)
        if report_status:
            set_status(self._viewer, '显示变换不可用：未检测到显示器配置文件，已禁用')
        return False

    def save_output_layer(self) -> None:
        output_layer = self._output_layer()
        if output_layer is None:
            QMessageBox.warning(dialog_parent(self._viewer), '保存输出', '请先运行模拟，再保存输出图层。')
            return

        # ── 弹出保存选项对话框 ──────────────────────────────────────────────
        from qtpy import QtWidgets as _QW, QtCore as _QC
        opts_dialog = _QW.QDialog(dialog_parent(self._viewer))
        opts_dialog.setWindowTitle('保存选项')
        opts_dialog.setFixedWidth(320)
        opts_layout = _QW.QFormLayout(opts_dialog)
        opts_layout.setContentsMargins(16, 16, 16, 16)
        opts_layout.setSpacing(10)

        fmt_combo = _QW.QComboBox()
        fmt_combo.addItems(['JPEG (.jpg)', 'PNG (.png)', 'TIFF 16bit (.tif)', 'TIFF 32bit float (.tif)', 'EXR 16bit (.exr)', 'EXR 32bit (.exr)'])
        opts_layout.addRow('格式', fmt_combo)

        quality_spin = _QW.QSpinBox()
        quality_spin.setRange(1, 100)
        quality_spin.setValue(95)
        quality_spin.setSuffix('%')
        quality_label = _QW.QLabel('JPEG 质量')
        opts_layout.addRow(quality_label, quality_spin)

        def on_fmt_changed(idx):
            is_jpeg = idx == 0
            quality_label.setVisible(is_jpeg)
            quality_spin.setVisible(is_jpeg)
        fmt_combo.currentIndexChanged.connect(on_fmt_changed)

        btn_box = _QW.QDialogButtonBox(_QW.QDialogButtonBox.Ok | _QW.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(opts_dialog.accept)
        btn_box.rejected.connect(opts_dialog.reject)
        opts_layout.addRow(btn_box)

        if opts_dialog.exec_() != _QW.QDialog.Accepted:
            return

        fmt_idx = fmt_combo.currentIndex()
        fmt_map = {
            0: ('jpg', 8,  95),
            1: ('png', 8,  95),
            2: ('tif', 16, 95),
            3: ('tif', 32, 95),
            4: ('exr', 16, 95),
            5: ('exr', 32, 95),
        }
        ext, bit_depth, _ = fmt_map[fmt_idx]
        jpeg_quality = quality_spin.value() if fmt_idx == 0 else 95

        # ── 文件保存对话框 ──────────────────────────────────────────────────
        if self._current_input_path is not None:
            default_name = Path(self._current_input_path).stem + '.' + ext
        else:
            default_name = 'output.' + ext

        filter_str = {
            'jpg': 'JPEG 图像 (*.jpg *.jpeg)',
            'png': 'PNG 图像 (*.png)',
            'tif': 'TIFF 图像 (*.tif *.tiff)',
            'exr': 'EXR 图像 (*.exr)',
        }[ext]

        filepath, _ = _DirMemoryDialog('save_output').get_save_file_name(
            dialog_parent(self._viewer),
            '保存输出图像',
            default_name,
            filter_str,
        )
        if not filepath:
            return

        gui_state = collect_gui_state(widgets=self._widgets)

        # 如果 output layer 已经是全分辨率扫描结果，直接复用，不重跑
        cached_float = self._output_layer_float_data()
        is_full_res = output_layer.metadata.get(OUTPUT_IS_FULL_RESOLUTION_KEY, False)
        if is_full_res and cached_float is not None:
            image_data = np.asarray(cached_float, dtype=np.float64)
            set_status(self._viewer, '使用已有扫描结果保存...', timeout_ms=0)
            QtWidgets.QApplication.processEvents()
        else:
            # 没有全分辨率缓存，重跑全分辨率模拟
            input_image = self._current_input_image
            if input_image is None:
                QMessageBox.warning(dialog_parent(self._viewer), '保存输出', '请先加载输入图像，再保存。')
                return

            set_status(self._viewer, '正在生成全分辨率输出，请稍候...', timeout_ms=0)
            QtWidgets.QApplication.processEvents()

            try:
                image_data = self._run_full_scan_with_cache(gui_state, input_image)
            except Exception as exc:
                QMessageBox.critical(dialog_parent(self._viewer), '保存输出', f'生成输出失败。\n\n{exc}')
                set_status(self._viewer, '保存失败')
                return

        source_color_space, source_cctf_encoding = self._output_layer_render_settings(
            default_color_space=gui_state.simulation.output_color_space,
            default_cctf_encoding=True,
        )
        saving_color_space = gui_state.simulation.saving_color_space
        saving_cctf_encoding = gui_state.simulation.saving_cctf_encoding
        if source_color_space != saving_color_space:
            image_data = colour.RGB_to_RGB(
                image_data,
                source_color_space,
                saving_color_space,
                apply_cctf_decoding=source_cctf_encoding,
                apply_cctf_encoding=saving_cctf_encoding,
            )
        elif source_cctf_encoding != saving_cctf_encoding:
            image_data = colour.RGB_to_RGB(
                image_data,
                source_color_space,
                saving_color_space,
                apply_cctf_decoding=source_cctf_encoding,
                apply_cctf_encoding=saving_cctf_encoding,
            )

        source_metadata = None

        if self._current_input_path is not None:
            source_metadata = read_image_metadata(self._current_input_path)

        try:
            save_image_oiio(
                filepath,
                image_data,
                bit_depth=bit_depth,
                jpeg_quality=jpeg_quality,
                color_space=saving_color_space,
                cctf_encoding=saving_cctf_encoding,
            )
        except (OSError, ValueError) as exc:
            QMessageBox.critical(dialog_parent(self._viewer), '保存输出', f'保存输出图像失败。\n\n{exc}')
            return

        metadata_write_error = None
        try:
            write_image_metadata(
                filepath,
                source_metadata,
                saving_color_space=saving_color_space,
                saving_cctf_encoding=saving_cctf_encoding,
            )
        except Exception as exc:
            metadata_write_error = exc

        if metadata_write_error is not None:
            set_status(
                self._viewer,
                f"已保存到 {filepath}（元数据复制失败：{metadata_write_error}）",
            )
        else:
            set_status(self._viewer, f"已保存到 {filepath}")

    def batch_save(self) -> None:
        """批量处理：选择文件夹，用当前参数处理所有图片并保存到同一目录。"""
        from qtpy import QtWidgets as _QW
        import os as _os

        # 选择输入文件夹
        input_dir = _QW.QFileDialog.getExistingDirectory(
            dialog_parent(self._viewer),
            '选择要批量处理的图片文件夹',
            _os.path.expanduser('~/Desktop'),
        )
        if not input_dir:
            return

        files = sorted([
            f for f in _os.listdir(input_dir)
            if _os.path.splitext(f)[1].lstrip('.').lower() in SUPPORTED_EXTS
        ])
        if not files:
            QMessageBox.warning(dialog_parent(self._viewer), '批量保存', '文件夹内没有支持的图片文件。')
            return

        # 选择输出格式
        fmt_dialog = _QW.QDialog(dialog_parent(self._viewer))
        fmt_dialog.setWindowTitle('批量保存选项')
        fmt_dialog.setFixedWidth(320)
        layout = _QW.QFormLayout(fmt_dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        fmt_combo = _QW.QComboBox()
        fmt_combo.addItems(['JPEG (.jpg)', 'PNG (.png)', 'TIFF 16bit (.tif)', 'TIFF 32bit float (.tif)'])
        layout.addRow('输出格式', fmt_combo)

        quality_spin = _QW.QSpinBox()
        quality_spin.setRange(1, 100)
        quality_spin.setValue(95)
        quality_spin.setSuffix('%')
        quality_label = _QW.QLabel('JPEG 质量')
        layout.addRow(quality_label, quality_spin)

        suffix_edit = _QW.QLineEdit('_spektrafilm')
        layout.addRow('文件名后缀', suffix_edit)

        def on_fmt(idx):
            quality_label.setVisible(idx == 0)
            quality_spin.setVisible(idx == 0)
        fmt_combo.currentIndexChanged.connect(on_fmt)

        btn_box = _QW.QDialogButtonBox(_QW.QDialogButtonBox.Ok | _QW.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(fmt_dialog.accept)
        btn_box.rejected.connect(fmt_dialog.reject)
        layout.addRow(btn_box)

        if fmt_dialog.exec_() != _QW.QDialog.Accepted:
            return

        fmt_idx = fmt_combo.currentIndex()
        fmt_map = {0: ('jpg', 8), 1: ('png', 8), 2: ('tif', 16), 3: ('tif', 32)}
        ext, bit_depth = fmt_map[fmt_idx]
        jpeg_quality = quality_spin.value() if fmt_idx == 0 else 95
        suffix = suffix_edit.text().strip()

        # 构建参数（一次，复用 Simulator）
        gui_state = collect_gui_state(widgets=self._widgets)
        try:
            params = build_params_from_state(gui_state)
            from spektrafilm.runtime.params_builder import digest_params as _digest
            from spektrafilm.runtime.process import Simulator as _Sim
            digested = _digest(params)
            sim = _Sim(digested)
        except Exception as exc:
            QMessageBox.critical(dialog_parent(self._viewer), '批量保存', f'初始化模拟器失败。\n\n{exc}')
            return

        # 进度对话框
        progress = _QW.QProgressDialog('正在批量处理...', '取消', 0, len(files), dialog_parent(self._viewer))
        progress.setWindowTitle('批量保存')
        progress.setMinimumDuration(0)
        progress.setValue(0)

        errors = []
        for i, filename in enumerate(files):
            if progress.wasCanceled():
                break
            progress.setLabelText(f'处理中 ({i+1}/{len(files)})：{filename}')
            progress.setValue(i)
            _QW.QApplication.processEvents()

            filepath = _os.path.join(input_dir, filename)
            stem = _os.path.splitext(filename)[0]
            out_name = f"{stem}{suffix}.{ext}"
            out_path = _os.path.join(input_dir, out_name)

            try:
                file_ext = _os.path.splitext(filename)[1].lstrip('.').lower()
                if file_ext in RAW_EXTS:
                    image = load_and_process_raw_file(
                        filepath,
                        white_balance=gui_state.load_raw.white_balance,
                        temperature=gui_state.load_raw.temperature,
                        tint=gui_state.load_raw.tint,
                        lens_correction=gui_state.load_raw.lens_correction,
                        output_colorspace=gui_state.input_image.input_color_space,
                        output_cctf_encoding=gui_state.input_image.apply_cctf_decoding,
                    )
                else:
                    image = load_image_oiio(filepath)[..., :3]

                result = sim.process(np.asarray(image, dtype=np.float64)[..., :3])

                # pipeline 输出已是 sRGB gamma encoded（params.io.output_cctf_encoding=True）
                # 只在 source 与 saving 不一致时才转换
                src_cs = gui_state.simulation.output_color_space
                src_enc = True
                save_cs = gui_state.simulation.saving_color_space
                save_enc = gui_state.simulation.saving_cctf_encoding
                if src_cs != save_cs or src_enc != save_enc:
                    result = colour.RGB_to_RGB(
                        result, src_cs, save_cs,
                        apply_cctf_decoding=src_enc,
                        apply_cctf_encoding=save_enc,
                    )

                save_image_oiio(
                    out_path,
                    result,
                    bit_depth=bit_depth,
                    jpeg_quality=jpeg_quality,
                    color_space=save_cs,
                    cctf_encoding=save_enc,
                )
            except Exception as exc:
                errors.append(f'{filename}: {exc}')

        progress.setValue(len(files))

        if errors:
            QMessageBox.warning(
                dialog_parent(self._viewer), '批量保存',
                f'完成，但 {len(errors)} 个文件失败：\n' + '\n'.join(errors[:5]),
            )
            set_status(self._viewer, f'批量保存完成，{len(files) - len(errors)}/{len(files)} 成功')
        else:
            set_status(self._viewer, f'批量保存完成，共处理 {len(files)} 张图片 → {input_dir}')

    def setup_grain_preview_mouse_callback(self) -> None:
        """在 napari canvas 上安装 Option+点击 eventFilter。"""
        if self._grain_preview is not None:
            self._grain_preview.install_canvas_filter(self._viewer)

    def request_grain_crop_preview(self, *_args) -> None:
        """颗粒参数改变时触发裁剪预览（debounce）。"""
        if self._grain_preview is not None:
            self._grain_preview.request()

    # ── 对比模式（按 Y / 点 ⇆ 全屏切换原图 vs 模拟图）─────────────────────

    def is_compare_mode_active(self) -> bool:
        return bool(self._compare_mode_active)

    def toggle_split_mode(self) -> None:
        """切换对比模式：全屏在原图（input_preview）和模拟图（output）之间 toggle。

        Lightroom 反斜杠键风格。比 Split View 简单，依赖少，UX 直觉。
        Tab 栏 ⇆ 按钮 + Y 快捷键的入口。
        """
        output_layer = self._layers.image_layer(OUTPUT_LAYER_NAME)
        input_layer = self._layers.preview_input_layer()
        if output_layer is None or input_layer is None:
            set_status(self._viewer, '请先生成胶片效果（点预览或扫描）后再开对比')
            return

        # 停掉 output 的入场动画/crossfade，避免数据正在被定时器改写
        self._layers._stop_output_layer_animation(output_layer, restore_final=True)

        if self._compare_mode_active:
            # 当前正在显示原图 → 切回模拟图
            try:
                input_layer.visible = False
                output_layer.visible = True
            except Exception:
                pass
            self._layers.move_layer_to_top(output_layer)
            self._layers.set_active_layer(output_layer)
            self._compare_mode_active = False
            set_status(self._viewer, '对比：胶片效果（再按 Y 看原图）')
        else:
            # 当前正在显示模拟图 → 切到原图
            try:
                output_layer.visible = False
                input_layer.visible = True
            except Exception:
                pass
            self._layers.move_layer_to_top(input_layer)
            self._layers.set_active_layer(input_layer)
            self._compare_mode_active = True
            set_status(self._viewer, '对比：原图（再按 Y 看胶片效果）')

    # ── 颗粒裁剪预览 ─────────────────────────────────────────────────────────

    def set_grain_crop_center(self, cx: float, cy: float) -> None:
        if self._grain_preview is not None:
            self._grain_preview.set_crop_center(cx, cy)

    # ── 中间结果缓存 ──────────────────────────────────────────────────────────

    def _make_expose_key(self, state) -> str:
        """生成 expose 阶段的缓存 key，依赖：图像路径 + 胶片型号 + 曝光 + Halation + 前期柔光 + 镜头模糊"""
        s = state.simulation
        h = state.halation
        return '|'.join([
            str(self._current_input_path),
            s.film_stock,
            str(s.exposure_compensation_ev),
            str(s.auto_exposure),
            str(s.camera_lens_blur_um),
            str(s.camera_diffusion_filter_active),
            str(s.camera_diffusion_filter_family),
            str(s.camera_diffusion_filter_strength),
            str(s.camera_diffusion_filter_spatial_scale),
            str(h.active),
            str(h.scatter_amount), str(h.scatter_spatial_scale),
            str(h.halation_amount), str(h.halation_spatial_scale),
            str(h.boost_ev), str(h.protect_ev), str(h.boost_range),
            str(h.halation_strength), str(h.halation_first_sigma_um),
            str(h.halation_n_bounces), str(h.halation_bounce_decay),
            str(state.input_image.input_color_space),
            str(state.input_image.apply_cctf_decoding),
        ])

    def _make_develop_key(self, state, expose_key: str) -> str:
        """生成 develop 阶段的缓存 key，依赖：expose_key + 颗粒 + DIR 耦合剂 + 胶片 gamma"""
        g = state.grain
        c = state.couplers
        sp = state.special
        return expose_key + '||' + '|'.join([
            str(g.active), str(g.particle_area_um2), str(g.blur),
            str(g.blur_dye_clouds_um), str(g.particle_scale),
            str(c.active), str(c.amount),
            str(sp.film_gamma_factor),
        ])

    def _schedule_expose_precompute(self) -> None:
        """图片加载后，延迟 500ms 在后台预计算 expose，缓存结果。"""
        QTimer.singleShot(500, self._run_expose_precompute)

    def _run_expose_precompute(self) -> None:
        """后台预计算 expose，结果缓存到 _expose_cache。"""
        if self._current_input_image is None:
            return
        if self._active_simulation_worker is not None:
            # 有扫描在跑，延迟重试
            QTimer.singleShot(2000, self._run_expose_precompute)
            return

        state = collect_gui_state(widgets=self._widgets)
        expose_key = self._make_expose_key(state)

        # 已有有效缓存，不重算
        if self._expose_cache is not None and self._expose_cache.get('key') == expose_key:
            return

        try:
            params = build_params_from_state(state)
            from spektrafilm.runtime.params_builder import digest_params as _digest
            from spektrafilm.runtime.pipeline import SimulationPipeline as _Pipeline
            digested = _digest(params)
            pipeline = _Pipeline(digested)

            img = np.asarray(self._current_input_image, dtype=np.float64)[..., :3]
            img_prep = pipeline._preprocess(img)
            log_raw = pipeline._filming_stage.expose(img_prep.copy())

            self._expose_cache = {
                'key': expose_key,
                'img_prep': img_prep,
                'log_raw': log_raw,
                'pipeline': pipeline,
                'pixel_size_um': pipeline._resize_service.pixel_size_um,
            }
            self._develop_cache = None  # expose 更新后 develop 缓存失效
        except Exception:
            self._expose_cache = None

    def _run_full_scan_with_cache(self, state, input_image: np.ndarray) -> np.ndarray:
        """带缓存的全分辨率扫描。根据参数变化决定从哪个阶段开始。"""
        from spektrafilm.runtime.params_builder import digest_params as _digest
        from spektrafilm.runtime.pipeline import SimulationPipeline as _Pipeline

        expose_key = self._make_expose_key(state)
        develop_key = self._make_develop_key(state, expose_key)

        params = build_params_from_state(state)
        digested = _digest(params)

        # 检查 develop 缓存（最快路径：只跑 printing + scan）
        if (self._develop_cache is not None
                and self._develop_cache.get('key') == develop_key
                and self._expose_cache is not None
                and self._expose_cache.get('key') == expose_key):
            pipeline = self._expose_cache['pipeline']
            pipeline.update(digested)
            # update() 会重建 ResizingService，pixel_size_um 被重置为 None；
            # 而 printing/scanning 阶段依赖它做 diffusion/halation 物理换算。
            # 从缓存恢复，避免 None / int 崩溃。
            pipeline._resize_service.pixel_size_um = self._expose_cache['pixel_size_um']
            cmy_film = self._develop_cache['cmy_film']
            log_raw_print = pipeline._printing_stage.expose(cmy_film.copy())
            cmy_print = pipeline._printing_stage.develop(log_raw_print)
            return pipeline._scanning_stage.scan(cmy_print)

        # 检查 expose 缓存（中间路径：只跑 develop + printing + scan）
        if (self._expose_cache is not None
                and self._expose_cache.get('key') == expose_key):
            pipeline = self._expose_cache['pipeline']
            pipeline.update(digested)
            pipeline._resize_service.pixel_size_um = self._expose_cache['pixel_size_um']
            log_raw = self._expose_cache['log_raw']
            cmy_film = pipeline._filming_stage.develop(log_raw.copy())
            # 更新 develop 缓存
            self._develop_cache = {'key': develop_key, 'cmy_film': cmy_film.copy()}
            log_raw_print = pipeline._printing_stage.expose(cmy_film.copy())
            cmy_print = pipeline._printing_stage.develop(log_raw_print)
            return pipeline._scanning_stage.scan(cmy_print)

        # 无缓存，完整跑
        pipeline = _Pipeline(digested)
        img = np.asarray(input_image, dtype=np.float64)[..., :3]
        img_prep = pipeline._preprocess(img)
        log_raw = pipeline._filming_stage.expose(img_prep.copy())
        # 更新 expose 缓存（含 pixel_size_um，用于命中缓存后恢复）
        self._expose_cache = {
            'key': expose_key,
            'img_prep': img_prep,
            'log_raw': log_raw,
            'pipeline': pipeline,
            'pixel_size_um': pipeline._resize_service.pixel_size_um,
        }
        cmy_film = pipeline._filming_stage.develop(log_raw.copy())
        self._develop_cache = {'key': develop_key, 'cmy_film': cmy_film.copy()}
        log_raw_print = pipeline._printing_stage.expose(cmy_film.copy())
        cmy_print = pipeline._printing_stage.develop(log_raw_print)
        return pipeline._scanning_stage.scan(cmy_print)

    def apply_preset(self, name: str) -> None:
        """从预设目录加载指定预设并应用。"""
        preset_path = Path.home() / '.spektrafilm' / 'presets' / f"{name}.json"
        try:
            state = load_gui_state_from_path(preset_path)
        except Exception as exc:
            QMessageBox.critical(dialog_parent(self._viewer), '加载预设', f'加载失败。\n\n{exc}')
            return
        apply_gui_state(widgets=self._widgets, state=state)
        self._sync_canvas_background()
        set_status(self._viewer, f'已应用预设：{name}')

    def delete_preset(self, name: str) -> None:
        """删除指定预设文件。"""
        preset_path = Path.home() / '.spektrafilm' / 'presets' / f"{name}.json"
        try:
            if preset_path.exists():
                preset_path.unlink()
        except OSError as exc:
            QMessageBox.critical(dialog_parent(self._viewer), '删除预设', f'删除失败。\n\n{exc}')
            return
        # 刷新主面板预设列表
        preset_panel = getattr(self._widgets, 'preset_panel', None)
        if preset_panel is not None and hasattr(preset_panel, 'refresh'):
            preset_panel.refresh()
        set_status(self._viewer, f'已删除预设：{name}')

    def save_preset(self) -> None:
        """将当前参数保存为命名预设。"""
        from qtpy import QtWidgets as _QW

        name, ok = _QW.QInputDialog.getText(
            dialog_parent(self._viewer),
            '另存为预设',
            '预设名称：',
        )
        if not ok or not name.strip():
            return
        name = name.strip()

        presets_dir = Path.home() / '.spektrafilm' / 'presets'
        presets_dir.mkdir(parents=True, exist_ok=True)
        preset_path = presets_dir / f"{name}.json"

        state = collect_gui_state(widgets=self._widgets)
        save_gui_state_to_path(state, preset_path)
        # 刷新主面板预设列表
        preset_panel = getattr(self._widgets, 'preset_panel', None)
        if preset_panel is not None and hasattr(preset_panel, 'refresh'):
            preset_panel.refresh()
        set_status(self._viewer, f'预设已保存：{name}')

    def load_preset(self) -> None:
        """从已保存的预设列表中选择并加载。"""
        from qtpy import QtWidgets as _QW

        presets_dir = Path.home() / '.spektrafilm' / 'presets'
        if not presets_dir.exists():
            QMessageBox.information(dialog_parent(self._viewer), '加载预设', '还没有保存任何预设。')
            return

        presets = sorted([p.stem for p in presets_dir.glob('*.json')])
        if not presets:
            QMessageBox.information(dialog_parent(self._viewer), '加载预设', '还没有保存任何预设。')
            return

        name, ok = _QW.QInputDialog.getItem(
            dialog_parent(self._viewer),
            '加载预设',
            '选择预设：',
            presets,
            0,
            False,
        )
        if not ok or not name:
            return

        preset_path = presets_dir / f"{name}.json"
        try:
            state = load_gui_state_from_path(preset_path)
        except Exception as exc:
            QMessageBox.critical(dialog_parent(self._viewer), '加载预设', f'加载失败。\n\n{exc}')
            return

        apply_gui_state(widgets=self._widgets, state=state)
        self._sync_canvas_background()
        set_status(self._viewer, f'已加载预设：{name}')

    def save_current_as_default(self) -> None:
        persistence_actions.save_current_as_default(
            viewer=self._viewer,
            widgets=self._widgets,
            collect_gui_state_fn=collect_gui_state,
            save_default_gui_state_fn=save_default_gui_state,
            set_status_fn=set_status,
            dialog_parent_fn=dialog_parent,
            message_box=QMessageBox,
        )

    def save_current_state_to_file(self) -> None:
        persistence_actions.save_current_state_to_file(
            viewer=self._viewer,
            widgets=self._widgets,
            file_dialog=_DirMemoryDialog('gui_state'),
            collect_gui_state_fn=collect_gui_state,
            save_gui_state_to_path_fn=save_gui_state_to_path,
            set_status_fn=set_status,
            dialog_parent_fn=dialog_parent,
            message_box=QMessageBox,
        )

    def load_state_from_file(self) -> None:
        persistence_actions.load_state_from_file(
            viewer=self._viewer,
            widgets=self._widgets,
            file_dialog=_DirMemoryDialog('gui_state'),
            load_gui_state_from_path_fn=load_gui_state_from_path,
            apply_gui_state_fn=apply_gui_state,
            sync_canvas_background_fn=self._sync_canvas_background,
            set_status_fn=set_status,
            dialog_parent_fn=dialog_parent,
            message_box=QMessageBox,
        )

    def restore_factory_default(self) -> None:
        persistence_actions.restore_factory_default(
            viewer=self._viewer,
            widgets=self._widgets,
            project_default_gui_state=PROJECT_DEFAULT_GUI_STATE,
            clear_saved_default_gui_state_fn=clear_saved_default_gui_state,
            apply_gui_state_fn=apply_gui_state,
            sync_canvas_background_fn=self._sync_canvas_background,
            set_status_fn=set_status,
            dialog_parent_fn=dialog_parent,
            message_box=QMessageBox,
        )

    def _preview_input_layer(self) -> NapariImageLayer | None:
        return self._layers.preview_input_layer()

    def _white_border_layer(self) -> NapariImageLayer | None:
        return self._layers.white_border_layer()

    def _set_or_add_output_layer(
        self,
        image: np.ndarray,
        *,
        float_image: np.ndarray,
        output_color_space: str,
        output_cctf_encoding: bool,
        use_display_transform: bool,
        is_full_resolution: bool = False,
    ) -> None:
        self._layers.set_or_add_output_layer(
            image,
            float_image=float_image,
            output_color_space=output_color_space,
            output_cctf_encoding=output_cctf_encoding,
            use_display_transform=use_display_transform,
            output_interpolation_mode=self._output_interpolation_mode(),
            is_full_resolution=is_full_resolution,
        )

    def _set_or_add_input_stack(
        self,
        image: np.ndarray,
    ) -> None:
        self._update_preview_cache(
            image,
            home_input_stack=True,
            hide_output=True,
        )

    def _update_preview_cache(
        self,
        image: np.ndarray,
        *,
        home_input_stack: bool,
        hide_output: bool,
    ) -> None:
        state = collect_gui_state(widgets=self._widgets)
        preview_image = self._resize_for_preview(image, max_size=state.display.preview_max_size)
        preview_display_image = self._prepare_input_color_preview_image(
            preview_image,
            input_color_space=state.input_image.input_color_space,
            apply_cctf_decoding=state.input_image.apply_cctf_decoding,
        )
        self._current_input_image = image
        self._current_preview_image = preview_image
        self._layers.set_or_add_input_preview_layer(
            preview_display_image,
            watermark_source_size=tuple(int(dimension) for dimension in image.shape[:2]),
            white_padding=state.display.white_padding,
            hide_output=hide_output,
            set_active=home_input_stack or self._output_layer() is None,
        )
        if home_input_stack:
            self._home_input_stack()

    def _sync_white_border(self, *, white_padding: float) -> None:
        self._layers.sync_white_border(white_padding=white_padding)

    def _home_input_stack(self) -> None:
        if self._white_border_layer() is None:
            return
        reset_viewer_camera(self._viewer)
        self._set_active_layer(self._white_border_layer())

    def _simulation_input_image(self, *, source_layer_name: str) -> np.ndarray | None:
        if source_layer_name == INPUT_PREVIEW_LAYER_NAME:
            return self._current_preview_image
        if source_layer_name == INPUT_LAYER_NAME:
            return self._current_input_image
        return None

    def _auto_preview_enabled(self) -> bool:
        simulation_section = getattr(self._widgets, 'simulation', None)
        auto_preview_value = getattr(simulation_section, 'auto_preview_value', None)
        return bool(auto_preview_value()) if callable(auto_preview_value) else False

    def _run_scheduled_auto_preview(self) -> None:
        self._auto_preview_scheduled = False
        if not self._auto_preview_enabled() or self._current_preview_image is None:
            self._pending_auto_preview = False
            return
        if self._active_simulation_worker is not None:
            self._pending_auto_preview = True
            return
        self._run_preview(report_status=False)

    def _replay_pending_auto_preview(self) -> None:
        if not self._pending_auto_preview:
            return
        self._pending_auto_preview = False
        self.request_auto_preview()

    def _output_layer(self) -> NapariImageLayer | None:
        return self._layers.output_layer()

    def _set_active_layer(self, layer: NapariImageLayer | None) -> None:
        self._layers.set_active_layer(layer)

    def _output_layer_float_data(self) -> np.ndarray | None:
        output_layer = self._output_layer()
        if output_layer is None:
            return None
        float_data = output_layer.metadata.get(OUTPUT_FLOAT_DATA_KEY)
        if float_data is None:
            return None
        return np.asarray(float_data)

    def _output_layer_render_settings(
        self,
        *,
        default_color_space: str,
        default_cctf_encoding: bool,
    ) -> tuple[str, bool]:
        output_layer = self._output_layer()
        if output_layer is None:
            return default_color_space, default_cctf_encoding
        color_space = output_layer.metadata.get(OUTPUT_COLOR_SPACE_KEY, default_color_space)
        cctf_encoding = output_layer.metadata.get(OUTPUT_CCTF_ENCODING_KEY, default_cctf_encoding)
        return str(color_space), bool(cctf_encoding)

    def _output_interpolation_mode(self) -> str:
        display_section = getattr(self._widgets, 'display', None)
        editor = getattr(display_section, 'output_interpolation', None)
        value = getattr(editor, 'value', None)
        if isinstance(value, str) and value:
            return value
        current_text = getattr(editor, 'currentText', None)
        if callable(current_text):
            text = current_text()
            if isinstance(text, str) and text:
                return text
        return 'spline36'

    @staticmethod
    def _resize_for_preview(image_data: np.ndarray, *, max_size: int) -> np.ndarray:
        return resize_for_preview(image_data, max_size)

    @staticmethod
    def _prepare_input_color_preview_image(
        image_data: np.ndarray,
        *,
        input_color_space: str,
        apply_cctf_decoding: bool,
    ) -> np.ndarray:
        return runtime.prepare_input_color_preview_image(
            image_data,
            input_color_space=input_color_space,
            apply_cctf_decoding=apply_cctf_decoding,
            colour_module=colour,
        )

    @staticmethod
    def _prepare_output_display_image(
        image_data: np.ndarray,
        *,
        output_color_space: str,
        use_display_transform: bool,
        padding_pixels: float = 0.0,
    ) -> tuple[np.ndarray, str]:
        return runtime.prepare_output_display_image(
            image_data,
            output_color_space=output_color_space,
            use_display_transform=use_display_transform,
            padding_pixels=padding_pixels,
            imagecms_module=ImageCms,
            colour_module=colour,
            pil_image_module=PILImage,
        )

    def _process_image_with_runtime(self, image_data: np.ndarray, params) -> np.ndarray:
        apply_stocks_specifics = (
            self._runtime_simulator is None
            or self._next_runtime_digest_applies_stock_specifics
        )
        digested_params = digest_params(
            params,
            apply_stocks_specifics=apply_stocks_specifics,
        )

        # 全分辨率模式（preview_mode=False）走缓存路径
        settings = getattr(digested_params, 'settings', None)
        is_preview = getattr(settings, 'preview_mode', True) if settings else True
        if not is_preview and self._current_input_image is not None:
            try:
                state = collect_gui_state(widgets=self._widgets)
                result = self._run_full_scan_with_cache(state, self._current_input_image)
                self._next_runtime_digest_applies_stock_specifics = False
                return result
            except Exception:
                pass  # fallback to original path

        try:
            if self._runtime_simulator is None:
                self._runtime_simulator = runtime_simulator(digested_params)
            else:
                self._runtime_simulator.update_params(digested_params)
            self._next_runtime_digest_applies_stock_specifics = False
            return self._runtime_simulator.process(image_data)
        except Exception:
            self._runtime_simulator = None
            raise

    def _set_display_transform_checked(self, enabled: bool) -> None:
        display_section = getattr(self._widgets, 'display', None)
        toggle = getattr(display_section, 'use_display_transform', None)
        if toggle is None:
            return

        block_signals = getattr(toggle, 'blockSignals', None)
        set_checked = getattr(toggle, 'setChecked', None)
        if not callable(set_checked):
            return

        previous_block_state = None
        if callable(block_signals):
            previous_block_state = block_signals(True)
        try:
            set_checked(enabled)
        finally:
            if callable(block_signals):
                block_signals(bool(previous_block_state))

    def _sync_canvas_background(self) -> None:
        display_section = getattr(self._widgets, 'display', None)
        toggle = getattr(display_section, 'gray_18_canvas', None)
        is_checked = getattr(toggle, 'isChecked', None)
        self.set_gray_18_canvas_enabled(bool(is_checked()) if callable(is_checked) else False)

    def _execute_simulation_request(self, request: SimulationRequest) -> SimulationResult:
        return runtime.execute_simulation_request(
            request,
            run_simulation_fn=self._process_image_with_runtime,
            prepare_output_display_image_fn=self._prepare_output_display_image,
        )

    @staticmethod
    def _configure_simulation_params(params, *, source_layer_name: str):
        settings = getattr(params, 'settings', None)
        if settings is not None and hasattr(settings, 'preview_mode'):
            settings.preview_mode = source_layer_name == INPUT_PREVIEW_LAYER_NAME
        return params

    def _start_simulation(self, *, source_layer_name: str, mode_label: str, report_status: bool = True) -> None:
        if self._active_simulation_worker is not None:
            set_status(self._viewer, '正在生成胶片效果，请稍候')
            return

        image_data = self._simulation_input_image(source_layer_name=source_layer_name)
        if image_data is None:
            QMessageBox.warning(dialog_parent(self._viewer), '运行模拟', '请先加载输入图像，再运行模拟。')
            return

        state = collect_gui_state(widgets=self._widgets)
        self._sync_white_border(white_padding=state.display.white_padding)
        params = self._configure_simulation_params(
            build_params_from_state(state),
            source_layer_name=source_layer_name,
        )

        image = np.double(image_data)
        request = SimulationRequest(
            mode_label=mode_label,
            image=image,
            params=params,
            output_color_space=state.simulation.output_color_space,
            use_display_transform=state.display.use_display_transform,
        )

        worker = runtime.SimulationWorker(request, execute_request=self._execute_simulation_request)
        worker.signals.finished.connect(self._on_simulation_finished)
        worker.signals.failed.connect(self._on_simulation_failed)
        self._active_simulation_worker = worker
        self._active_simulation_label = mode_label
        self._active_simulation_reports_status = report_status
        self._set_simulation_controls_enabled(False)
        if report_status:
            set_status(self._viewer, f'正在{mode_label.lower()}，图像越大耗时越长，请稍候...', timeout_ms=0)
        self._thread_pool.start(worker)

    def _on_simulation_finished(self, result: SimulationResult) -> None:
        report_status = self._active_simulation_reports_status
        is_preview = result.mode_label == '预览'
        self._active_simulation_worker = None
        self._active_simulation_label = None
        self._active_simulation_reports_status = True
        self._set_simulation_controls_enabled(True)

        self._set_or_add_output_layer(
            result.display_image,
            float_image=result.float_image,
            output_color_space=result.output_color_space,
            output_cctf_encoding=True,
            use_display_transform=result.use_display_transform,
            is_full_resolution=not is_preview,
        )

        if report_status:
            if not is_preview:
                # 全分辨率扫描完成，提示用户
                set_status(self._viewer, '全分辨率扫描完成。调其他参数会切回预览模式（颗粒仅在最终保存时生效）。')
            else:
                set_status(self._viewer, f'{result.mode_label}完成。{result.status_message}')
        self._replay_pending_auto_preview()

    def _on_simulation_failed(self, message: str) -> None:
        self._active_simulation_worker = None
        mode_label = self._active_simulation_label or '模拟'
        self._active_simulation_label = None
        self._active_simulation_reports_status = True
        self._set_simulation_controls_enabled(True)
        QMessageBox.critical(dialog_parent(self._viewer), '运行模拟', f'模拟失败.\n\n{message}')
        set_status(self._viewer, f'{mode_label}失败')
        self._replay_pending_auto_preview()

    def _set_simulation_controls_enabled(self, enabled: bool) -> None:
        simulation_section = getattr(self._widgets, 'simulation', None)
        if simulation_section is None:
            return
        for button_name in ('preview_button', 'scan_button', 'save_button'):
            button = getattr(simulation_section, button_name, None)
            set_enabled = getattr(button, 'setEnabled', None)
            if callable(set_enabled):
                set_enabled(enabled)

    def _run_simulation(self, *, source_layer_name: str) -> None:
        image_data = self._simulation_input_image(source_layer_name=source_layer_name)
        if image_data is None:
            QMessageBox.warning(dialog_parent(self._viewer), '运行模拟', '请先加载输入图像，再运行模拟。')
            return

        state = collect_gui_state(widgets=self._widgets)
        self._sync_white_border(white_padding=state.display.white_padding)
        params = self._configure_simulation_params(
            build_params_from_state(state),
            source_layer_name=source_layer_name,
        )

        image = np.double(image_data)
        scan = self._process_image_with_runtime(image, params)
        scan_display, display_status = self._prepare_output_display_image(
            scan,
            output_color_space=state.simulation.output_color_space,
            use_display_transform=state.display.use_display_transform,
        )
        self._set_or_add_output_layer(
            scan_display,
            float_image=scan,
            output_color_space=state.simulation.output_color_space,
            output_cctf_encoding=True,
            use_display_transform=state.display.use_display_transform,
        )
        set_status(self._viewer, display_status)
