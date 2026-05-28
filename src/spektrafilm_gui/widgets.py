from dataclasses import dataclass

from spektrafilm_gui.widget_primitives import CollapsibleSection, platform_default_font
from spektrafilm_gui.widget_sections import (
    CameraSection,
    CameraDiffusionSection,
    CouplersSection,
    DisplaySection,
    DiffusionSection,
    EnlargerSection,
    ExposureControlSection,
    FilePickerSection,
    GlareSection,
    GrainCropPreviewWidget,
    GrainSection,
    GuiConfigSection,
    HalationSection,
    InputImageSection,
    LoadRawSection,
    OutputSection,
    PreflashingSection,
    PresetPanelSection,
    PreviewCropSection,
    ScannerSection,
    SimulationSection,
    SpecialSection,
    SpectralUpsamplingSection,
    TuneSection,
)


@dataclass(slots=True)
class WidgetBundle:
    filepicker: FilePickerSection
    gui_config: GuiConfigSection
    display: DisplaySection
    input_image: InputImageSection
    load_raw: LoadRawSection
    grain: GrainSection
    grain_crop_preview: GrainCropPreviewWidget
    preflashing: PreflashingSection
    diffusion: DiffusionSection
    camera_diffusion: CameraDiffusionSection
    halation: HalationSection
    couplers: CouplersSection
    glare: GlareSection
    special: SpecialSection
    simulation: SimulationSection
    preview_crop: PreviewCropSection
    camera: CameraSection
    exposure_control: ExposureControlSection
    enlarger: EnlargerSection
    scanner: ScannerSection
    spectral_upsampling: SpectralUpsamplingSection
    tune: TuneSection
    output: OutputSection
    preset_panel: PresetPanelSection


def create_widget_bundle() -> WidgetBundle:
    filepicker = FilePickerSection()
    input_image = InputImageSection(filepicker)
    simulation = SimulationSection()
    special = SpecialSection(simulation)
    glare = GlareSection()
    scanner = ScannerSection(simulation)
    simulation.bind_scan_for_print_glare_section(glare)

    return WidgetBundle(
        filepicker=filepicker,
        gui_config=GuiConfigSection(),
        display=DisplaySection(),
        input_image=input_image,
        load_raw=LoadRawSection(),
        grain=GrainSection(),
        grain_crop_preview=GrainCropPreviewWidget(),
        preflashing=PreflashingSection(),
        diffusion=DiffusionSection(simulation),
        camera_diffusion=CameraDiffusionSection(simulation),
        halation=HalationSection(),
        couplers=CouplersSection(),
        glare=glare,
        special=special,
        simulation=simulation,
        preview_crop=PreviewCropSection(input_image),
        camera=CameraSection(simulation),
        exposure_control=ExposureControlSection(simulation),
        enlarger=EnlargerSection(simulation),
        scanner=scanner,
        spectral_upsampling=SpectralUpsamplingSection(input_image),
        tune=TuneSection(special),
        output=OutputSection(simulation),
        preset_panel=PresetPanelSection(),
    )