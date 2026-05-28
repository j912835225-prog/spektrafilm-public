from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

from qtpy import QtCore, QtWidgets

QFileDialog = QtWidgets.QFileDialog
QFormLayout = QtWidgets.QFormLayout
QHBoxLayout = QtWidgets.QHBoxLayout
QLabel = QtWidgets.QLabel
QLineEdit = QtWidgets.QLineEdit
QPushButton = QtWidgets.QPushButton
QSizePolicy = QtWidgets.QSizePolicy
QVBoxLayout = QtWidgets.QVBoxLayout
QWidget = QtWidgets.QWidget
Qt = QtCore.Qt
Signal = QtCore.Signal

from spektrafilm_gui.state import (
    CouplersState,
    DisplayState,
    GlareState,
    GrainState,
    HalationState,
    InputImageState,
    LoadRawState,
    PreflashingState,
    SimulationState,
    SpecialState,
)
from spektrafilm_gui.persistence import load_dialog_dir, save_dialog_dir
from spektrafilm_gui.theme_palette import SIZE_FOOTER_ITEM_SPACING
from spektrafilm_gui.widget_editors import BoolEditor, EnumEditor, FloatEditor, FloatTupleEditor, IntEditor, IntTupleEditor, ProfileEnumEditor, SliderFloatEditor
from spektrafilm_gui.widget_primitives import CollapsibleSection, normalize_ui_text as _normalize_ui_text
from spektrafilm_gui.widget_specs import GUI_SECTION_ENUMS, get_auxiliary_spec, get_button_spec, get_widget_spec
from spektrafilm_gui.file_formats import RAW_EXTS


def _enum_values(enum_cls):
    return [member.value for member in enum_cls]


def _build_collapsible_form_section(
    title: str,
    form: QFormLayout,
    *,
    expanded: bool,
) -> QVBoxLayout:
    content = QWidget()
    content.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
    content.setLayout(form)

    root = QVBoxLayout()
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)
    root.addWidget(CollapsibleSection(title, content, expanded=expanded))
    return root


def _new_form_layout() -> QFormLayout:
    form = QFormLayout()
    form.setContentsMargins(0, 0, 0, 0)
    form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    form.setFormAlignment(Qt.AlignTop | Qt.AlignLeft)
    return form


def _add_form_rows(form: QFormLayout, rows: list[tuple[str | QLabel, QWidget]]) -> None:
    for label, widget in rows:
        if isinstance(label, str):
            label = _normalize_ui_text(label)
        form.addRow(label, widget)


def _build_linked_form_section(
    title: str,
    rows: list[tuple[str | QLabel, QWidget]],
    *,
    expanded: bool,
) -> QVBoxLayout:
    form = _new_form_layout()
    _add_form_rows(form, rows)
    return _build_collapsible_form_section(title, form, expanded=expanded)


def _build_button(
    text: str,
    callback: Any,
    *,
    tooltip: str | None = None,
    preserve_case: bool = False,
    role: str | None = None,
) -> QPushButton:
    button = QPushButton(text if preserve_case else _normalize_ui_text(text))
    if role is not None:
        button.setProperty('role', role)
    if tooltip:
        button.setToolTip(tooltip)
    button.clicked.connect(callback)
    return button


def _build_widget_label(section_name: str, field_name: str) -> QLabel:
    spec = get_widget_spec(section_name, field_name)
    label_text = spec.label or _format_label(field_name)
    label = QLabel(_normalize_ui_text(label_text))
    if spec.tooltip:
        label.setToolTip(spec.tooltip)
    return label


def _build_auxiliary_label(name: str) -> QLabel:
    spec = get_auxiliary_spec(name)
    label_text = spec.label or name.replace("_", " ")
    label = QLabel(_normalize_ui_text(label_text))
    if spec.tooltip:
        label.setToolTip(spec.tooltip)
    return label


def _spec_row(section_name: str, field_name: str, widget: QWidget) -> tuple[QLabel, QWidget]:
    return _build_widget_label(section_name, field_name), widget


def _compound_spec_row(section_name: str, label_field_name: str, *widgets: QWidget) -> tuple[QLabel, QWidget]:
    return _build_widget_label(section_name, label_field_name), _build_inline_container(*widgets, stretch_last=True)


def _build_button_row(*widgets: QWidget, stretch: int | None = None, spacing: int = 6) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(spacing)
    for widget in widgets:
        if stretch is None:
            row.addWidget(widget)
        else:
            row.addWidget(widget, stretch)
    return row


def _build_inline_container(
    *widgets: QWidget,
    spacing: int = 6,
    add_stretch: bool = False,
    stretch_last: bool = False,
) -> QWidget:
    container = QWidget()
    container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(spacing)
    last_widget_index = len(widgets) - 1
    for index, widget in enumerate(widgets):
        if stretch_last and index == last_widget_index:
            size_policy = widget.sizePolicy()
            size_policy.setHorizontalPolicy(QSizePolicy.Expanding)
            widget.setSizePolicy(size_policy)
            layout.addWidget(widget, 1)
        else:
            layout.addWidget(widget)
    if add_stretch and not stretch_last:
        layout.addStretch(1)
    return container


def _build_vertical_container(*items: QHBoxLayout | QFormLayout | QWidget, spacing: int = 6) -> QWidget:
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(spacing)
    layout.setAlignment(Qt.AlignTop)
    for item in items:
        if isinstance(item, QWidget):
            layout.addWidget(item)
        else:
            layout.addLayout(item)
    return container


def _set_single_collapsible_layout(widget: QWidget, title: str, content: QWidget, *, expanded: bool = True) -> None:
    root = QVBoxLayout()
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)
    root.addWidget(CollapsibleSection(_normalize_ui_text(title), content, expanded=expanded))
    widget.setLayout(root)


