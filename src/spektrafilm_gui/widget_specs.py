from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from spektrafilm_gui.options import (
    AutoExposureMethods,
    DiffusionFilterFamilies,
    NapariInterpolationModes,
    RGBColorSpaces,
    RGBtoRAWMethod,
    RawWhiteBalance,
)
from spektrafilm.model.illuminants import Illuminants
from spektrafilm.model.stocks import FilmStocks, PrintPapers


@dataclass(frozen=True, slots=True)
class WidgetSpec:
    label: str | None = None
    tooltip: str | None = None
    min_value: float | int | None = None
    max_value: float | int | None = None
    step: float | int | None = None
    decimals: int | None = None


@dataclass(frozen=True, slots=True)
class ButtonSpec:
    text: str
    tooltip: str | None = None
    preserve_case: bool = False


GUI_SECTION_ENUMS: dict[str, dict[str, type[Enum]]] = {
    "input_image": {
        "input_color_space": RGBColorSpaces,
        "spectral_upsampling_method": RGBtoRAWMethod,
    },
    "load_raw": {
        "white_balance": RawWhiteBalance,
    },
    "display": {
        "output_interpolation": NapariInterpolationModes,
    },
    "simulation": {
        "film_stock": FilmStocks,
        "auto_exposure_method": AutoExposureMethods,
        "camera_diffusion_filter_family": DiffusionFilterFamilies,
        "print_paper": PrintPapers,
        "print_illuminant": Illuminants,
        "output_color_space": RGBColorSpaces,
        "saving_color_space": RGBColorSpaces,
        "diffusion_filter_family": DiffusionFilterFamilies,
    },
}


