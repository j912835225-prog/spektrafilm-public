"""
颗粒裁剪预览控制器。

完全独立于主扫描流程：
- 不读写主扫描缓存
- 不更新主视图 output layer
- 不依赖 GuiController 的内部状态
- 唯一的外部依赖：get_input_image()、get_gui_state()、is_main_scan_running()
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import numpy as np
from qtpy import QtCore

from spektrafilm_gui import controller_runtime as runtime
from spektrafilm_gui.params_mapper import build_params_from_state

if TYPE_CHECKING:
    from spektrafilm_gui.widget_sections import GrainCropPreviewWidget

QTimer = getattr(QtCore, 'QTimer')
QThreadPool = getattr(QtCore, 'QThreadPool')


def _run_grain_crop(
    crop: np.ndarray,
    params: object,
    output_color_space: str,
    use_display_transform: bool,
    prepare_display_fn: Callable,
) -> runtime.SimulationResult:
    """纯函数：跑裁剪块，返回 SimulationResult。不依赖任何外部状态。"""
    from importlib import import_module
    digest_params = import_module('spektrafilm.runtime.params_builder').digest_params
    Simulator = import_module('spektrafilm.runtime.process').Simulator

    digested = digest_params(params, apply_stocks_specifics=True)
    sim = Simulator(digested)
    scan = np.asarray(sim.process(crop), dtype=np.float32)
    display_image, display_status = prepare_display_fn(
        scan,
        output_color_space=output_color_space,
        use_display_transform=use_display_transform,
    )
    return runtime.SimulationResult(
        mode_label='颗粒预览',
        display_image=display_image,
        float_image=scan,
        output_color_space=output_color_space,
        use_display_transform=use_display_transform,
        status_message=display_status,
    )


class GrainCropPreviewController:
    """
    颗粒裁剪预览的全部逻辑。

    GuiController 持有一个实例，通过三个回调注入依赖：
      get_input_image   → 返回当前原图（或 None）
      get_gui_state     → 返回当前 GUI 状态
      is_main_scanning  → 返回主扫描是否正在运行
    """

    CROP_SIZE_PX = 300

    def __init__(
        self,
        *,
        preview_widget: GrainCropPreviewWidget,
        get_input_image: Callable[[], np.ndarray | None],
        get_gui_state: Callable,
        is_main_scanning: Callable[[], bool],
        prepare_display_fn: Callable,
        thread_pool: QThreadPool | None = None,
    ) -> None:
        self._widget = preview_widget
        self._get_input_image = get_input_image
        self._get_gui_state = get_gui_state
        self._is_main_scanning = is_main_scanning
        self._prepare_display_fn = prepare_display_fn
        self._thread_pool = thread_pool or QThreadPool.globalInstance()

        self._crop_center: tuple[float, float] = (0.5, 0.5)
        self._scheduled = False
        self._worker: runtime.SimulationWorker | None = None
        self._alt_click_filter: object | None = None  # 持有引用防止 GC
        self._mouse_callback: Callable | None = None  # 同上，napari layer callback
        self._layer_inserted_callback: Callable | None = None  # 同上，layer 添加监听

    # ── 公开接口 ──────────────────────────────────────────────────────────────

    def set_crop_center(self, cx: float, cy: float) -> None:
        self._crop_center = (max(0.0, min(1.0, cx)), max(0.0, min(1.0, cy)))

    def request(self, *_args) -> None:
        """debounce 800ms 后触发预览（颗粒参数改变时调用）。"""
        if self._get_input_image() is None:
            return
        if self._scheduled:
            return
        self._scheduled = True
        QTimer.singleShot(800, self._run)

    def trigger_now(self) -> None:
        """立刻触发预览（Option+点击后调用）。"""
        self._scheduled = False
        QTimer.singleShot(0, self._run)

    def reset(self) -> None:
        """加载新图片时重置状态。"""
        self._crop_center = (0.5, 0.5)
        self._scheduled = False
        self._widget.clear()

    def install_canvas_filter(self, viewer: object) -> None:
        """Alt+点击精确定位（按 napari 官方 pattern）：
        - 注册到 `viewer.mouse_drag_callbacks`（不是 layer 上，避开注册时机问题）
        - 用 `event.position`（world 坐标）+ `layer.world_to_data` 反算到 layer 像素
        - 参考：napari 官方 examples/custom_mouse_functions.py
        - 失败时退回 Qt eventFilter（精度差，仅作兜底）
        """
        from spektrafilm_gui.controller_layers import (
            INPUT_LAYER_NAME,
            INPUT_PREVIEW_LAYER_NAME,
        )

        controller = self
        target_names = (INPUT_PREVIEW_LAYER_NAME, INPUT_LAYER_NAME)

        def _resolve_target_layer():
            try:
                layers = viewer.layers
            except Exception:
                return None
            # 优先 input_preview（用户看到的那张），其次 input
            for name in target_names:
                for layer in layers:
                    if getattr(layer, 'name', None) == name:
                        return layer
            return None

        def _on_drag(view, event):
            modifiers = getattr(event, 'modifiers', None) or ()
            if 'Alt' not in modifiers:
                return
            if controller._get_input_image() is None:
                return
            world = getattr(event, 'position', None)
            if world is None:
                return
            layer = _resolve_target_layer()
            if layer is None:
                return
            try:
                data_pos = layer.world_to_data(world)
            except Exception:
                return
            try:
                y_data = float(data_pos[-2])
                x_data = float(data_pos[-1])
            except (TypeError, ValueError, IndexError):
                return
            # 关键：归一化分母是 layer 自己的数据形状，不是全分辨率原图。
            # input_preview layer 显示的是降采样后的图（preview_max_size），
            # world_to_data 给出的是该 layer 数据空间像素索引。
            try:
                layer_data = np.asarray(layer.data)
                lh, lw = int(layer_data.shape[0]), int(layer_data.shape[1])
            except Exception:
                return
            if lw <= 0 or lh <= 0:
                return
            cx = max(0.0, min(1.0, x_data / lw))
            cy = max(0.0, min(1.0, y_data / lh))
            controller.set_crop_center(cx, cy)
            controller.trigger_now()

        # 持引用防 GC
        self._mouse_callback = _on_drag

        registered = False
        try:
            viewer.mouse_drag_callbacks.append(_on_drag)
            registered = True
        except Exception:
            pass

        if registered:
            return

        # Fallback：viewer 接口不可用时退回 Qt eventFilter（canvas 像素归一化，
        # 精度受 zoom/pan 影响，仅兜底）
        class _AltClickFilter(QtCore.QObject):
            def eventFilter(self, obj, event):
                if event.type() != QtCore.QEvent.MouseButtonPress:
                    return False
                if not (event.modifiers() & QtCore.Qt.AltModifier):
                    return False
                if controller._get_input_image() is None:
                    return False
                try:
                    pos = event.pos()
                    w_canvas, h_canvas = obj.width(), obj.height()
                    if w_canvas <= 0 or h_canvas <= 0:
                        return False
                    cx = max(0.0, min(1.0, pos.x() / w_canvas))
                    cy = max(0.0, min(1.0, pos.y() / h_canvas))
                except Exception:
                    return False
                controller.set_crop_center(cx, cy)
                controller.trigger_now()
                return True

        try:
            native_canvas = viewer.window._qt_viewer.canvas.native
            self._alt_click_filter = _AltClickFilter(native_canvas)
            native_canvas.installEventFilter(self._alt_click_filter)
        except Exception:
            pass

    # ── 内部实现 ──────────────────────────────────────────────────────────────

    def _run(self) -> None:
        self._scheduled = False
        input_image = self._get_input_image()
        if input_image is None:
            return
        if self._is_main_scanning():
            return
        if self._worker is not None:
            return

        state = self._get_gui_state()
        h, w = input_image.shape[:2]
        cx = int(self._crop_center[0] * w)
        cy = int(self._crop_center[1] * h)
        half = self.CROP_SIZE_PX // 2
        x0 = max(0, cx - half)
        y0 = max(0, cy - half)
        x1 = min(w, x0 + self.CROP_SIZE_PX)
        y1 = min(h, y0 + self.CROP_SIZE_PX)
        x0 = max(0, x1 - self.CROP_SIZE_PX)
        y0 = max(0, y1 - self.CROP_SIZE_PX)

        crop = np.asarray(input_image[y0:y1, x0:x1], dtype=np.float64)
        if crop.size == 0:
            return

        params = build_params_from_state(state)
        params.settings.preview_mode = False  # 颗粒在 preview_mode=True 时被强制关闭

        request = runtime.SimulationRequest(
            mode_label='颗粒预览',
            image=np.double(crop),
            params=params,
            output_color_space=state.simulation.output_color_space,
            use_display_transform=state.display.use_display_transform,
        )

        worker = runtime.SimulationWorker(request, execute_request=self._execute_request)
        worker.signals.finished.connect(self._on_finished)
        worker.signals.failed.connect(self._on_failed)
        self._worker = worker
        self._thread_pool.start(worker)
        # 显示采样区域 + 归一化中心，便于核对是否点到了正确位置
        cx_pct = self._crop_center[0] * 100.0
        cy_pct = self._crop_center[1] * 100.0
        self._widget.set_status(
            f'计算中… 区域 ({x0},{y0})–({x1},{y1}) | 中心 {cx_pct:.0f}%×{cy_pct:.0f}% | 原图 {w}×{h}'
        )

    def _execute_request(self, request: runtime.SimulationRequest) -> runtime.SimulationResult:
        return _run_grain_crop(
            crop=request.image,
            params=request.params,
            output_color_space=request.output_color_space,
            use_display_transform=request.use_display_transform,
            prepare_display_fn=self._prepare_display_fn,
        )

    def _on_finished(self, result: runtime.SimulationResult) -> None:
        self._worker = None
        img = np.asarray(result.display_image)
        if img.ndim == 2:
            img = np.stack([img] * 3, axis=-1)
        self._widget.set_image(img)
        self._widget.set_status('⌥ Option+点击主视图选择查看区域')

    def _on_failed(self, message: str) -> None:
        self._worker = None
        self._widget.set_status(f'预览失败：{message[:60]}')