def _format_label(field_name: str) -> str:
    return _normalize_ui_text(field_name.replace("_", " "))


class DataclassSection(QWidget):
    def __init__(
        self,
        *,
        state_cls: type[Any],
        section_name: str,
        title: str,
        enum_fields: dict[str, type[Any]] | None = None,
        hidden_fields: set[str] | None = None,
        collapsed_by_default: bool = False,
        section_tooltip: str | None = None,
    ):
        super().__init__()
        self._state_cls = state_cls
        self._section_name = section_name
        self._title = title
        self._section_tooltip = section_tooltip
        self._enum_fields = enum_fields or {}
        self._hidden_fields = hidden_fields or set()
        self._collapsed_by_default = collapsed_by_default
        self._type_hints = get_type_hints(state_cls)
        self._init_extra_widgets()
        self._build_ui()
        self._apply_specs()

    def _init_extra_widgets(self) -> None:
        return

    def _build_ui(self) -> None:
        form = _new_form_layout()
        self._add_extra_rows_before(form)
        for field_info in fields(self._state_cls):
            field_name = field_info.name
            annotation = self._type_hints[field_name]
            widget = self._build_editor(field_name, annotation)
            setattr(self, field_name, widget)
            if field_name not in self._hidden_fields:
                form.addRow(_build_widget_label(self._section_name, field_name), self._row_widget(field_name, widget))
        self._add_extra_rows_after(form)

        content = QWidget()
        content.setLayout(form)

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(CollapsibleSection(self._title, content, expanded=not self._collapsed_by_default, tooltip=self._section_tooltip))
        self.setLayout(root)

    def _add_extra_rows_before(self, form: QFormLayout) -> None:
        del form
        return

    def _add_extra_rows_after(self, form: QFormLayout) -> None:
        del form
        return

    def _row_widget(self, field_name: str, widget: QWidget) -> QWidget:
        del field_name
        return widget

    def _build_editor(self, field_name: str, annotation: Any) -> QWidget:
        spec = get_widget_spec(self._section_name, field_name)
        enum_cls = self._enum_fields.get(field_name)
        if enum_cls is not None:
            if self._section_name == 'simulation' and field_name in {'film_stock', 'print_paper'}:
                return ProfileEnumEditor(_enum_values(enum_cls))
            return EnumEditor(_enum_values(enum_cls))
        if annotation is bool:
            return BoolEditor()
        if annotation is int:
            return IntEditor()
        if annotation is float:
            # 有 min/max/step 的浮点参数用滑块，否则用普通输入框
            if spec.min_value is not None and spec.max_value is not None and spec.step is not None:
                dec = 2 if spec.decimals is None else spec.decimals
                slider_editor = SliderFloatEditor(
                    minimum=spec.min_value,
                    maximum=spec.max_value,
                    step=spec.step,
                    decimals=dec,
                )
                # 默认值将在 set_state 时记录，这里先记录 spec 中点作为占位
                return slider_editor
            return FloatEditor(decimals=2 if spec.decimals is None else spec.decimals)
        if get_origin(annotation) is tuple:
            element_types = get_args(annotation)
            if element_types and all(element_type is int for element_type in element_types):
                return IntTupleEditor(len(element_types))
            return FloatTupleEditor(len(element_types), decimals=2 if spec.decimals is None else spec.decimals)
        raise TypeError(f"Unsupported field type for {self._state_cls.__name__}.{field_name}: {annotation!r}")

    def _apply_specs(self) -> None:
        for field_info in fields(self._state_cls):
            field_name = field_info.name
            spec = get_widget_spec(self._section_name, field_name)
            widget = getattr(self, field_name)
            if spec.tooltip:
                widget.setToolTip(spec.tooltip)
            if spec.min_value is not None:
                self._apply_numeric_attr(widget, 'setMinimum', spec.min_value)
            if spec.max_value is not None:
                self._apply_numeric_attr(widget, 'setMaximum', spec.max_value)
            if spec.step is not None:
                self._apply_numeric_attr(widget, 'setSingleStep', spec.step)
            # SliderFloatEditor：把当前值记为默认值（此时已是 profile 加载后的值）
            if hasattr(widget, 'set_default_value'):
                try:
                    widget.set_default_value(float(widget.value))
                except (TypeError, ValueError):
                    pass

    @staticmethod
    def _apply_numeric_attr(widget: QWidget, method_name: str, value: float | int) -> None:
        method = getattr(widget, method_name, None)
        if callable(method):
            method(value)
            return
        editors = getattr(widget, '_editors', None)
        if editors is not None:
            for editor in editors:
                getattr(editor, method_name)(value)

    def set_state(self, state: Any) -> None:
        for field_info in fields(self._state_cls):
            field_name = field_info.name
            widget = getattr(self, field_name)
            val = getattr(state, field_name)
            widget.value = val
            # 记录默认值，供双击归零使用
            if hasattr(widget, 'set_default_value'):
                widget.set_default_value(float(val))

    def get_state(self) -> Any:
        values = {field_info.name: getattr(self, field_info.name).value for field_info in fields(self._state_cls)}
        return self._state_cls(**values)

    def _bind_toggle(self, toggle_field: str, controlled_fields: list[str]) -> None:
        """将一个布尔开关控件与它控制的参数控件绑定：开关关闭时，受控控件变灰不可用。"""
        toggle_widget = getattr(self, toggle_field, None)
        if toggle_widget is None:
            return

        def _update(checked: bool) -> None:
            for field in controlled_fields:
                w = getattr(self, field, None)
                if w is not None:
                    w.setEnabled(checked)

        toggle_widget.toggled.connect(_update)
        # 初始化状态
        _update(bool(toggle_widget.value))


