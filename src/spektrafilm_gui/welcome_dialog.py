"""
欢迎对话框 — 首次启动时显示，可选择不再显示。
"""
from __future__ import annotations

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import QSettings

from spektrafilm_gui.theme_palette import (
    ACCENT_COLOR_TEXT,
    GRAY_0, GRAY_1, GRAY_2, GRAY_3, GRAY_4,
    TEXT_DIM, TEXT_MAIN, TEXT_HI,
)

_SETTINGS_KEY = "welcome/show_on_startup"


def should_show_welcome() -> bool:
    settings = QSettings("spektrafilm", "spektrafilm")
    return bool(settings.value(_SETTINGS_KEY, True, type=bool))


def _set_show_on_startup(value: bool) -> None:
    settings = QSettings("spektrafilm", "spektrafilm")
    settings.setValue(_SETTINGS_KEY, value)


class _LogoWidget(QtWidgets.QWidget):
    """手绘 logo：胶片条纹 + S 字母。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(52, 52)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        accent = QtGui.QColor(ACCENT_COLOR_TEXT)
        dim = QtGui.QColor(GRAY_3)
        bg = QtGui.QColor(GRAY_1)

        w, h = self.width(), self.height()

        # 外框圆角矩形（胶片边框感）
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(0, 0, w, h, 6, 6)

        # 左右胶片格孔（各 3 个小方块）
        hole_w, hole_h = 5, 7
        hole_x_left = 4
        hole_x_right = w - hole_w - 4
        hole_positions = [8, 22, 36]
        p.setBrush(dim)
        for y in hole_positions:
            p.drawRoundedRect(hole_x_left, y, hole_w, hole_h, 1, 1)
            p.drawRoundedRect(hole_x_right, y, hole_w, hole_h, 1, 1)

        # 中央 "S" 字母
        p.setPen(accent)
        font = QtGui.QFont("-apple-system", 22, QtGui.QFont.Bold)
        font.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, -1)
        p.setFont(font)
        p.drawText(QtCore.QRect(0, 0, w, h), QtCore.Qt.AlignCenter, "S")

        p.end()


class WelcomeDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Spektrafilm")
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        self.setFixedSize(520, 380)
        self._build_ui()
        self._apply_style()

    def _build_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(48, 44, 48, 32)
        root.setSpacing(0)

        # ── Logo + 标题 横排 ──
        header = QtWidgets.QHBoxLayout()
        header.setSpacing(16)
        header.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        logo = _LogoWidget()
        header.addWidget(logo)

        title_col = QtWidgets.QVBoxLayout()
        title_col.setSpacing(2)
        title = QtWidgets.QLabel("Spektrafilm")
        title.setObjectName("welcome_title")
        subtitle = QtWidgets.QLabel("胶片成像的物理模拟")
        subtitle.setObjectName("welcome_subtitle")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col)

        root.addLayout(header)
        root.addSpacing(28)

        # ── 正文 ──
        line2 = QtWidgets.QLabel("选一张底片，选一张相纸，剩下的交给化学。")
        line2.setObjectName("welcome_body")
        root.addWidget(line2)

        root.addStretch()

        # ── 分割线 ──
        divider = QtWidgets.QFrame()
        divider.setFrameShape(QtWidgets.QFrame.HLine)
        divider.setObjectName("welcome_divider")
        root.addWidget(divider)
        root.addSpacing(16)

        # ── 作者第一句（深夜那句，更有温度，放前面）──
        quote1_en = QtWidgets.QLabel(
            "\u201cDeveloped in my free time, often during late nights\n"
            "after my research work at KTH.\u201d"
        )
        quote1_en.setObjectName("welcome_quote")
        quote1_en.setWordWrap(True)
        root.addWidget(quote1_en)

        quote1_cn = QtWidgets.QLabel("在 KTH 的研究工作结束后的深夜，用业余时间写成。")
        quote1_cn.setObjectName("welcome_quote_cn")
        quote1_cn.setWordWrap(True)
        root.addWidget(quote1_cn)

        root.addSpacing(12)

        # ── 作者第二句（使命那句）──
        quote2_en = QtWidgets.QLabel(
            "\u201cNot just to imitate a generic film look, but to build\n"
            "a model grounded in measurements.\u201d"
        )
        quote2_en.setObjectName("welcome_quote")
        quote2_en.setWordWrap(True)
        root.addWidget(quote2_en)

        quote2_cn = QtWidgets.QLabel("不只是模仿胶片感，而是建立以实测数据为基础的模型。")
        quote2_cn.setObjectName("welcome_quote_cn")
        quote2_cn.setWordWrap(True)
        root.addWidget(quote2_cn)

        root.addSpacing(10)

        # ── 署名 ──
        credit = QtWidgets.QLabel("— Andrea Volpato，KTH 皇家理工学院")
        credit.setObjectName("welcome_credit")
        root.addWidget(credit)

        root.addSpacing(20)

        # ── 底部：不再显示 + 开始 ──
        bottom = QtWidgets.QHBoxLayout()
        bottom.setSpacing(0)

        self._no_show_checkbox = QtWidgets.QCheckBox("不再显示")
        self._no_show_checkbox.setObjectName("welcome_checkbox")
        bottom.addWidget(self._no_show_checkbox)
        bottom.addStretch()

        start_btn = QtWidgets.QPushButton("开始")
        start_btn.setObjectName("welcome_start_btn")
        start_btn.setFixedSize(80, 32)
        start_btn.clicked.connect(self._on_start)
        bottom.addWidget(start_btn)

        root.addLayout(bottom)

    def _apply_style(self) -> None:
        self.setStyleSheet(f"""
            WelcomeDialog {{
                background: {GRAY_0};
                border: 1px solid {GRAY_3};
            }}
            QLabel#welcome_title {{
                font-family: -apple-system, 'PingFang SC', sans-serif;
                font-size: 24px;
                font-weight: 600;
                color: {ACCENT_COLOR_TEXT};
                letter-spacing: 0.02em;
            }}
            QLabel#welcome_subtitle {{
                font-family: -apple-system, 'PingFang SC', sans-serif;
                font-size: 12px;
                color: {TEXT_DIM};
                letter-spacing: 0.03em;
            }}
            QLabel#welcome_body {{
                font-family: -apple-system, 'PingFang SC', sans-serif;
                font-size: 15px;
                color: {TEXT_MAIN};
            }}
            QFrame#welcome_divider {{
                color: {GRAY_3};
                background: {GRAY_3};
                max-height: 1px;
            }}
            QLabel#welcome_quote {{
                font-family: Georgia, serif;
                font-size: 12px;
                font-style: italic;
                color: {TEXT_DIM};
            }}
            QLabel#welcome_quote_cn {{
                font-family: -apple-system, 'PingFang SC', sans-serif;
                font-size: 11px;
                color: {GRAY_4};
                padding-left: 2px;
            }}
            QLabel#welcome_credit {{
                font-family: -apple-system, 'PingFang SC', sans-serif;
                font-size: 11px;
                color: {TEXT_DIM};
            }}
            QCheckBox#welcome_checkbox {{
                font-family: -apple-system, 'PingFang SC', sans-serif;
                font-size: 12px;
                color: {TEXT_DIM};
                spacing: 6px;
            }}
            QCheckBox#welcome_checkbox::indicator {{
                width: 14px;
                height: 14px;
                border: 1px solid {GRAY_3};
                border-radius: 3px;
                background: {GRAY_2};
            }}
            QCheckBox#welcome_checkbox::indicator:checked {{
                background: {GRAY_3};
                border-color: {ACCENT_COLOR_TEXT};
            }}
            QPushButton#welcome_start_btn {{
                font-family: -apple-system, 'PingFang SC', sans-serif;
                font-size: 13px;
                color: {ACCENT_COLOR_TEXT};
                background: transparent;
                border: 1px solid {GRAY_3};
                border-radius: 4px;
                padding: 0 16px;
            }}
            QPushButton#welcome_start_btn:hover {{
                background: {GRAY_2};
                border-color: {ACCENT_COLOR_TEXT};
            }}
            QPushButton#welcome_start_btn:pressed {{
                background: {GRAY_1};
            }}
        """)

    def _on_start(self) -> None:
        if self._no_show_checkbox.isChecked():
            _set_show_on_startup(False)
        self.accept()


def show_welcome_if_needed(parent: QtWidgets.QWidget | None = None) -> None:
    """如果用户没有选择「不再显示」，弹出欢迎对话框。"""
    if not should_show_welcome():
        return
    dialog = WelcomeDialog(parent)
    dialog.exec()