GUI_WIDGET_SPECS = {
    "simulation": {
        "film_stock": WidgetSpec(label="胶片型号", tooltip="选择要模拟的胶片"),
        "exposure_compensation_ev": WidgetSpec(
            label="相机曝光补偿 EV",
            tooltip="在自动曝光基础上叠加偏移量。±1EV 是日常范围，±3EV 是极端情况。每 1EV 亮度翻倍或减半。",
            min_value=-5,
            max_value=5,
            step=0.25,
        ),
        "auto_exposure": WidgetSpec(
            label="相机自动曝光",
            tooltip="启用虚拟相机的自动曝光功能",
        ),
        "film_format_mm": WidgetSpec(
            label="胶片幅面 mm",
            tooltip="胶片长边尺寸（毫米），如 8、16、35、60、120",
            min_value=8.0,
            max_value=120.0,
            step=1.0,
            decimals=0,
        ),
        "camera_lens_blur_um": WidgetSpec(
            label="镜头柔化",
            tooltip="相机镜头高斯模糊的 sigma 值（微米）。普通镜头约 5um，高质量镜头 2-4um，模拟无镜头模糊时设为 0。",
            step=0.05,
            min_value=0,
            max_value=15,
        ),
        "camera_diffusion_filter_active": WidgetSpec(
            label="柔光滤镜开关",
            tooltip="在胶片曝光前的相机阶段启用柔光滤镜",
        ),
        "camera_diffusion_filter_family": WidgetSpec(
            label="柔光滤镜类型",
            tooltip="相机阶段使用的 PSF 滤镜族",
        ),
        "camera_diffusion_filter_strength": WidgetSpec(
            label="柔光强度",
            tooltip="商业滤镜档位：0、1/8=0.125、1/4=0.25、1/2=0.5、1、2",
            min_value=0,
            max_value=2,
            step=0.125,
        ),
        "camera_diffusion_filter_spatial_scale": WidgetSpec(
            label="PSF 空间缩放",
            tooltip="相机阶段 PSF 宽度的倍率（1.0 = 默认尺寸，2.0 = 扩散范围翻倍）",
            min_value=0,
            max_value=4,
            step=0.05,
        ),
        "camera_diffusion_filter_halo_warmth": WidgetSpec(
            label="光晕暖调",
            tooltip="相机阶段光晕暖调偏移。正值=外圈暖/内圈冷，负值反转，0=使用默认值",
            min_value=-1.5,
            max_value=1.5,
            step=0.05,
        ),
        "camera_diffusion_filter_core_intensity": WidgetSpec(
            label="核心强度（高级）",
            tooltip="相机阶段核心权重倍率，1.0=使用默认值",
            min_value=0,
            max_value=4,
            step=0.05,
        ),
        "camera_diffusion_filter_core_size": WidgetSpec(
            label="核心尺寸（高级）",
            tooltip="相机阶段核心 lambda 倍率，1.0=使用默认值",
            min_value=0.1,
            max_value=4,
            step=0.05,
        ),
        "camera_diffusion_filter_halo_intensity": WidgetSpec(
            label="光晕强度（高级）",
            tooltip="相机阶段光晕权重倍率，1.0=使用默认值",
            min_value=0,
            max_value=4,
            step=0.05,
        ),
        "camera_diffusion_filter_halo_size": WidgetSpec(
            label="光晕尺寸（高级）",
            tooltip="相机阶段光晕 lambda 倍率，1.0=使用默认值",
            min_value=0.1,
            max_value=4,
            step=0.05,
        ),
        "camera_diffusion_filter_bloom_intensity": WidgetSpec(
            label="泛光强度（高级）",
            tooltip="相机阶段泛光权重倍率，1.0=使用默认值",
            min_value=0,
            max_value=4,
            step=0.05,
        ),
        "camera_diffusion_filter_bloom_size": WidgetSpec(
            label="泛光尺寸（高级）",
            tooltip="相机阶段泛光 lambda 倍率，1.0=使用默认值",
            min_value=0.1,
            max_value=4,
            step=0.05,
        ),
        "print_paper": WidgetSpec(label="相纸型号", tooltip="选择要模拟的相纸"),
        "print_illuminant": WidgetSpec(label="放大机光源", tooltip="模拟放大机使用的光源类型"),
        "print_exposure": WidgetSpec(
            label="印放曝光量",
            tooltip="调整虚拟放大机的曝光时间",
            step=0.02,
            min_value=0,
            max_value=3,
        ),
        "print_exposure_compensation": WidgetSpec(
            label="印放自动补偿",
            tooltip="根据相机曝光补偿 EV 自动调整印放曝光",
        ),
        "print_y_filter_shift": WidgetSpec(
            label="暖 ←→ 冷",
            tooltip="印刷色调暖冷偏移。向左偏暖，向右偏冷。典型范围 ±30。",
            min_value=-50,
            max_value=50,
            step=1,
            decimals=0,
        ),
        "print_m_filter_shift": WidgetSpec(
            label="品红 ←→ 绿",
            tooltip="印刷色调品红/绿偏移。向左偏品红，向右偏绿。典型范围 ±30。",
            min_value=-50,
            max_value=50,
            step=1,
            decimals=0,
        ),
        "diffusion_filter_active": WidgetSpec(
            label="柔光滤镜开关",
            tooltip="在印放阶段启用柔光滤镜（Pro-Mist 族）",
        ),
        "diffusion_filter_family": WidgetSpec(
            label="柔光滤镜类型",
            tooltip="PSF 族。pro_mist/classic_soft/glimmerglass 为透明（能量守恒）；black_pro_mist 会吸收部分偏折光，通过降低局部对比度来提亮阴影。",
        ),
        "diffusion_filter_strength": WidgetSpec(
            label="柔光强度",
            tooltip="商业滤镜档位：0、1/8=0.125、1/4=0.25、1/2=0.5、1、2",
            min_value=0,
            max_value=2,
            step=0.125,
        ),
        "diffusion_filter_spatial_scale": WidgetSpec(
            label="PSF 空间缩放",
            tooltip="图像平面 PSF 宽度的倍率（1.0 = 默认尺寸），根据幅面/印放尺寸调整",
            min_value=0,
            max_value=4,
            step=0.05,
        ),
        "diffusion_filter_halo_warmth": WidgetSpec(
            label="光晕暖调",
            tooltip="光晕暖调轴偏移。正值=外圈暖/内圈冷，负值反转，0=使用默认值",
            min_value=-1.5,
            max_value=1.5,
            step=0.05,
        ),
        "diffusion_filter_core_intensity": WidgetSpec(
            label="核心强度（高级）",
            tooltip="核心权重倍率，三组权重（核心/光晕/泛光）归一化为 1，1.0=使用默认值",
            min_value=0,
            max_value=4,
            step=0.05,
        ),
        "diffusion_filter_core_size": WidgetSpec(
            label="核心尺寸（高级）",
            tooltip="核心 lambda 倍率，1.0=使用默认值",
            min_value=0.1,
            max_value=4,
            step=0.05,
        ),
        "diffusion_filter_halo_intensity": WidgetSpec(
            label="光晕强度（高级）",
            tooltip="光晕权重倍率，三组权重归一化为 1，1.0=使用默认值",
            min_value=0,
            max_value=4,
            step=0.05,
        ),
        "diffusion_filter_halo_size": WidgetSpec(
            label="光晕尺寸（高级）",
            tooltip="光晕 lambda 倍率，1.0=使用默认值",
            min_value=0.1,
            max_value=4,
            step=0.05,
        ),
        "diffusion_filter_bloom_intensity": WidgetSpec(
            label="泛光强度（高级）",
            tooltip="泛光权重倍率，三组权重归一化为 1，1.0=使用默认值",
            min_value=0,
            max_value=4,
            step=0.05,
        ),
        "diffusion_filter_bloom_size": WidgetSpec(
            label="泛光尺寸（高级）",
            tooltip="泛光 lambda 倍率，1.0=使用默认值",
            min_value=0.1,
            max_value=4,
            step=0.05,
        ),
        "scan_lens_blur": WidgetSpec(
            label="输出柔化",
            tooltip="扫描仪镜头高斯模糊的 sigma 值（像素）",
            step=0.05,
            min_value=0,
            max_value=3,
        ),
        "scan_white_correction": WidgetSpec(
            label="输出白点校正",
            tooltip="启用输出的白点校正",
        ),
        "scan_white_level": WidgetSpec(
            label="输出白点目标值",
            tooltip="启用白点校正时的目标白点亮度",
            min_value=0,
            max_value=1,
            step=0.005,
            decimals=3,
        ),
        "scan_black_correction": WidgetSpec(
            label="输出黑点校正",
            tooltip="启用输出的黑点校正",
        ),
        "scan_black_level": WidgetSpec(
            label="输出黑点目标值",
            tooltip="启用黑点校正时的目标黑点亮度",
            min_value=0,
            max_value=1,
            step=0.005,
            decimals=3,
        ),
        "scan_unsharp_mask": WidgetSpec(
            label="输出锐化",
            tooltip="对输出结果应用锐化蒙版，[像素 sigma，强度]",
            step=0.05,
            min_value=0,
            max_value=3,
        ),
        "output_color_space": WidgetSpec(label="输出色彩空间", tooltip="模拟结果的输出色彩空间"),
        "saving_color_space": WidgetSpec(label="保存色彩空间", tooltip="保存图像文件时使用的色彩空间"),
        "saving_cctf_encoding": WidgetSpec(
            label="保存 CCTF 编码",
            tooltip="保存文件时是否附加 CCTF 传递函数",
        ),
        "auto_preview": WidgetSpec(label="自动预览", tooltip="每次修改参数后自动触发预览，可用鼠标滚轮调节参数值"),
        "scan_film": WidgetSpec(label="扫描负片", tooltip="显示负片扫描结果而非印放输出"),
    },
    "display": {
        "use_display_transform": WidgetSpec(
            label="使用显示变换",
            tooltip="使用 Pillow.ImageCms 获取显示变换（仅 Windows）并应用到 napari 输出，禁用时直接使用输出色彩空间",
        ),
        "gray_18_canvas": WidgetSpec(
            label="18% 灰色背景",
            tooltip="使用中性 18% 灰作为背景，便于判断曝光和中性色",
        ),
        "output_interpolation": WidgetSpec(
            label="输出插值方式",
            tooltip="napari 查看器显示输出图层时使用的插值模式",
        ),
        "white_padding": WidgetSpec(
            label="白边宽度",
            tooltip="预览帧周围白色边框的宽度，以图像长边的比例表示",
            min_value=0,
            max_value=1,
            step=0.01,
        ),
        "preview_max_size": WidgetSpec(
            label="预览最大尺寸",
            tooltip="预览图像长边的最大像素数，越大越清晰但越慢。建议：1200（清晰快速）/ 1600（高清）/ 2048（极清，较慢）",
            min_value=256,
            max_value=2048,
            step=128,
        ),
    },
    "special": {
        "film_gamma_factor": WidgetSpec(
            label="胶片 Gamma 系数",
            tooltip="负片密度曲线的 gamma 系数，<1 降低对比度，>1 提高对比度",
            step=0.02,
            min_value=0.01,
            max_value=2,
        ),
        "film_channel_swap": WidgetSpec(label="胶片通道互换"),
        "print_gamma_factor": WidgetSpec(
            label="相纸 Gamma 系数",
            tooltip="相纸的 gamma 系数，<1 降低对比度，>1 提高对比度",
            step=0.02,
            min_value=0.01,
            max_value=2,
        ),
        "print_channel_swap": WidgetSpec(label="相纸通道互换",
        min_value=0,
        max_value=2,
        step=1
        )
    },
    "glare": {
        "active": WidgetSpec(label="开关", tooltip="为印放结果添加眩光"),
        "percent": WidgetSpec(
            label="眩光强度",
            tooltip="眩光光量百分比（典型值 0.1-0.25）",
            step=0.005,
            min_value=0,
            max_value=1,
            decimals=3,
        ),
        "roughness": WidgetSpec(
            label="粗糙度",
            tooltip="眩光粗糙度（0=镜面，1=完全漫射）",
            min_value=0,
            max_value=1,
            step=0.02,
        ),
        "blur": WidgetSpec(
            label="模糊范围",
            tooltip="眩光高斯模糊的 sigma 值（像素）",
            min_value=0,
            max_value=30,
            step=0.1,
        ),
    },
    "halation": {
        "scatter_amount": WidgetSpec(
            label="散射强度",
            tooltip="散射强度。1.0=完整物理散射，0.0=无散射。控制乳剂内散射光的比例。",
            min_value=0,
            max_value=3,
            step=0.05,
        ),
        "scatter_spatial_scale": WidgetSpec(
            label="散射尺寸倍率",
            tooltip="散射尺寸倍率（1.0=物理默认值），同时缩放核心和尾部 sigma",
            min_value=0,
            max_value=4,
            step=0.05,
        ),
        "halation_amount": WidgetSpec(
            label="Halation 强度",
            tooltip="Halation 强度倍率（1.0=物理默认值），缩放各通道 halation 幅度",
            min_value=0,
            max_value=3,
            step=0.05,
        ),
        "halation_spatial_scale": WidgetSpec(
            label="Halation 尺寸倍率",
            tooltip="Halation 尺寸倍率（1.0=物理默认值），缩放第一次反弹 sigma",
            min_value=0,
            max_value=4,
            step=0.05,
        ),
        "boost_ev": WidgetSpec(
            label="高光提升量",
            tooltip="高光最大提升量（档），0=不提升",
            min_value=0,
            max_value=4,
            step=0.25,
        ),
        "protect_ev": WidgetSpec(
            label="高光保护范围",
            tooltip="高光提升起始点距中灰的保护范围（档），典型值 3-5",
            min_value=0,
            max_value=8,
            step=0.25,
        ),
        "boost_range": WidgetSpec(
            label="高光过渡速度",
            tooltip="高光提升的过渡速度，0=硬切，1=最柔",
            min_value=0,
            max_value=1,
            step=0.05,
        ),
        "scatter_core_um": WidgetSpec(
            label="散射核心 [R,G,B]",
            tooltip="各通道 [R,G,B] 散射核心高斯 sigma（微米），控制乳剂内细节锐度损失",
            min_value=0,
            max_value=15,
            step=0.2,
        ),
        "scatter_tail_um": WidgetSpec(
            label="散射尾部 [R,G,B]",
            tooltip="各通道 [R,G,B] 散射指数尾部衰减常数（微米），控制乳剂内的延伸扩散",
            min_value=0,
            max_value=30,
            step=0.5,
        ),
        "scatter_tail_weight": WidgetSpec(
            label="散射尾部权重 %",
            tooltip="各通道 [R,G,B] 散射尾部权重（0-100%），尾部+核心=100%，值越大散射越向长尾集中",
            min_value=0,
            max_value=100,
            step=1,
        ),
        "halation_strength": WidgetSpec(
            label="Halation 幅度 %",
            tooltip="各通道 [R,G,B] 背反射 halation 幅度（0-100%）。红通道典型值：弱 AH 2-8，无 AH 8-25，蓝通道通常接近 0",
            min_value=0,
            max_value=100,
            step=0.5,
        ),
        "halation_first_sigma_um": WidgetSpec(
            label="第一次反弹 sigma",
            tooltip="各通道 [R,G,B] 第一次反弹 halation 的 sigma（微米），由片基厚度决定（典型电影/静态片基 40-80um）",
            min_value=0,
            max_value=150,
            step=1.0,
            decimals=0,
        ),
        "halation_n_bounces": WidgetSpec(
            label="反弹次数",
            tooltip="halation 叠加的多次反弹高斯数量，后续反弹使用 sqrt(k) 间距宽度，典型值 2-3",
            min_value=1,
            max_value=5,
            step=1,
        ),
        "halation_bounce_decay": WidgetSpec(
            label="反弹衰减比",
            tooltip="每次反弹的幅度衰减比（rho），物理范围 0.3-0.7，控制 halation 能量在各次反弹间的衰减速度",
            min_value=0,
            max_value=1,
            step=0.02,
        ),
        "halation_renormalize": WidgetSpec(
            label="归一化",
            tooltip="启用时除以（1+反弹幅度之和）以保持中灰不变；禁用时 halation 为纯叠加，会轻微提亮阴影和高光",
        ),
    },
    "couplers": {
        "amount": WidgetSpec(
            label="全局倍率",
            tooltip="DIR 耦合剂抑制矩阵的全局倍率，1.0=保持各通道 gamma 不变",
            min_value=0,
            max_value=3,
            step=0.02,
        ),
        "inhibition_samelayer": WidgetSpec(
            label="同层抑制",
            tooltip="同层（对角线）抑制倍率，控制各 RGB 层内的整体对比度/gamma 降低",
            min_value=0,
            max_value=3,
            step=0.02,
        ),
        "inhibition_interlayer": WidgetSpec(
            label="跨层抑制",
            tooltip="跨层（非对角线）抑制倍率，控制层间 DIR 效应带来的饱和度增强",
            min_value=0,
            max_value=3,
            step=0.02,
        ),
        "gamma_samelayer_rgb": WidgetSpec(
            label="同层 gamma [R,G,B]",
            tooltip="各通道同层 DIR gamma（R、G、B），即各层密度曲线的有效 gamma 降低量",
            min_value=0,
            max_value=1,
            step=0.01,
        ),
        "gamma_interlayer_r_to_gb": WidgetSpec(
            label="R→GB 跨层抑制",
            tooltip="R 层对 G、B 层的 DIR 抑制（g_R→G，g_R→B）",
            min_value=0,
            max_value=1,
            step=0.01,
        ),
        "gamma_interlayer_g_to_rb": WidgetSpec(
            label="G→RB 跨层抑制",
            tooltip="G 层对 R、B 层的 DIR 抑制（g_G→R，g_G→B）",
            min_value=0,
            max_value=1,
            step=0.01,
        ),
        "gamma_interlayer_b_to_rg": WidgetSpec(
            label="B→RG 跨层抑制",
            tooltip="B 层对 R、G 层的 DIR 抑制（g_B→R，g_B→G）",
            min_value=0,
            max_value=1,
            step=0.01,
        ),
        "diffusion_size_um": WidgetSpec(
            label="扩散尺寸 um",
            tooltip="耦合剂扩散的 sigma（微米，5-20um），控制锐度并影响饱和度",
            min_value=0,
            max_value=50,
            step=1,
            decimals=0,
        ),
    },
    "grain": {
        "active": WidgetSpec(label="开关", tooltip="为负片添加颗粒"),
        "sublayers_active": WidgetSpec(label="子层开关", tooltip="启用颗粒子层模拟，关闭后颗粒分布更均匀但细节减少"),
        "particle_area_um2": WidgetSpec(
            label="颗粒大小 (um²)",
            tooltip="颗粒面积（平方微米），与 ISO 相关。ISO 100 约 0.1，ISO 400 约 0.4，ISO 3200 约 1.5",
            step=0.05,
            min_value=0,
            max_value=2,
        ),
        "particle_scale": WidgetSpec(
            label="RGB 层颗粒比例",
            tooltip="RGB 三层颗粒面积的独立缩放系数，乘以颗粒面积",
            min_value=0,
            max_value=5,
            step=0.05,
        ),
        "particle_scale_layers": WidgetSpec(
            label="子层缩放 [R,G,B]",
            tooltip="每个颜色层内各子层颗粒面积的缩放系数",
            min_value=0,
            max_value=5,
            step=0.1,
        ),
        "density_min": WidgetSpec(
            label="最小密度 [R,G,B]",
            tooltip="颗粒最小密度（基础雾度），典型值 0.03-0.06",
            min_value=0,
            max_value=0.2,
            step=0.005,
            decimals=3,
        ),
        "uniformity": WidgetSpec(
            label="均匀度 [R,G,B]",
            tooltip="颗粒分布均匀度，典型值 0.94-0.98，越低颗粒越不规则",
            min_value=0.8,
            max_value=1.0,
            step=0.005,
            decimals=3,
        ),
        "blur": WidgetSpec(
            label="颗粒柔化",
            tooltip="高斯模糊 sigma（像素），控制颗粒的软硬感。高分辨率建议 0.8–0.9，低分辨率可降至 0.6",
            min_value=0,
            max_value=2,
            step=0.05,
        ),
        "blur_dye_clouds_um": WidgetSpec(
            label="颗粒晕染",
            tooltip="颗粒边缘的渗透扩散程度（微米）。调高让颗粒互相融合，调低颗粒更分明清晰",
            min_value=0,
            max_value=3,
            step=0.05,
        ),
        "micro_structure": WidgetSpec(
            label="微结构",
            tooltip="分子级团簇微结构参数，[模糊 sigma / 极限分辨率（默认 0.10um），团簇尺寸（nm，默认 30nm）]。仅用于极端放大倍率。",
            min_value=0,
            step=0.05,
        ),
    },
    "preflashing": {
        "exposure": WidgetSpec(
            label="预闪曝光量",
            tooltip="印放预闪曝光量（EV），典型值 0.01-0.1，超过 0.3 会明显降低对比度",
            step=0.005,
            min_value=0,
            max_value=0.5,
            decimals=3,
        ),
        "y_filter_shift": WidgetSpec(
            label="Y 滤镜偏移",
            tooltip="预闪时放大机 Y 滤镜从中性位置的偏移量，典型值 -20 到 20，单位 Kodak CC",
            min_value=-50,
            max_value=50,
            step=1,
            decimals=0,
        ),
        "m_filter_shift": WidgetSpec(
            label="M 滤镜偏移",
            tooltip="预闪时放大机 M 滤镜从中性位置的偏移量，典型值 -20 到 20，单位 Kodak CC",
            min_value=-50,
            max_value=50,
            step=1,
            decimals=0,
        ),
    },
    "input_image": {
        "crop": WidgetSpec(label="裁剪", tooltip="将图像裁剪到原始尺寸的一部分，以全尺寸预览细节"),
        "crop_center": WidgetSpec(
            label="裁剪中心",
            tooltip="裁剪区域中心的相对坐标 x, y（0-1）",
            step=0.01,
            min_value=0,
            max_value=1,
        ),
        "crop_size": WidgetSpec(
            label="裁剪尺寸",
            tooltip="裁剪区域的归一化尺寸 x, y（0-1），以长边比例表示",
            step=0.01,
            min_value=0,
            max_value=1,
        ),
        "input_color_space": WidgetSpec(
            label="输入色彩空间",
            tooltip="输入图像的色彩空间，内部会转换为 sRGB，负值将被截断",
        ),
        "apply_cctf_decoding": WidgetSpec(
            label="应用 CCTF 解码",
            tooltip="应用色彩空间的逆 CCTF 传递函数",
        ),
        "upscale_factor": WidgetSpec(label="放大系数", tooltip="放大图像尺寸以提高分辨率",
                                     min_value=0.5,
                                     max_value=3,
                                     step=0.5,
                                     decimals=1,
                                     ),
        "spectral_upsampling_method": WidgetSpec(
            label="光谱上采样方法",
            tooltip="图像光谱分辨率上采样方法。hanatos2025 支持完整可见光域；mallett2019 仅支持 sRGB（超出范围会截断）",
        ),
        "apply_hanatos2025_adaptation_window": WidgetSpec(
            label="hanatos2025 适应窗口",
            tooltip="重建光谱时应用 hanatos2025 带通适应窗口",
        ),
        "apply_hanatos2025_adaptation_surface": WidgetSpec(
            label="hanatos2025 适应曲面",
            tooltip="重建光谱时应用 hanatos2025 曲面适应多项式",
        ),
        "spectral_gaussian_blur": WidgetSpec(
            label="光谱高斯模糊",
            tooltip="对重建光谱应用高斯模糊的 sigma 值（nm），超过 5nm 会明显影响光谱精度",
            min_value=0,
            max_value=5,
            step=0.1,
        ),
        "filter_uv": WidgetSpec(
            label="UV 滤镜",
            tooltip="过滤紫外光（幅度、截止波长 nm、sigma nm），主要用于防止 UV 光破坏红色。修改此项会影响放大机滤镜中性点。",
            min_value=0,
            max_value=800,
            step=1,
            decimals=0,
        ),
        "filter_ir": WidgetSpec(
            label="IR 滤镜",
            tooltip="过滤红外光（幅度、截止波长 nm、sigma nm）。修改此项会影响放大机滤镜中性点。",
            min_value=0,
            max_value=800,
            step=1,
            decimals=0,
        ),
    },
    "load_raw": {
        "white_balance": WidgetSpec(
            label="白平衡",
            tooltip="选择白平衡设置，选择自定义时可调节色温和色调",
        ),
        "temperature": WidgetSpec(
            label="色温",
            tooltip="自定义白平衡的色温（开尔文），其他白平衡模式下不生效",
            step=50,
            min_value=1000,
            max_value=10000,
            decimals=0,
        ),
        "tint": WidgetSpec(
            label="色调",
            tooltip="自定义白平衡的色调值，其他白平衡模式下不生效",
            min_value=0,
            max_value=2,
            step=0.01,
        ),
        "lens_correction": WidgetSpec(label="镜头校正", tooltip="应用镜头畸变校正"),
    },
}