class SimpleDataclassSection(DataclassSection):
    STATE_CLS: type[Any]
    SECTION_NAME: str
    TITLE: str
    SECTION_TOOLTIP: str | None = None
    COLLAPSED_BY_DEFAULT = True
    ENUM_FIELDS_KEY: str | None = None
    HIDDEN_FIELDS: set[str] = set()

    def __init__(self):
        super().__init__(
            state_cls=self.STATE_CLS,
            section_name=self.SECTION_NAME,
            title=self.TITLE,
            enum_fields=GUI_SECTION_ENUMS[self.ENUM_FIELDS_KEY] if self.ENUM_FIELDS_KEY is not None else None,
            hidden_fields=self.HIDDEN_FIELDS,
            collapsed_by_default=self.COLLAPSED_BY_DEFAULT,
            section_tooltip=self.SECTION_TOOLTIP,
        )
        self._setup_conditional_enables()

    def _setup_conditional_enables(self) -> None:
        """子类重写此方法，调用 _bind_toggle 设置开关与受控参数的联动。"""
        pass


class InputImageSection(SimpleDataclassSection):
    STATE_CLS = InputImageState
    SECTION_NAME = 'input_image'
    TITLE = '输入图像'
    ENUM_FIELDS_KEY = 'input_image'
    HIDDEN_FIELDS = {
        'upscale_factor',
        'crop',
        'crop_center',
        'crop_size',
        'spectral_upsampling_method',
        'apply_hanatos2025_adaptation_window',
        'apply_hanatos2025_adaptation_surface',
        'spectral_gaussian_blur',
        'filter_uv',
        'filter_ir',
    }

    def __init__(self, filepicker_section: 'FilePickerSection'):
        self._filepicker_section = filepicker_section
        super().__init__()


class LoadRawSection(DataclassSection):
    load_requested = Signal(str)

    def __init__(self):
        super().__init__(
            state_cls=LoadRawState,
            section_name='load_raw',
            title='RAW 参数（导入 RAW 后生效）',
            enum_fields=GUI_SECTION_ENUMS['load_raw'],
            collapsed_by_default=True,
        )

    def _init_extra_widgets(self) -> None:
        # 不再显示独立的文件选择器，文件通过上方"导入图像"统一导入
        self.reprocess_button = _build_button('重新处理 RAW', self._reprocess_raw, role='compactAction')
        self.reprocess_button.setEnabled(False)
        self._current_path: str = ''

    def _add_extra_rows_after(self, form: QFormLayout) -> None:
        form.addRow(self.reprocess_button)

    def _build_ui(self) -> None:
        super()._build_ui()
        # 白平衡切换时，动态 enable/disable 色温和色调
        self.white_balance.currentTextChanged.connect(self._on_white_balance_changed)
        self._on_white_balance_changed(self.white_balance.value)

    def _on_white_balance_changed(self, value: str) -> None:
        is_custom = (value == 'custom')
        self.temperature.setEnabled(is_custom)
        self.tint.setEnabled(is_custom)

    def _reprocess_raw(self) -> None:
        if not self._current_path:
            return
        self.load_requested.emit(self._current_path)

    def set_path(self, path: str) -> None:
        self._current_path = path
        self.reprocess_button.setEnabled(bool(path.strip()))


class PreviewCropSection(QWidget):
    def __init__(self, input_image_section: InputImageSection):
        super().__init__()
        self.setLayout(
            _build_linked_form_section(
                '裁剪与放大',
                [
                    _spec_row('input_image', 'upscale_factor', input_image_section.upscale_factor),
                    _spec_row('input_image', 'crop', input_image_section.crop),
                    _spec_row('input_image', 'crop_center', input_image_section.crop_center),
                    _spec_row('input_image', 'crop_size', input_image_section.crop_size),
                ],
                expanded=False,
            ),
        )
        # 裁剪开关关闭时，裁剪中心和裁剪尺寸变灰
        def _on_crop_changed(checked: bool) -> None:
            input_image_section.crop_center.setEnabled(checked)
            input_image_section.crop_size.setEnabled(checked)
        input_image_section.crop.toggled.connect(_on_crop_changed)
        _on_crop_changed(bool(input_image_section.crop.value))


class GrainSection(SimpleDataclassSection):
    STATE_CLS = GrainState
    SECTION_NAME = 'grain'
    TITLE = '颗粒'

    def _setup_conditional_enables(self) -> None:
        self._bind_toggle('active', [
            'sublayers_active', 'particle_area_um2', 'particle_scale',
            'particle_scale_layers', 'density_min', 'uniformity',
            'blur', 'blur_dye_clouds_um', 'micro_structure',
        ])
        self._bind_toggle('sublayers_active', ['particle_scale_layers'])


class PreflashingSection(SimpleDataclassSection):
    STATE_CLS = PreflashingState
    SECTION_NAME = 'preflashing'
    TITLE = '预闪'


class HalationSection(SimpleDataclassSection):
    STATE_CLS = HalationState
    SECTION_NAME = 'halation'
    TITLE = 'Halation（红光渗透）'

    def _setup_conditional_enables(self) -> None:
        self._bind_toggle('active', [
            'scatter_amount', 'scatter_spatial_scale', 'halation_amount', 'halation_spatial_scale',
            'boost_ev', 'protect_ev', 'boost_range',
            'scatter_core_um', 'scatter_tail_um', 'scatter_tail_weight',
            'halation_strength', 'halation_first_sigma_um',
            'halation_n_bounces', 'halation_bounce_decay', 'halation_renormalize',
        ])


