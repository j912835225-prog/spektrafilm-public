# Spektrafilm — 胶片成像的物理模拟

**[English below](#english)**

---

这个项目脱胎于 [@andreavolpato](https://github.com/andreavolpato) 在瑞典 KTH 皇家理工学院的研究工作。

他在研究工作结束后的深夜，用业余时间写出了这套物理模型。
他的目标不是模仿一种泛泛的胶片感，而是建立一个以实测数据为基础、能预测真实摄影材料行为的模型。

我们继承了他的全部算法，重新设计了界面——让中文世界的专业摄影师能够真正用上它。

---

## 这是什么

不是胶片 LUT，不是滤镜。

是从光谱数据出发的**完整物理模拟**：卤化银颗粒的随机显影、染料耦合剂的层间抑制、Halation 的背反射光晕、印放机的色温模型——每一步都有物理方程支撑。

LUT 能做到的是颜色映射。这个模型能做到的是：颗粒随曝光变化、高光自然滚降、阴影里的色彩串扰。这是胶片之所以是胶片的原因。

---

## 对专业摄影师

如果你用 Capture One 或 Lightroom 处理 RAW，这个工具可以接在你的工作流之后：

1. 导入你的 RAW 文件（或线性 TIFF）
2. 选一张底片（Portra 400、Velvia 100、Vision3……）
3. 选一张相纸（Endura、Crystal Archive……）
4. 调整印放参数，导出

结果不是「胶片风格」，是「如果你当时用的是这张底片，冲洗在这张相纸上，它会是什么样子」。

---

## 安装

**macOS：**

```bash
# 方式一：双击安装
双击 安装.command，再双击 启动.command

# 方式二：命令行
uv run spektrafilm
```

需要 Python 3.13 和 [uv](https://docs.astral.sh/uv/)。

---

## 与原项目的关系

| 部分 | 来源 |
|------|------|
| 物理算法核心（`src/spektrafilm/`） | 完整继承自 [@andreavolpato](https://github.com/andreavolpato) 的原始研究，未做修改 |
| GUI 界面（`src/spektrafilm_gui/`） | 重新设计，中文支持，专业摄影师工作流优化 |
| 胶片/相纸 profile 数据 | 来自原项目，基于厂商数据表 |

原项目地址：[github.com/andreavolpato/spektrafilm](https://github.com/andreavolpato/spektrafilm)

如果这个工具对你有用，请同时给原项目点一个 Star。那里才是这一切的起点。

---

## 致 Andrea Volpato

感谢你把这件事做出来，并且选择开源。

用业余时间、在深夜、从光谱数据开始，把胶片的化学过程写成方程——这不是一个工程决定，是一种执念。我们理解这种执念，所以我们想让更多人用上它。

我们遵守 GPLv3，所有改动公开，物理模型完整保留。
如果你看到这里，希望你认可我们做这件事的方式。

---

## License

GPL-3.0-or-later，与上游一致。

衍生作品必须同样开源。详见 [LICENSE](../LICENSE)。

---

<a name="english"></a>

## English

This project is built on top of [@andreavolpato](https://github.com/andreavolpato)'s [spektrafilm](https://github.com/andreavolpato/spektrafilm), a physically-based spectral film simulation developed at KTH Royal Institute of Technology, Sweden.

We kept the entire physics engine intact and redesigned the interface for Chinese-speaking professional photographers.

**What it does:** Simulates the complete analog photography pipeline — silver halide grain development, dye coupler interactions, halation, enlarger color balance — from spectral data. Not a LUT. Not a filter. A physical model.

**For photographers:** Load your RAW or linear TIFF, choose a film stock and paper, adjust the enlarger, export. The result is not a "film look" — it's a prediction of what your image would look like if it had been shot on that film and printed on that paper.

**Installation:**
```bash
# macOS — double-click 安装.command, then 启动.command
# or:
uv run spektrafilm
```

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/).

**To Andrea:** Thank you for building this and keeping it open. We inherit from your work with respect, and we keep it open the same way you did.

Original project: [github.com/andreavolpato/spektrafilm](https://github.com/andreavolpato/spektrafilm) — please star it there too.
