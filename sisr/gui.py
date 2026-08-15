#!/usr/bin/env python3
"""
Simple Image Sequence Renderer (SISR) GUI.

This module provides a graphical user interface for the SISR application,
allowing users to:
- Select input and output directories
- Choose crop options (Instagram, HD, UHD)
- Add overlays (date, frame)
- Set quality and frame rate options
- Monitor rendering progress
"""

import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

from PyQt6.QtCore import QEvent, QObject, QSize, Qt, QThread, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QCloseEvent,
    QFocusEvent,
    QFont,
    QIcon,
    QPalette,
    QPixmap,
    QValidator,
)
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStyleFactory,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .core import (
    create_video_with_overlay,
    find_image_directories,
    create_date_files,
    UnprocessableImageSequenceError,
    RenderCancelled,
    format_batch_render_summary,
)
from .preferences import load_prefs, save_prefs
from .utils import resource_path

# Crop dropdown: (label shown in UI, internal key, helper copy)
CROP_ENTRIES: List[Tuple[str, str, str]] = [
    (
        "None",
        "none",
        "Keep the full frame. Optionally scale with max width and height.",
    ),
    (
        "Instagram",
        "instagram",
        "1080×1920 portrait (9:16). Position and max size are not used.",
    ),
    (
        "HD",
        "hd",
        "1920×1080 landscape (16:9). Choose which part of the frame to keep.",
    ),
    (
        "UHD",
        "uhd",
        "3840×2160 landscape (16:9). Choose which part of the frame to keep.",
    ),
]
CROP_HINTS: Dict[str, str] = {key: hint for _label, key, hint in CROP_ENTRIES}

# Position dropdown: label -> API segment (hd_center / uhd_* use these)
POSITION_LABEL_TO_API: Dict[str, str] = {
    "": "",
    "Center": "center",
    "Keep top": "keep_top",
    "Keep bottom": "keep_bottom",
}
POSITION_DISPLAY_VALUES: Tuple[str, ...] = (
    "",
    "Center",
    "Keep top",
    "Keep bottom",
)
HD_UHD_POSITIONS: Tuple[str, ...] = ("Center", "Keep top", "Keep bottom")

QUALITY_LABEL_TO_KEY: Dict[str, str] = {
    "Default (H.264)": "default",
    "ProRes": "prores",
    "ProRes HQ": "proreshq",
    "GIF": "gif",
}

APP_CHROME_STYLE = """
QWidget#CentralRoot, QScrollArea#PageScroll, QWidget#ScrollInner {
    background: palette(window);
    border: none;
}
QFrame#SettingsCard {
    background: palette(base);
    border: 1px solid palette(mid);
    border-radius: 10px;
}
QFrame#RowDivider {
    background: palette(mid);
    border: none;
    max-height: 1px;
    min-height: 1px;
}
QLabel#HeroKicker {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.6px;
}
QLabel#HeroTitle {
    font-size: 22px;
    font-weight: 700;
}
QLabel#HeroSubtitle {
    font-size: 13px;
}
QLabel#GroupTitle {
    font-size: 13px;
    font-weight: 600;
}
QLabel#RowLabel {
    font-size: 13px;
}
QLabel#HintLabel {
    font-size: 11px;
}
QFrame#FooterBar {
    background: palette(window);
    border: none;
}
QProgressBar#RenderProgress {
    border: 1px solid palette(mid);
    border-radius: 6px;
    background: palette(base);
    text-align: center;
    min-height: 18px;
    max-height: 18px;
    color: palette(text);
}
QProgressBar#RenderProgress::chunk {
    background-color: palette(highlight);
    border-radius: 5px;
}
"""


def _font(
    point_size: int,
    weight: QFont.Weight = QFont.Weight.Normal,
) -> QFont:
    font = QFont()
    font.setPointSize(point_size)
    font.setWeight(weight)
    return font


def _muted(label: QLabel) -> None:
    label.setForegroundRole(QPalette.ColorRole.PlaceholderText)