class CouplersSection(SimpleDataclassSection):
    STATE_CLS = CouplersState
    SECTION_NAME = 'couplers'
    TITLE = 'DIR 耦合剂'
    SECTION_TOOLTIP = 'DIR 耦合剂（Dye Inhibitor Release）：胶片显影时各染料层之间的化学抑制效应，决定了不同胶片的色彩性格差异。切换胶片型号时自动加载对应数值，通常不需要手动调。'

    def _setup_conditional_enables(self) -> None:
        self._bind_toggle('active', [
            'amount', 'inhibition_samelayer', 'inhibition_interlayer',
            'gamma_samelayer_rgb', 'gamma_interlayer_r_to_gb',
            'gamma_interlayer_g_to_rb', 'gamma_interlayer_b_to_rg',
            'diffusion_size_um',
        ])


class GlareSection(SimpleDataclassSection):
    STATE_CLS = GlareState
    SECTION_NAME = 'glare'
    TITLE = '眩光'

    def _setup_conditional_enables(self) -> None:
        self._bind_toggle('active', ['percent', 'roughness', 'blur'])


class SpecialSection(DataclassSection):
    def __init__(self, simulation_section: 'SimulationSection'):
        self._simulation_section = simulation_section
        super().__init__(
            state_cls=SpecialState,
            section_name='special',
            title='实验性功能',
            collapsed_by_default=True,
            hidden_fields={
                'film_gamma_factor',
                'print_gamma_factor',
            },
        )

    def _add_extra_rows_before(self, form: QFormLayout) -> None:
        form.addRow(_build_widget_label('simulation', 'print_illuminant'), self._simulation_section.print_illuminant)


class SpectralUpsamplingSection(QWidget):
    def __init__(self, input_image_section: InputImageSection):
        super().__init__()
        self.setLayout(
            _build_linked_form_section(
                '光谱上采样',
                [
                    _spec_row('input_image', 'spectral_upsampling_method', input_image_section.spectral_upsampling_method),
                    _spec_row('input_image', 'apply_hanatos2025_adaptation_window', input_image_section.apply_hanatos2025_adaptation_window),
                    _spec_row('input_image', 'apply_hanatos2025_adaptation_surface', input_image_section.apply_hanatos2025_adaptation_surface),
                    _spec_row('input_image', 'spectral_gaussian_blur', input_image_section.spectral_gaussian_blur),
                    _spec_row('input_image', 'filter_uv', input_image_section.filter_uv),
                    _spec_row('input_image', 'filter_ir', input_image_section.filter_ir),
                ],
                expanded=False,
            ),
        )


class TuneSection(QWidget):
    def __init__(self, special_section: SpecialSection):
        super().__init__()
        self.setLayout(
            _build_linked_form_section(
                '微调',
                [
                    _spec_row('special', 'film_gamma_factor', special_section.film_gamma_factor),
                    _spec_row('special', 'print_gamma_factor', special_section.print_gamma_factor),
                ],
                expanded=True,
            ),
        )


# RAW 文件扩展名从 file_formats 导入（避免多处定义）
_RAW_EXTENSIONS = RAW_EXTS


class FilePickerSection(QWidget):
    """统一导入入口：自动识别 RAW 和 RGB，发出对应信号。"""
    load_rgb_requested = Signal(str)
    load_raw_requested = Signal(str)
    # 保留旧信号名兼容 controller
    load_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self) -> None:
        self.file_path = QLineEdit()
        self.file_path.setReadOnly(True)
        self.file_path.setPlaceholderText(_normalize_ui_text('拖入或点击选择图像 / RAW'))

        browse_button = _build_button('选择文件', self._choose_file, role='compactAction')
        content = _build_vertical_container(
            _build_button_row(self.file_path, browse_button, spacing=4),
            spacing=6,
        )
        _set_single_collapsible_layout(self, '导入图像', content)

    def _choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            _normalize_ui_text('选择图像或 RAW 文件'),
            load_dialog_dir('rgb_input'),
            '所有支持的格式 (*.jpg *.jpeg *.png *.tif *.tiff *.exr '
            '*.arw *.cr2 *.cr3 *.nef *.nrw *.orf *.rw2 *.pef *.dng *.raf *.raw *.3fr *.mef *.mrw *.x3f *.kdc *.dcr *.erf *.iiq *.mos *.sr2)'
            ';;RGB 图像 (*.jpg *.jpeg *.png *.tif *.tiff *.exr)'
            ';;RAW 文件 (*.arw *.cr2 *.cr3 *.nef *.nrw *.orf *.rw2 *.pef *.dng *.raf *.raw *.3fr *.mef *.mrw *.x3f *.kdc *.dcr *.erf *.iiq *.mos *.sr2)',
        )
        if not path:
            return
        save_dialog_dir('rgb_input', str(Path(path).parent))
        self._load_path(path)

    def _load_path(self, path: str) -> None:
        self.file_path.setText(path)
        ext = Path(path).suffix.lstrip('.').lower()
        if ext in _RAW_EXTENSIONS:
            self.load_raw_requested.emit(path)
        else:
            self.load_rgb_requested.emit(path)
            self.load_requested.emit(path)  # 兼容旧接口

    def set_path(self, path: str) -> None:
        self.file_path.setText(path)


class GuiConfigSection(QWidget):
    save_current_as_default_requested = Signal()
    save_current_to_file_requested = Signal()
    load_from_file_requested = Signal()
    restore_factory_default_requested = Signal()
    save_preset_requested = Signal()
    load_preset_requested = Signal()

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self) -> None:
        self.save_current_as_default_button = _build_button(
            '保存为默认设置',
            self.save_current_as_default_requested.emit,
        )
        self.save_current_to_file_button = _build_button(
            '保存到文件',
            self.save_current_to_file_requested.emit,
        )
        self.load_from_file_button = _build_button('从文件加载', self.load_from_file_requested.emit)
        self.restore_factory_default_button = _build_button(
            '恢复出厂默认',
            self.restore_factory_default_requested.emit,
        )
        self.save_preset_button = _build_button(
            '另存为预设',
            self.save_preset_requested.emit,
            tooltip='将当前参数保存为命名预设，可随时加载复用',
            role='compactAction',
        )
        self.load_preset_button = _build_button(
            '加载预设',
            self.load_preset_requested.emit,
            tooltip='从已保存的预设列表中选择并加载',
            role='compactAction',
        )

        content = _build_vertical_container(
            _build_button_row(self.save_current_as_default_button, self.save_current_to_file_button),
            _build_button_row(self.load_from_file_button, self.restore_factory_default_button),
            _build_button_row(self.save_preset_button, self.load_preset_button),
        )
        _set_single_collapsible_layout(self, 'GUI 参数', content, expanded=True)