GUI_AUXILIARY_SPECS = {
    "scan_for_print": WidgetSpec(
        label="为印放扫描",
        tooltip="为印放模式扫描，即扫描仪白点和黑点校正均启用，眩光关闭",
    ),
}


GUI_BUTTON_SPECS = {
    "preview": ButtonSpec(
        text="预览",
        tooltip="快速预览效果（约 2-4 秒）。日常调参用这个，不需要每次都扫描。\n注意：预览模式下颗粒、Halation、镜头模糊、锐化蒙版均关闭，看到的效果与最终扫描结果有差异。",
        preserve_case=True,
    ),
    "scan": ButtonSpec(
        text="全分辨率扫描",
        tooltip="在原始分辨率上运行完整模拟（10-30 秒，取决于图像大小）。确认效果后再扫描，然后保存。",
        preserve_case=True,
    ),
    "save": ButtonSpec(
        text="保存",
        tooltip="保存输出图像。如果已有全分辨率扫描结果，直接保存，无需重新计算。",
        preserve_case=True,
    ),
}


EMPTY_WIDGET_SPEC = WidgetSpec()


def get_widget_spec(section_name: str, field_name: str) -> WidgetSpec:
    return GUI_WIDGET_SPECS.get(section_name, {}).get(field_name, EMPTY_WIDGET_SPEC)


def get_auxiliary_spec(name: str) -> WidgetSpec:
    return GUI_AUXILIARY_SPECS.get(name, EMPTY_WIDGET_SPEC)


def get_button_spec(name: str) -> ButtonSpec:
    return GUI_BUTTON_SPECS[name]