class AutoSpinBox(QSpinBox):
    """Optional pixel size: empty/0 shows a placeholder, not the word Auto."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setRange(0, 16384)
        self.setSingleStep(2)
        self.setValue(0)
        self.lineEdit().setPlaceholderText("Auto")

    def textFromValue(self, value: int) -> str:
        if value == 0:
            return ""
        return super().textFromValue(value)

    def valueFromText(self, text: str) -> int:
        stripped = text.strip()
        if not stripped:
            return 0
        return super().valueFromText(stripped)

    def validate(self, text: str, pos: int):
        if text.strip() == "":
            return (QValidator.State.Acceptable, text, pos)
        return super().validate(text, pos)

    def focusInEvent(self, event: QFocusEvent) -> None:
        super().focusInEvent(event)
        if self.value() == 0:
            self.lineEdit().clear()
        else:
            self.lineEdit().selectAll()


class SettingsGroup(QWidget):
    """A titled, rounded group in the style of macOS Settings."""

    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        heading = QLabel(title)
        heading.setObjectName("GroupTitle")
        heading.setFont(_font(13, QFont.Weight.DemiBold))
        outer.addWidget(heading)

        self._card = QFrame()
        self._card.setObjectName("SettingsCard")
        self._card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._rows = QVBoxLayout(self._card)
        self._rows.setContentsMargins(14, 4, 14, 4)
        self._rows.setSpacing(0)
        outer.addWidget(self._card)
        self._row_count = 0

    def add_row(
        self,
        label: str,
        field: QWidget,
        hint: Optional[QLabel] = None,
    ) -> None:
        if self._row_count:
            divider = QFrame()
            divider.setObjectName("RowDivider")
            divider.setFixedHeight(1)
            self._rows.addWidget(divider)

        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(12)

        name = QLabel(label)
        name.setObjectName("RowLabel")
        name.setMinimumWidth(118)
        name.setMaximumWidth(118)
        name.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        layout.addWidget(name)
        field.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        layout.addWidget(field, 1)
        self._rows.addWidget(row)

        if hint is not None:
            hint.setObjectName("HintLabel")
            hint.setWordWrap(True)
            _muted(hint)
            hint.setContentsMargins(130, 0, 4, 8)
            self._rows.addWidget(hint)

        self._row_count += 1


class RenderWorker(QObject):
    """Runs a batch render off the UI thread."""

    progress = pyqtSignal(float, str)
    status = pyqtSignal(str)
    finished_info = pyqtSignal(str, str)
    finished_warning = pyqtSignal(str, str)
    finished_error = pyqtSignal(str, str)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()
    done = pyqtSignal()

    def __init__(
        self,
        input_dir: str,
        output_dir: str,
        crop_type: Optional[str],
        overlay_type: Optional[str],
        quality: str,
        fps: float,
        max_width: Optional[int],
        max_height: Optional[int],
    ) -> None:
        super().__init__()
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.crop_type = crop_type
        self.overlay_type = overlay_type
        self.quality = quality
        self.fps = fps
        self.max_width = max_width
        self.max_height = max_height
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            image_dirs = find_image_directories(self.input_dir)
            if not image_dirs:
                self.failed.emit("No image directories found")
                return
            skipped: List[Tuple[str, str]] = []
            rendered_count = 0
            for dir_path in image_dirs:
                if self._cancel:
                    self.cancelled.emit()
                    return
                dir_name = os.path.basename(dir_path)
                output_file = os.path.join(self.output_dir, f"{dir_name}.mp4")
                if self.overlay_type == "date":
                    image_date_files = create_date_files(
                        dir_path,
                        self.output_dir,
                    )
                else:
                    image_files = [
                        f
                        for f in sorted(os.listdir(dir_path))
                        if not f.startswith(".")
                        and f.lower().endswith(
                            (".jpg", ".jpeg", ".png", ".tiff", ".bmp")
                        )
                    ]
                    image_date_files = [
                        (os.path.join(dir_path, f), None) for f in image_files
                    ]
                if not image_date_files:
                    skipped.append(
                        (
                            dir_name,
                            "No image files were found that can be "
                            "rendered as a sequence.",
                        )
                    )
                    self.status.emit(
                        f"Skipping {dir_name}: no processable image sequence"
                    )
                    continue
                self.status.emit(f"Processing {dir_name}…")

                def progress_callback(
                    frame: int, total: int, name: str = dir_name
                ) -> None:
                    percent = (frame / total) * 100 if total else 0
                    self.progress.emit(
                        percent,
                        f"Processing {name}… {percent:.1f}%",
                    )

                try:
                    create_video_with_overlay(
                        image_date_files=image_date_files,
                        output_file=output_file,
                        fps=self.fps,
                        crop_type=self.crop_type,
                        overlay_type=self.overlay_type,
                        quality=self.quality,
                        max_width=self.max_width,
                        max_height=self.max_height,
                        progress_callback=progress_callback,
                        cancel_requested=lambda: self._cancel,
                    )
                except RenderCancelled:
                    self.cancelled.emit()
                    return
                except UnprocessableImageSequenceError as e:
                    skipped.append((dir_name, str(e)))
                    self.status.emit(
                        f"Skipping {dir_name}: no processable image sequence"
                    )
                    continue
                rendered_count += 1
            summary = format_batch_render_summary(rendered_count, skipped)
            if rendered_count and skipped:
                self.finished_warning.emit(
                    (
                        f"Rendering finished: {rendered_count} ok, "
                        f"{len(skipped)} skipped"
                    ),
                    summary,
                )
            elif skipped:
                self.finished_error.emit(
                    "No folders could be rendered",
                    summary,
                )
            else:
                self.finished_info.emit(
                    "Rendering completed successfully",
                    summary,
                )
        except Exception as e:  # noqa: BLE001 — show render failures in UI
            self.failed.emit(str(e))
        finally:
            self.done.emit()


class SISRGUI(QMainWindow):
    """Main window for the Simple Image Sequence Renderer."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Simple Image Sequence Renderer")
        self.setMinimumSize(QSize(640, 720))
        self.resize(680, 820)
        self.setStyleSheet(APP_CHROME_STYLE)

        png = resource_path("icons", "icon_128x128.png")
        if os.path.isfile(png):
            self.setWindowIcon(QIcon(png))

        self.prefs: Dict[str, Any] = load_prefs()
        self.input_dir: Optional[str] = self.prefs.get("input_dir")
        self.output_dir: Optional[str] = self.prefs.get("output_dir")

        self._worker: Optional[RenderWorker] = None
        self._thread: Optional[QThread] = None

        self._build_menu()
        self._build_ui()
        self._sync_crop_controls()

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        choose_input = QAction("Choose Input Folder…", self)
        choose_input.setShortcut("Ctrl+O")
        choose_input.triggered.connect(self.select_input_dir)
        file_menu.addAction(choose_input)

        choose_output = QAction("Choose Output Folder…", self)
        choose_output.setShortcut("Ctrl+Shift+O")
        choose_output.triggered.connect(self.select_output_dir)
        file_menu.addAction(choose_output)

        file_menu.addSeparator()

        start_action = QAction("Start Rendering", self)
        start_action.setShortcut("Ctrl+Return")
        start_action.triggered.connect(self.start_render)
        file_menu.addAction(start_action)

        self._cancel_action = QAction("Cancel Rendering", self)
        self._cancel_action.setShortcut("Ctrl+.")
        self._cancel_action.setEnabled(False)
        self._cancel_action.triggered.connect(self.cancel_render)
        file_menu.addAction(self._cancel_action)

        help_menu = self.menuBar().addMenu("&Help")
        about = QAction("About SISR", self)
        about.triggered.connect(self._show_about)
        help_menu.addAction(about)

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("CentralRoot")
        self.setCentralWidget(central)
        shell = QVBoxLayout(central)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("PageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
        )
        shell.addWidget(scroll, 1)

        page = QWidget()
        page.setObjectName("ScrollInner")
        scroll.setWidget(page)
        root = QVBoxLayout(page)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(18)

        root.addLayout(self._build_header())

        locations = SettingsGroup("Locations")
        self.input_dir_edit = QLineEdit(self.input_dir or "")
        self.input_dir_edit.setPlaceholderText("Folder of image sequences")
        self.input_dir_edit.setClearButtonEnabled(True)
        self.input_dir_edit.editingFinished.connect(self._on_input_edited)
        locations.add_row(
            "Input",
            self._path_row(self.input_dir_edit, self.select_input_dir),
        )
        self.output_dir_edit = QLineEdit(self.output_dir or "")
        self.output_dir_edit.setPlaceholderText("Save videos here")
        self.output_dir_edit.setClearButtonEnabled(True)
        self.output_dir_edit.editingFinished.connect(self._on_output_edited)
        locations.add_row(
            "Output",
            self._path_row(self.output_dir_edit, self.select_output_dir),
        )
        root.addWidget(locations)

        framing = SettingsGroup("Framing")
        self.crop_combo = QComboBox()
        for label, key, _hint in CROP_ENTRIES:
            self.crop_combo.addItem(label, key)
        self.crop_combo.currentIndexChanged.connect(self._sync_crop_controls)
        self.crop_hint = QLabel()
        framing.add_row("Crop", self.crop_combo, self.crop_hint)

        self.crop_position_combo = QComboBox()
        self.crop_position_combo.addItems(POSITION_DISPLAY_VALUES)
        framing.add_row("Position", self.crop_position_combo)

        self.max_width_spin = self._auto_spin()
        self.max_height_spin = self._auto_spin()
        max_row = QWidget()
        max_layout = QHBoxLayout(max_row)
        max_layout.setContentsMargins(0, 0, 0, 0)
        max_layout.setSpacing(8)
        max_layout.addWidget(self.max_width_spin)
        times = QLabel("×")
        times.setAlignment(Qt.AlignmentFlag.AlignCenter)
        max_layout.addWidget(times)
        max_layout.addWidget(self.max_height_spin)
        self.max_dim_note = QLabel()
        framing.add_row("Max size", max_row, self.max_dim_note)
        root.addWidget(framing)

        render = SettingsGroup("Render")
        self.overlay_combo = QComboBox()
        self.overlay_combo.addItems(("None", "Date", "Frame"))
        overlay_hint = QLabel("Date uses EXIF; Frame adds a counter.")
        render.add_row("Overlay", self.overlay_combo, overlay_hint)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(tuple(QUALITY_LABEL_TO_KEY.keys()))
        quality_hint = QLabel(
            "Default is high-quality H.264. ProRes writes a .mov file."
        )
        render.add_row("Quality", self.quality_combo, quality_hint)

        default_fps = float(self.prefs.get("fps", 30) or 30)
        self.fps_spin = QDoubleSpinBox()
        self.fps_spin.setRange(0.01, 240.0)
        self.fps_spin.setDecimals(2)
        self.fps_spin.setSingleStep(1.0)
        self.fps_spin.setValue(default_fps)
        self.fps_spin.setSuffix(" fps")
        self.fps_spin.setMaximumWidth(140)
        fps_wrap = QWidget()
        fps_layout = QHBoxLayout(fps_wrap)
        fps_layout.setContentsMargins(0, 0, 0, 0)
        fps_layout.addWidget(self.fps_spin)
        fps_layout.addStretch(1)
        render.add_row("Frame rate", fps_wrap)
        root.addWidget(render)
        root.addStretch(1)

        footer = QFrame()
        footer.setObjectName("FooterBar")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(24, 12, 24, 16)
        footer_layout.setSpacing(10)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("HintLabel")
        self.status_label.setWordWrap(True)
        _muted(self.status_label)
        footer_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("RenderProgress")
        fusion = QStyleFactory.create("Fusion")
        if fusion is not None:
            self.progress_bar.setStyle(fusion)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setMinimumHeight(18)
        footer_layout.addWidget(self.progress_bar)

        action_row = QHBoxLayout()
        action_row.setSpacing(12)
        action_row.addStretch(1)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setAutoDefault(False)
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.setMinimumHeight(28)
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self.cancel_render)
        action_row.addWidget(self.cancel_button)
        self.start_button = QPushButton("Start Rendering")
        self.start_button.setDefault(True)
        self.start_button.setAutoDefault(True)
        self.start_button.setMinimumWidth(168)
        self.start_button.setMinimumHeight(28)
        self.start_button.clicked.connect(self.start_render)
        action_row.addWidget(self.start_button)
        footer_layout.addLayout(action_row)
        shell.addWidget(footer)

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(14)

        icon_label = QLabel()
        png = resource_path("icons", "icon_128x128.png")
        if os.path.isfile(png):
            pixmap = QPixmap(png).scaled(
                56,
                56,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_label.setPixmap(pixmap)
            icon_label.setFixedSize(56, 56)
        header.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)

        titles = QVBoxLayout()
        titles.setSpacing(2)
        kicker = QLabel("SISR")
        kicker.setObjectName("HeroKicker")
        kicker.setFont(_font(11, QFont.Weight.DemiBold))
        accent = getattr(QPalette.ColorRole, "Accent", QPalette.ColorRole.Link)
        kicker.setForegroundRole(accent)
        titles.addWidget(kicker)

        title = QLabel("Simple Image Sequence Renderer")
        title.setObjectName("HeroTitle")
        title.setFont(_font(22, QFont.Weight.Bold))
        title.setWordWrap(True)
        titles.addWidget(title)

        subtitle = QLabel("Turn image sequences into video or GIF.")
        subtitle.setObjectName("HeroSubtitle")
        subtitle.setFont(_font(13))
        subtitle.setWordWrap(True)
        _muted(subtitle)
        titles.addWidget(subtitle)
        header.addLayout(titles, 1)
        return header

    def _auto_spin(self) -> AutoSpinBox:
        return AutoSpinBox()

    def _path_row(
        self,
        field: QLineEdit,
        choose: Callable[[], None],
    ) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        field.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        layout.addWidget(field)
        button = QPushButton("Choose…")
        button.setAutoDefault(False)
        button.clicked.connect(choose)
        layout.addWidget(button)
        return row

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About SISR",
            (
                "Simple Image Sequence Renderer\n"
                f"Version {__version__}\n\n"
                "Convert image sequences into video, ProRes, or GIF."
            ),
        )

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.PaletteChange:
            self.setStyleSheet(APP_CHROME_STYLE)
        super().changeEvent(event)

    def _on_input_edited(self) -> None:
        path = self.input_dir_edit.text().strip()
        self.input_dir = path or None
        if path:
            self.prefs["input_dir"] = path
            save_prefs(self.prefs)

    def _on_output_edited(self) -> None:
        path = self.output_dir_edit.text().strip()
        self.output_dir = path or None
        if path:
            self.prefs["output_dir"] = path
            save_prefs(self.prefs)

    def select_input_dir(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Choose Input Folder",
            self.input_dir or "",
            QFileDialog.Option.ShowDirsOnly,
        )
        if dir_path:
            self.input_dir_edit.setText(dir_path)
            self.input_dir = dir_path
            self.prefs["input_dir"] = dir_path
            save_prefs(self.prefs)
            if not find_image_directories(dir_path):
                QMessageBox.warning(
                    self,
                    "No Images Found",
                    "No image files were found in the selected folder.",
                )

    def select_output_dir(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Choose Output Folder",
            self.output_dir or "",
            QFileDialog.Option.ShowDirsOnly,
        )
        if dir_path:
            self.output_dir_edit.setText(dir_path)
            self.output_dir = dir_path
            self.prefs["output_dir"] = dir_path
            save_prefs(self.prefs)
            os.makedirs(dir_path, exist_ok=True)

    def _sync_crop_controls(self) -> None:
        key = str(self.crop_combo.currentData() or "none")
        self.crop_hint.setText(CROP_HINTS.get(key, ""))

        if key == "none":
            self.max_width_spin.setEnabled(True)
            self.max_height_spin.setEnabled(True)
            self.max_dim_note.setText("Auto keeps the original image size.")
            self.crop_position_combo.clear()
            self.crop_position_combo.addItems(POSITION_DISPLAY_VALUES)
            self.crop_position_combo.setCurrentIndex(0)
            self.crop_position_combo.setEnabled(False)
        elif key == "instagram":
            self.max_width_spin.setEnabled(False)
            self.max_height_spin.setEnabled(False)
            self.max_dim_note.setText("Size is fixed by this crop preset.")
            self.crop_position_combo.clear()
            self.crop_position_combo.addItems(POSITION_DISPLAY_VALUES)
            self.crop_position_combo.setCurrentIndex(0)
            self.crop_position_combo.setEnabled(False)
        else:
            self.max_width_spin.setEnabled(False)
            self.max_height_spin.setEnabled(False)
            self.max_dim_note.setText(
                "Output size is fixed by the selected crop preset."
            )
            current = self.crop_position_combo.currentText()
            self.crop_position_combo.clear()
            self.crop_position_combo.addItems(HD_UHD_POSITIONS)
            self.crop_position_combo.setEnabled(True)
            if current in HD_UHD_POSITIONS:
                self.crop_position_combo.setCurrentText(current)
            else:
                self.crop_position_combo.setCurrentText("Center")

    def get_crop_type(self) -> Optional[str]:
        key = str(self.crop_combo.currentData() or "none")
        if key == "none":
            return None
        if key == "instagram":
            return "instagram"
        pos_label = self.crop_position_combo.currentText()
        api_pos = POSITION_LABEL_TO_API.get(pos_label, "")
        if key == "hd":
            if not api_pos:
                raise ValueError("Select a crop position for HD output.")
            return f"hd_{api_pos}"
        if key == "uhd":
            if not api_pos:
                raise ValueError("Select a crop position for UHD output.")
            return f"uhd_{api_pos}"
        return None

    def get_overlay_type(self) -> Optional[str]:
        overlay_type = self.overlay_combo.currentText()
        if overlay_type == "None":
            return None
        return overlay_type.lower()

    def get_quality(self) -> str:
        return QUALITY_LABEL_TO_KEY.get(
            self.quality_combo.currentText(),
            "default",
        )

    def get_max_width(self) -> Optional[int]:
        value = int(self.max_width_spin.value())
        return value if value > 0 else None

    def get_max_height(self) -> Optional[int]:
        value = int(self.max_height_spin.value())
        return value if value > 0 else None

    def get_fps(self) -> float:
        fps = float(self.fps_spin.value())
        if fps <= 0:
            raise ValueError("Frame rate must be positive")
        return fps

    def start_render(self) -> None:
        self._on_input_edited()
        self._on_output_edited()
        if not self.input_dir or not self.output_dir:
            QMessageBox.critical(
                self,
                "Missing Folders",
                "Please select both input and output folders.",
            )
            return
        try:
            fps = self.get_fps()
            crop_type = self.get_crop_type()
        except ValueError as e:
            QMessageBox.critical(self, "Invalid Setting", str(e))
            return
        self.prefs["fps"] = fps
        save_prefs(self.prefs)

        if self._thread is not None and self._thread.isRunning():
            return

        self.start_button.setEnabled(False)
        self.cancel_button.setVisible(True)
        self.cancel_button.setEnabled(True)
        self._cancel_action.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting rendering…")

        worker = RenderWorker(
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            crop_type=crop_type,
            overlay_type=self.get_overlay_type(),
            quality=self.get_quality(),
            fps=fps,
            max_width=self.get_max_width(),
            max_height=self.get_max_height(),
        )
        thread = QThread(self)
        worker.moveToThread(thread)
        worker.progress.connect(self._on_progress)
        worker.status.connect(self.status_label.setText)
        worker.finished_info.connect(self._on_finished_info)
        worker.finished_warning.connect(self._on_finished_warning)
        worker.finished_error.connect(self._on_finished_error)
        worker.failed.connect(self._on_failed)
        worker.cancelled.connect(self._on_cancelled)
        worker.done.connect(thread.quit)
        thread.started.connect(worker.run)
        thread.finished.connect(worker.deleteLater)
        self._worker = worker
        self._thread = thread
        thread.start()

    def cancel_render(self) -> None:
        if self._worker is None:
            return
        self._worker.cancel()
        self.cancel_button.setEnabled(False)
        self._cancel_action.setEnabled(False)
        self.status_label.setText("Cancelling…")

    def _on_progress(self, percent: float, text: str) -> None:
        self.progress_bar.setValue(int(percent))
        self.status_label.setText(text)

    def _finish_render_ui(self) -> None:
        self.start_button.setEnabled(True)
        self.cancel_button.setVisible(False)
        self.cancel_button.setEnabled(True)
        self._cancel_action.setEnabled(False)
        self.progress_bar.setValue(0)

    def _on_cancelled(self) -> None:
        self.status_label.setText("Cancelled")
        self._finish_render_ui()

    def _on_finished_info(self, status: str, message: str) -> None:
        self.status_label.setText(status)
        self._finish_render_ui()
        QMessageBox.information(self, "Success", message)

    def _on_finished_warning(self, status: str, message: str) -> None:
        self.status_label.setText(status)
        self._finish_render_ui()
        QMessageBox.warning(
            self,
            "Rendering finished with skipped folders",
            message,
        )

    def _on_finished_error(self, status: str, message: str) -> None:
        self.status_label.setText(status)
        self._finish_render_ui()
        QMessageBox.critical(self, "No processable image sequences", message)

    def _on_failed(self, text: str) -> None:
        self.status_label.setText("Error during rendering")
        self._finish_render_ui()
        QMessageBox.critical(self, "Error", text)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._worker is not None:
            self._worker.cancel()
        if self._thread is not None and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)
        super().closeEvent(event)


def main() -> None:
    """Main entry point for the GUI application."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    app.setApplicationName("SISR")
    app.setApplicationDisplayName("SISR")
    app.setOrganizationName("Timelapse Tech")
    if sys.platform == "darwin":
        app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, True)
        app.setStyle("macos")

    png = resource_path("icons", "icon_128x128.png")
    if os.path.isfile(png):
        app.setWindowIcon(QIcon(png))

    window = SISRGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