class DisplaySection(SimpleDataclassSection):
    STATE_CLS = DisplayState
    SECTION_NAME = 'display'
    TITLE = '显示'
    COLLAPSED_BY_DEFAULT = False
    ENUM_FIELDS_KEY = 'display'
    HIDDEN_FIELDS = {'preview_max_size'}

    update_preview_requested = Signal()

    def _init_extra_widgets(self) -> None:
        self.update_preview_button = _build_button(
            'update',
            self.update_preview_requested.emit,
            preserve_case=True,
            role='compactAction',
        )
        self.update_preview_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

    def _add_extra_rows_after(self, form: QFormLayout) -> None:
        form.addRow(
            _build_widget_label('display', 'preview_max_size'),
            _build_vertical_container(
                _build_button_row(self.preview_max_size, self.update_preview_button, spacing=4),
                spacing=0,
            ),
        )


class SimulationSection(DataclassSection):
    preview_requested = Signal()
    scan_requested = Signal()
    save_requested = Signal()
    _glare_section: 'GlareSection | None'
    _scan_for_print_restore_state: dict[str, object] | None

    def __init__(self):
        super().__init__(
            state_cls=SimulationState,
            section_name='simulation',
            title='胶片与相纸',
            enum_fields=GUI_SECTION_ENUMS['simulation'],
            hidden_fields={
                'film_format_mm',
                'camera_lens_blur_um',
                'camera_diffusion_filter_active',
                'camera_diffusion_filter_family',
                'camera_diffusion_filter_strength',
                'camera_diffusion_filter_spatial_scale',
                'camera_diffusion_filter_halo_warmth',
                'camera_diffusion_filter_core_intensity',
                'camera_diffusion_filter_core_size',
                'camera_diffusion_filter_halo_intensity',
                'camera_diffusion_filter_halo_size',
                'camera_diffusion_filter_bloom_intensity',
                'camera_diffusion_filter_bloom_size',
                'exposure_compensation_ev',
                'auto_exposure',
                'auto_exposure_method',
                'print_exposure',
                'print_exposure_compensation',
                'print_y_filter_shift',
                'print_m_filter_shift',
                'diffusion_filter_active',
                'diffusion_filter_family',
                'diffusion_filter_strength',
                'diffusion_filter_spatial_scale',
                'diffusion_filter_halo_warmth',
                'diffusion_filter_core_intensity',
                'diffusion_filter_core_size',
                'diffusion_filter_halo_intensity',
                'diffusion_filter_halo_size',
                'diffusion_filter_bloom_intensity',
                'diffusion_filter_bloom_size',
                'print_illuminant',
                'scan_lens_blur',
                'scan_white_correction',
                'scan_white_level',
                'scan_black_correction',
                'scan_black_level',
                'scan_unsharp_mask',
                'auto_preview',
                'scan_film',
                'output_color_space',
                'saving_color_space',
                'saving_cctf_encoding',
            },
        )
        self._setup_simulation_conditional_enables()

    def _init_extra_widgets(self) -> None:
        self._glare_section = None
        self._scan_for_print_restore_state = None
        self.bottom_auto_preview = BoolEditor()
        self.bottom_scan_film = BoolEditor()
        self.bottom_scan_for_print = BoolEditor()
        scan_for_print_spec = get_auxiliary_spec('scan_for_print')
        if scan_for_print_spec.tooltip:
            self.bottom_scan_for_print.setToolTip(scan_for_print_spec.tooltip)
        self.bottom_scan_for_print.toggled.connect(self._apply_scan_for_print_mode)
        preview_button_spec = get_button_spec('preview')
        self.preview_button = _build_button(
            preview_button_spec.text,
            self.preview_requested.emit,
            tooltip=preview_button_spec.tooltip,
            preserve_case=preview_button_spec.preserve_case,
            role='accentAction',
        )
        scan_button_spec = get_button_spec('scan')
        self.scan_button = _build_button(
            scan_button_spec.text,
            self.scan_requested.emit,
            tooltip=scan_button_spec.tooltip,
            preserve_case=scan_button_spec.preserve_case,
            role='accentAction',
        )
        save_button_spec = get_button_spec('save')
        self.save_button = _build_button(
            save_button_spec.text,
            self.save_requested.emit,
            tooltip=save_button_spec.tooltip,
            preserve_case=save_button_spec.preserve_case,
            role='saveAction',
        )

        # 底部开关行：加分隔符和更清晰的标签
        scan_film_row = QHBoxLayout()
        scan_film_row.setContentsMargins(0, 0, 0, 0)
        scan_film_row.setSpacing(SIZE_FOOTER_ITEM_SPACING)

        auto_preview_label = _build_widget_label('simulation', 'auto_preview')
        auto_preview_label.setToolTip('参数改变后自动触发预览，方便实时查看效果')
        scan_film_row.addWidget(auto_preview_label)
        scan_film_row.addWidget(self.bottom_auto_preview)

        sep1 = QWidget(); sep1.setFixedWidth(1); sep1.setStyleSheet('background:#333;')
        scan_film_row.addSpacing(4)
        scan_film_row.addWidget(sep1)
        scan_film_row.addSpacing(4)

        scan_film_label = _build_widget_label('simulation', 'scan_film')
        scan_film_label.setToolTip('显示负片原始状态（橙色底片），用于研究胶片化学特性')
        scan_film_row.addWidget(scan_film_label)
        scan_film_row.addWidget(self.bottom_scan_film)

        sep2 = QWidget(); sep2.setFixedWidth(1); sep2.setStyleSheet('background:#333;')
        scan_film_row.addSpacing(4)
        scan_film_row.addWidget(sep2)
        scan_film_row.addSpacing(4)

        scan_for_print_label = _build_auxiliary_label('scan_for_print')
        scan_for_print_spec = get_auxiliary_spec('scan_for_print')
        if scan_for_print_spec.tooltip:
            scan_for_print_label.setToolTip(scan_for_print_spec.tooltip)
        scan_film_row.addWidget(scan_for_print_label)
        scan_film_row.addWidget(self.bottom_scan_for_print)
        scan_film_row.addStretch(1)

        # 操作按钮行：预览和扫描较小，保存突出
        preview_scan_container = QWidget()
        preview_scan_layout = _build_button_row(
            self.preview_button,
            self.scan_button,
            stretch=1,
            spacing=SIZE_FOOTER_ITEM_SPACING,
        )
        preview_scan_container.setLayout(preview_scan_layout)

        action_buttons = QWidget()
        action_layout = QHBoxLayout(action_buttons)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(SIZE_FOOTER_ITEM_SPACING)
        action_layout.addWidget(preview_scan_container, 2)
        action_layout.addWidget(self.save_button, 1)

        self.bottom_bar = QWidget()
        bottom_bar_layout = QVBoxLayout(self.bottom_bar)
        bottom_bar_layout.setContentsMargins(0, 0, 0, 0)
        bottom_bar_layout.setSpacing(SIZE_FOOTER_ITEM_SPACING)
        bottom_bar_layout.addLayout(scan_film_row)
        bottom_bar_layout.addWidget(action_buttons)

    def action_bar(self) -> QWidget:
        return self.bottom_bar

    def _setup_simulation_conditional_enables(self) -> None:
        """SimulationSection 里的开关联动。"""
        # 扫描白点/黑点校正
        self._bind_toggle('scan_white_correction', ['scan_white_level'])
        self._bind_toggle('scan_black_correction', ['scan_black_level'])
        # 相机柔光滤镜
        self._bind_toggle('camera_diffusion_filter_active', [
            'camera_diffusion_filter_family', 'camera_diffusion_filter_strength',
            'camera_diffusion_filter_spatial_scale', 'camera_diffusion_filter_halo_warmth',
            'camera_diffusion_filter_core_intensity', 'camera_diffusion_filter_core_size',
            'camera_diffusion_filter_halo_intensity', 'camera_diffusion_filter_halo_size',
            'camera_diffusion_filter_bloom_intensity', 'camera_diffusion_filter_bloom_size',
        ])
        # 印放柔光滤镜
        self._bind_toggle('diffusion_filter_active', [
            'diffusion_filter_family', 'diffusion_filter_strength',
            'diffusion_filter_spatial_scale', 'diffusion_filter_halo_warmth',
            'diffusion_filter_core_intensity', 'diffusion_filter_core_size',
            'diffusion_filter_halo_intensity', 'diffusion_filter_halo_size',
            'diffusion_filter_bloom_intensity', 'diffusion_filter_bloom_size',
        ])

    def set_auto_preview_value(self, value: bool) -> None:
        self.bottom_auto_preview.setChecked(value)

    def auto_preview_value(self) -> bool:
        return self.bottom_auto_preview.isChecked()

    def set_scan_film_value(self, value: bool) -> None:
        self.bottom_scan_film.setChecked(value)

    def scan_film_value(self) -> bool:
        return self.bottom_scan_film.isChecked()

    def bind_scan_for_print_glare_section(self, glare_section: 'GlareSection') -> None:
        self._glare_section = glare_section

    def reset_scan_for_print_value(self) -> None:
        was_blocked = self.bottom_scan_for_print.blockSignals(True)
        self.bottom_scan_for_print.setChecked(False)
        self.bottom_scan_for_print.blockSignals(was_blocked)
        self._scan_for_print_restore_state = None

    def _apply_scan_for_print_mode(self, active: bool) -> None:
        if active:
            if self._scan_for_print_restore_state is None:
                self._scan_for_print_restore_state = {
                    'scan_white_correction': self.scan_white_correction.value,
                    'scan_black_correction': self.scan_black_correction.value,
                    'glare_active': None if self._glare_section is None else self._glare_section.active.value,
                }
            self.scan_white_correction.value = True
            self.scan_black_correction.value = True
            if self._glare_section is not None:
                self._glare_section.active.value = False
            return

        restore_state = self._scan_for_print_restore_state
        if restore_state is None:
            return
        self.scan_white_correction.value = restore_state['scan_white_correction']
        self.scan_black_correction.value = restore_state['scan_black_correction']
        glare_active = restore_state['glare_active']
        if self._glare_section is not None and glare_active is not None:
            self._glare_section.active.value = glare_active
        self._scan_for_print_restore_state = None


