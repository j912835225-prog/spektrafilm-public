"""
帮助对话框 — 参数使用指南
"""
from __future__ import annotations

from qtpy import QtCore, QtWidgets, QtGui

HELP_HTML = """
<style>
body { font-family: -apple-system, 'PingFang SC', sans-serif; font-size: 13px;
       color: #d4d4d4; background: #141414; line-height: 1.7; padding: 4px 8px; }
h1 { color: #c8a96e; font-size: 15px; margin: 16px 0 6px; border-bottom: 1px solid #2e2e2e; padding-bottom: 6px; }
h2 { color: #c8a96e; font-size: 13px; margin: 14px 0 4px; }
h3 { color: #aaa; font-size: 12px; margin: 10px 0 3px; }
p  { margin: 4px 0 8px; color: #b0b0b0; }
table { width: 100%; border-collapse: collapse; margin: 6px 0 12px; }
th { background: #1e1e1e; color: #888; font-size: 11px; padding: 5px 8px; text-align: left; }
td { padding: 5px 8px; border-bottom: 1px solid #222; color: #c0c0c0; font-size: 12px; }
td:first-child { color: #c8a96e; white-space: nowrap; }
.tag { display: inline-block; background: #2a2a1a; color: #c8a96e;
       border: 1px solid #4a3a20; border-radius: 3px; padding: 1px 6px;
       font-size: 11px; margin: 1px 2px; }
.note { background: #1a1a2a; border-left: 3px solid #c8a96e;
        padding: 6px 10px; margin: 8px 0; border-radius: 0 4px 4px 0;
        color: #aaa; font-size: 12px; }
.section-label { color: #888; font-size: 11px; text-transform: uppercase;
                 letter-spacing: 0.05em; margin: 16px 0 4px; }
</style>

<h1>参数使用指南</h1>
<p>这个工具用物理模型模拟胶片的完整成像过程，不是套滤镜。
下面按影响力从大到小说明哪些参数真正影响你的照片。</p>

<h1>第一层：决定整体色彩性格</h1>
<p class="section-label">主面板 → 胶片与相纸</p>
<p>这是最大的决定。不同胶片的色彩性格来自三个化学层的光谱敏感曲线和染料耦合关系，不是靠调色调出来的。</p>

<table>
<tr><th>你想要的感觉</th><th>选这个胶片</th></tr>
<tr><td>暖调人像，高光柔和，阴影偏绿</td><td>kodak_portra_400</td></tr>
<tr><td>极高饱和，风光，正片感</td><td>fujifilm_velvia_100</td></tr>
<tr><td>电影感，日光场景</td><td>kodak_vision3_50d</td></tr>
<tr><td>电影感，室内钨丝灯</td><td>kodak_vision3_500t</td></tr>
<tr><td>日系清冷，阴影偏绿蓝</td><td>fujifilm_pro_400h</td></tr>
<tr><td>复古暖调，Kodachrome 经典</td><td>kodak_kodachrome_64</td></tr>
<tr><td>高饱和风光，细腻颗粒</td><td>kodak_ektar_100</td></tr>
</table>

<p>相纸推荐起点：<span class="tag">kodak_ultra_endura</span> 或 <span class="tag">fujifilm_crystal_archive_typeii</span>，电影感用 <span class="tag">kodak_2383</span>。</p>

<h1>第二层：曝光和色调（每次都要调）</h1>
<p class="section-label">主面板 → 曝光控制 / 印刷色调 / 色调</p>

<h2>曝光补偿 EV</h2>
<p>胶片有自己的最佳曝光区间，不是数码的 0EV 就是最好。</p>
<table>
<tr><th>胶片</th><th>建议曝光</th><th>原因</th></tr>
<tr><td>Portra 系列</td><td>+0.5 到 +1EV</td><td>高光更柔，肤色更暖</td></tr>
<tr><td>Velvia</td><td>-0.3EV</td><td>饱和度更高</td></tr>
<tr><td>Vision3 系列</td><td>0EV</td><td>正常曝光即可</td></tr>
</table>

<h2>印刷色调</h2>
<p>模拟暗房里调整放大机滤镜，是控制整体色调最直接的手段。</p>
<table>
<tr><th>滑杆</th><th>向左</th><th>向右</th></tr>
<tr><td>暖 ←→ 冷</td><td>偏暖偏黄</td><td>偏冷偏青</td></tr>
<tr><td>品红 ←→ 绿</td><td>偏品红</td><td>偏绿，日系感</td></tr>
</table>
<p>典型范围 ±30，超过 ±40 会比较夸张。</p>

<h2>色调（胶片 gamma / 相纸 gamma）</h2>
<p>控制负片和相纸的对比度响应。&gt;1 对比更强，&lt;1 更柔。默认 1.0 是物理真实值。先定 gamma，再调印刷色调，顺序不要反。</p>

<h1>第三层：Halation（胶片感最强的特征）</h1>
<p class="section-label">效果 Tab → Halation（红光渗透）</p>

<p>Halation 是胶片最具辨识度的特征——红光穿透乳剂层反射回来，在高光边缘产生红色/橙色光晕。数码完全没有这个效果。</p>

<table>
<tr><th>想要的效果</th><th>散射强度</th><th>Halation 强度</th></tr>
<tr><td>最真实（物理默认）</td><td>1.0</td><td>1.0</td></tr>
<tr><td>更强的胶片感</td><td>1.2–1.5</td><td>1.2–1.5</td></tr>
<tr><td>干净一点</td><td>0.5–0.8</td><td>0.5–0.8</td></tr>
<tr><td>完全关闭</td><td>0</td><td>0（或关闭开关）</td></tr>
</table>

<div class="note">其他 Halation 参数（散射核心、尾部、反弹次数等）是物理底层参数，通常不需要动。作者已按胶片数据设好了默认值。</div>

<h1>第四层：颗粒（质感）</h1>
<p class="section-label">效果 Tab → 颗粒</p>

<p>这里的颗粒不是普通噪点叠加，是基于卤化银颗粒物理模型的光谱级模拟。</p>

<div class="note">颗粒在预览模式下不显示，需要全分辨率扫描才能看到实际效果。调整颗粒参数后松手会自动触发全分辨率扫描。</div>

<h2>颗粒大小（最重要）</h2>
<table>
<tr><th>颗粒大小</th><th>对应感觉</th></tr>
<tr><td>0.1</td><td>ISO 100，极细腻</td></tr>
<tr><td>0.4</td><td>ISO 400，标准</td></tr>
<tr><td>0.8</td><td>ISO 800，明显颗粒</td></tr>
<tr><td>1.5</td><td>ISO 3200，粗粒</td></tr>
</table>

<h2>模糊 sigma（像素）</h2>
<p>控制颗粒的"软硬"。0.6–0.7 是标准值，高分辨率图像可以调到 0.8–0.9，让颗粒看起来更自然。</p>

<div class="note">其他颗粒参数（RGB 层颗粒比例、子层缩放、均匀度等）是微调，通常不需要动。</div>

<h1>第五层：DIR 耦合剂（色彩性格的根源）</h1>
<p class="section-label">效果 Tab → DIR 耦合剂</p>

<p>这是"为什么 Portra 和 Pro 400H 颜色性格不同"的根本原因。切换胶片型号时会自动加载该胶片的物理默认值，通常不需要手动调。</p>

<table>
<tr><th>参数</th><th>调低效果</th><th>调高效果</th></tr>
<tr><td>全局倍率</td><td>色彩更"干净"，层间串扰减少</td><td>色彩关系更夸张</td></tr>
<tr><td>跨层抑制</td><td>饱和度降低</td><td>饱和度增强</td></tr>
</table>

<h1>第六层：效果细节</h1>
<p class="section-label">效果 Tab</p>

<h2>眩光</h2>
<p>模拟相纸表面的光泽反射。默认开启，强度 0.03 是很微弱的效果，通常不需要改。</p>

<h2>预闪</h2>
<p>暗房技术：在正式曝光前给相纸一次极低剂量的均匀曝光，压缩高光、提亮阴影，降低整体对比度。想要更低对比度时用，曝光量 0.01–0.05 EV。</p>

<h2>前期柔光</h2>
<p>模拟拍摄时镜头前加的柔光镜，作用在胶片曝光之前。影响整体柔化感。</p>

<h2>后期柔光</h2>
<p>模拟暗房放大机镜头前加的柔光镜，作用在印放阶段。和前期柔光叠加使用可以做出不同质感。</p>

<h1>高级参数（通常不需要动）</h1>
<p class="section-label">高级 Tab</p>

<h2>RAW 参数</h2>
<p>只在导入 RAW 文件时生效。白平衡默认 <span class="tag">as_shot</span>（使用相机记录的白平衡），对专业摄影师已经是正确答案。</p>

<h2>输入图像</h2>
<p>默认 <span class="tag">ProPhoto RGB</span>，对应 Darktable 线性导出。如果导入普通 JPEG，改为 <span class="tag">sRGB</span> 并开启 CCTF 解码。</p>

<h1>推荐工作流</h1>

<h2>快速出片（5 分钟）</h2>
<p>1. 导入图像<br>
2. 选胶片型号<br>
3. 调曝光补偿 EV<br>
4. 调印刷色调（暖冷 / 品红绿）<br>
5. 调 gamma 系数（对比度）<br>
6. 预览，满意就保存</p>

<h2>精细调整</h2>
<table>
<tr><th>问题</th><th>解决方法</th></tr>
<tr><td>高光太硬</td><td>调高 Halation 强度</td></tr>
<tr><td>颗粒太假</td><td>调整颗粒模糊 sigma</td></tr>
<tr><td>色彩关系不对</td><td>调色彩交叉全局倍率</td></tr>
<tr><td>想要更暗房感</td><td>开预闪，曝光量 0.02–0.05</td></tr>
<tr><td>整体太平</td><td>提高胶片/相纸 gamma 系数</td></tr>
<tr><td>整体太硬</td><td>降低 gamma，或开预闪</td></tr>
</table>

<h2>不需要动的参数</h2>
<p>散射核心/尾部、Halation 反弹次数/衰减比、颗粒各层缩放、光谱上采样参数——这些是物理底层，作者已按胶片数据设好了。</p>

<div style="margin-top: 24px; padding-top: 12px; border-top: 1px solid #2e2e2e; color: #444; font-size: 11px; line-height: 1.8;">
Physics engine &amp; film data: <span style="color: #666;">Andrea Volpato</span> — <a style="color: #555;">spektrafilm / agx-emulsion</a><br>
Interface &amp; experience: <span style="color: #666;">MZ</span>
</div>
"""


class HelpDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('参数使用指南')
        self.setMinimumSize(520, 680)
        self.resize(560, 720)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        browser = QtWidgets.QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setHtml(HELP_HTML)
        browser.setStyleSheet("""
            QTextBrowser {
                background: #141414;
                border: none;
                padding: 8px;
            }
            QScrollBar:vertical {
                background: #141414;
                width: 6px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #333;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)
        layout.addWidget(browser, 1)

        close_btn = QtWidgets.QPushButton('关闭')
        close_btn.setFixedHeight(32)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #1e1e1e;
                color: #888;
                border: none;
                border-top: 1px solid #2e2e2e;
                font-size: 12px;
            }
            QPushButton:hover { background: #282828; color: #ccc; }
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self.setStyleSheet('QDialog { background: #141414; border: 1px solid #2e2e2e; }')


def show_help(parent=None):
    dialog = HelpDialog(parent)
    dialog.exec_()