class OutputSection(QWidget):
    def __init__(self, simulation_section: SimulationSection):
        super().__init__()
        self.setLayout(
            _build_linked_form_section(
                '输出',
                [
                    _spec_row('simulation', 'output_color_space', simulation_section.output_color_space),
                    _spec_row('simulation', 'saving_color_space', simulation_section.saving_color_space),
                    _spec_row('simulation', 'saving_cctf_encoding', simulation_section.saving_cctf_encoding),
                ],
                expanded=False,
            ),
        )


class ExposureControlSection(QWidget):
    def __init__(self, simulation_section: SimulationSection):
        super().__init__()
        form = _new_form_layout()
        self._add_spec_row(form, 'simulation', 'auto_exposure', simulation_section.auto_exposure)
        self._add_spec_row(form, 'simulation', 'exposure_compensation_ev', simulation_section.exposure_compensation_ev)
        self._add_spec_row(form, 'simulation', 'print_exposure_compensation', simulation_section.print_exposure_compensation)
        self._add_spec_row(form, 'simulation', 'print_exposure', simulation_section.print_exposure)

        self.setLayout(_build_collapsible_form_section('曝光控制', form, expanded=True))

    def _add_spec_row(self, form: QFormLayout, section_name: str, field_name: str, widget: QWidget) -> None:
        spec = get_widget_spec(section_name, field_name)
        if spec.tooltip:
            widget.setToolTip(spec.tooltip)
        form.addRow(_build_widget_label(section_name, field_name), widget)


class EnlargerSection(QWidget):
    def __init__(self, simulation_section: SimulationSection):
        super().__init__()
        self.setLayout(
            _build_linked_form_section(
                '印刷色调',
                [
                    _spec_row('simulation', 'print_y_filter_shift', simulation_section.print_y_filter_shift),
                    _spec_row('simulation', 'print_m_filter_shift', simulation_section.print_m_filter_shift),
                ],
                expanded=True,
            ),
        )


class DiffusionSection(QWidget):
    def __init__(self, simulation_section: SimulationSection):
        super().__init__()
        self.setLayout(
            _build_linked_form_section(
                '后期柔光',
                [
                    _spec_row('simulation', 'diffusion_filter_active', simulation_section.diffusion_filter_active),
                    _spec_row('simulation', 'diffusion_filter_family', simulation_section.diffusion_filter_family),
                    _spec_row('simulation', 'diffusion_filter_strength', simulation_section.diffusion_filter_strength),
                    _spec_row('simulation', 'diffusion_filter_spatial_scale', simulation_section.diffusion_filter_spatial_scale),
                    _spec_row('simulation', 'diffusion_filter_halo_warmth', simulation_section.diffusion_filter_halo_warmth),
                    _spec_row('simulation', 'diffusion_filter_core_intensity', simulation_section.diffusion_filter_core_intensity),
                    _spec_row('simulation', 'diffusion_filter_core_size', simulation_section.diffusion_filter_core_size),
                    _spec_row('simulation', 'diffusion_filter_halo_intensity', simulation_section.diffusion_filter_halo_intensity),
                    _spec_row('simulation', 'diffusion_filter_halo_size', simulation_section.diffusion_filter_halo_size),
                    _spec_row('simulation', 'diffusion_filter_bloom_intensity', simulation_section.diffusion_filter_bloom_intensity),
                    _spec_row('simulation', 'diffusion_filter_bloom_size', simulation_section.diffusion_filter_bloom_size),
                ],
                expanded=False,
            ),
        )


class CameraDiffusionSection(QWidget):
    def __init__(self, simulation_section: SimulationSection):
        super().__init__()
        self.setLayout(
            _build_linked_form_section(
                '前期柔光',
                [
                    _spec_row('simulation', 'camera_diffusion_filter_active', simulation_section.camera_diffusion_filter_active),
                    _spec_row('simulation', 'camera_diffusion_filter_family', simulation_section.camera_diffusion_filter_family),
                    _spec_row('simulation', 'camera_diffusion_filter_strength', simulation_section.camera_diffusion_filter_strength),
                    _spec_row('simulation', 'camera_diffusion_filter_spatial_scale', simulation_section.camera_diffusion_filter_spatial_scale),
                    _spec_row('simulation', 'camera_diffusion_filter_halo_warmth', simulation_section.camera_diffusion_filter_halo_warmth),
                    _spec_row('simulation', 'camera_diffusion_filter_core_intensity', simulation_section.camera_diffusion_filter_core_intensity),
                    _spec_row('simulation', 'camera_diffusion_filter_core_size', simulation_section.camera_diffusion_filter_core_size),
                    _spec_row('simulation', 'camera_diffusion_filter_halo_intensity', simulation_section.camera_diffusion_filter_halo_intensity),
                    _spec_row('simulation', 'camera_diffusion_filter_halo_size', simulation_section.camera_diffusion_filter_halo_size),
                    _spec_row('simulation', 'camera_diffusion_filter_bloom_intensity', simulation_section.camera_diffusion_filter_bloom_intensity),
                    _spec_row('simulation', 'camera_diffusion_filter_bloom_size', simulation_section.camera_diffusion_filter_bloom_size),
                ],
                expanded=False,
            ),
        )


class ScannerSection(QWidget):
    def __init__(self, simulation_section: SimulationSection):
        super().__init__()
        self.setLayout(
            _build_linked_form_section(
                '扫描仪',
                [
                    _spec_row('simulation', 'scan_lens_blur', simulation_section.scan_lens_blur),
                    _compound_spec_row(
                        'simulation',
                        'scan_white_correction',
                        simulation_section.scan_white_correction,
                        simulation_section.scan_white_level,
                    ),
                    _compound_spec_row(
                        'simulation',
                        'scan_black_correction',
                        simulation_section.scan_black_correction,
                        simulation_section.scan_black_level,
                    ),
                    _spec_row('simulation', 'scan_unsharp_mask', simulation_section.scan_unsharp_mask),
                ],
                expanded=False,
            ),
        )


class CameraSection(QWidget):
    def __init__(self, simulation_section: SimulationSection):
        super().__init__()
        self.setLayout(
            _build_linked_form_section(
                '相机',
                [
                    _spec_row('simulation', 'film_format_mm', simulation_section.film_format_mm),
                    _spec_row('simulation', 'auto_exposure_method', simulation_section.auto_exposure_method),
                    _spec_row('simulation', 'camera_lens_blur_um', simulation_section.camera_lens_blur_um),
                ],
                expanded=False,
            ),
        )

class PresetPanelSection(QWidget):
    """主面板顶部的预设面板。
    显示已保存的预设列表，点击直接应用，另存为预设。
    """
    preset_apply_requested = Signal(str)   # 传预设名称
    preset_save_requested = Signal()
    preset_delete_requested = Signal(str)  # 传预设名称

    _PRESETS_DIR = Path.home() / '.spektrafilm' / 'presets'

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self) -> None:
        # 预设列表
        self._list = QtWidgets.QListWidget()
        self._list.setFixedHeight(120)
        self._list.setStyleSheet("""
            QListWidget {
                background: #1a1a1a;
                border: 1px solid #2e2e2e;
                border-radius: 3px;
                color: #c0c0c0;
                font-size: 12px;
            }
            QListWidget::item { padding: 4px 8px; }
            QListWidget::item:selected { background: #2a2a1a; color: #c8a96e; }
            QListWidget::item:hover { background: #222; }
        """)
        self._list.itemDoubleClicked.connect(self._on_double_click)

        # 按钮行
        apply_btn = _build_button('应用', self._on_apply, role='accentAction', preserve_case=True)
        apply_btn.setToolTip('应用选中的预设')
        save_btn = _build_button('另存为预设', self.preset_save_requested.emit, role='compactAction', preserve_case=True)
        save_btn.setToolTip('将当前参数保存为新预设')
        delete_btn = _build_button('删除', self._on_delete, role='compactAction', preserve_case=True)
        delete_btn.setToolTip('删除选中的预设（不可恢复）')

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(4)
        btn_row.addWidget(apply_btn, 2)
        btn_row.addWidget(save_btn, 2)
        btn_row.addWidget(delete_btn, 1)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 4, 0, 0)
        content_layout.setSpacing(4)
        content_layout.addWidget(self._list)
        content_layout.addLayout(btn_row)

        _set_single_collapsible_layout(self, '预设', content, expanded=True)
        self.refresh()

    def refresh(self) -> None:
        """重新扫描预设目录，更新列表。"""
        self._list.clear()
        if not self._PRESETS_DIR.exists():
            return
        for p in sorted(self._PRESETS_DIR.glob('*.json')):
            self._list.addItem(p.stem)

    def _on_apply(self) -> None:
        item = self._list.currentItem()
        if item:
            self.preset_apply_requested.emit(item.text())

    def _on_double_click(self, item: QtWidgets.QListWidgetItem) -> None:
        self.preset_apply_requested.emit(item.text())

    def _on_delete(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        name = item.text()
        reply = QtWidgets.QMessageBox.question(
            self,
            '删除预设',
            f'确定删除预设 "{name}" 吗？此操作不可恢复。',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.preset_delete_requested.emit(name)


class GrainCropPreviewWidget(QWidget):
    """颗粒裁剪预览窗口。
    在主视图上 Alt+点击 任意区域，以该点为中心显示全分辨率颗粒效果。
    """
    # 裁剪区域尺寸（原图像素）
    CROP_SIZE_PX = 300

    def __init__(self):
        super().__init__()
        self._original_pixmap = None
        self._build_ui()

    def _build_ui(self) -> None:
        # 预览图像标签
        self._image_label = QtWidgets.QLabel()
        # 不固定尺寸：随父布局自适应宽度，最小高度保证可读
        self._image_label.setMinimumSize(420, 280)
        self._image_label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setStyleSheet("""
            QLabel {
                background: #111;
                border: 1px solid #333;
                border-radius: 3px;
                color: #555;
                font-size: 11px;
            }
        """)
        self._image_label.setText('在主视图上 Alt+点击 任意区域，查看该位置的真实颗粒效果')
        self._image_label.setWordWrap(True)

        self._status_label = QLabel('Alt+点击主视图选择查看区域')
        self._status_label.setStyleSheet('color: #555; font-size: 11px;')

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self._image_label)
        layout.addWidget(self._status_label)

    def set_image(self, image_rgb: 'np.ndarray') -> None:
        """更新预览图像。image_rgb: (H, W, 3) uint8"""
        import numpy as np
        from qtpy import QtGui
        arr = np.asarray(image_rgb)
        if arr.ndim != 3 or arr.shape[2] != 3:
            return
        h, w = arr.shape[:2]
        # 转为连续 uint8，再用 bytes() 深拷贝，避免 QImage 持有裸指针时 numpy array 被 GC
        arr_c = np.ascontiguousarray(arr, dtype=np.uint8)
        raw_bytes = bytes(arr_c)
        qimg = QtGui.QImage(raw_bytes, w, h, w * 3, QtGui.QImage.Format_RGB888)
        self._original_pixmap = QtGui.QPixmap.fromImage(qimg)
        self._image_label.setText('')
        self._refresh_scaled_pixmap()

    def _refresh_scaled_pixmap(self) -> None:
        """根据当前 label 尺寸把原始 pixmap 缩放显示。"""
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return
        scaled = self._original_pixmap.scaled(
            self._image_label.width(),
            self._image_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self._image_label.setPixmap(scaled)

    def resizeEvent(self, event):  # noqa: N802 (Qt API)
        super().resizeEvent(event)
        self._refresh_scaled_pixmap()

    def set_status(self, text: str) -> None:
        self._status_label.setText(text)

    def clear(self) -> None:
        self._original_pixmap = None
        self._image_label.clear()
        self._image_label.setText('加载图像后点击"刷新预览"查看颗粒效果')
