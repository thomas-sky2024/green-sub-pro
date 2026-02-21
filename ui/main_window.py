"""
GreenSub Pro – Enhanced Main Window
Features added in this revision:
  • No outline stroke by default (Outline=0)
  • Outline opacity slider (0–100 %)
  • Title-safe / action-safe overlay drawn on the preview with QPainter
  • Safe-zone aspect-ratio selector (16:9 / 9:16)
  • Remove-video / remove-subtitle buttons (single-slot, replaces generic Reset)
  • PreviewWidget: custom QWidget that owns a QLabel + loading indicator,
    rescales the stored pixmap on resize, and draws safe-zone guides on top
  • Video quality preset selector (Low / Medium / Best)
"""

import os
import platform

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QComboBox, QColorDialog,
    QSpinBox, QProgressBar, QMessageBox, QFileDialog,
    QGroupBox, QFormLayout, QListWidget, QListWidgetItem,
    QSplitter, QSizePolicy, QCheckBox, QFrame,
)
from PySide6.QtGui import (
    QPixmap, QFontDatabase, QColor, QPainter, QPen, QBrush, QFont,
    QPainterPath,
)
from PySide6.QtCore import Qt, QTimer, Signal, QSize, QRect, QRectF

from ui.drag_drop import DragDropListWidget
from core.media_engine import MediaEngine


# ═══════════════════════════════════════════════════════════════════════════
# Stylesheet
# ═══════════════════════════════════════════════════════════════════════════
DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #111114;
    color: #e4e4e8;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
}
QGroupBox {
    background-color: #1b1b22;
    border: 1px solid #2b2b38;
    border-radius: 10px;
    margin-top: 20px;
    padding: 14px 10px 10px 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #b3ff00;
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 1px;
    text-transform: uppercase;
}
QPushButton {
    background-color: #23232d;
    border: 1px solid #38384a;
    border-radius: 7px;
    padding: 6px 12px;
    color: #e4e4e8;
}
QPushButton:hover  { background-color: #2e2e3c; border-color: #4a4a60; }
QPushButton:pressed { background-color: #1a1a24; }
QPushButton:disabled { background-color: #1b1b22; color: #484858; border-color: #252530; }
QComboBox, QSpinBox {
    background-color: #18181f;
    border: 1px solid #38384a;
    border-radius: 6px;
    padding: 5px 8px;
    color: #e4e4e8;
    min-height: 26px;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox::down-arrow { image: none; }
QComboBox QAbstractItemView {
    background-color: #1b1b26;
    border: 1px solid #38384a;
    selection-background-color: #b3ff00;
    selection-color: #000;
    outline: none;
}
QLabel { background-color: transparent; }
QCheckBox { spacing: 6px; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #38384a;
    border-radius: 4px;
    background: #18181f;
}
QCheckBox::indicator:checked {
    background: #b3ff00;
    border-color: #b3ff00;
}
QSlider::groove:horizontal {
    border: none;
    height: 4px;
    background: #2b2b38;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #b3ff00;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #b3ff00;
    border: 2px solid #111114;
    width: 14px; height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover { background: #ccff33; }
QProgressBar {
    border: none;
    border-radius: 6px;
    text-align: center;
    color: #000;
    font-weight: 700;
    font-size: 11px;
    background-color: #2b2b38;
    min-height: 16px;
    max-height: 16px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #7acc00, stop:1 #b3ff00);
    border-radius: 6px;
}
QListWidget {
    background-color: #18181f;
    border: 1px solid #2b2b38;
    border-radius: 8px;
    padding: 4px;
    color: #e4e4e8;
    outline: none;
}
QListWidget::item {
    padding: 6px 10px;
    border-radius: 5px;
    margin: 1px 0;
}
QListWidget::item:selected { background-color: #b3ff00; color: #000; font-weight: 600; }
QListWidget::item:hover:!selected { background-color: #26263a; }
QScrollBar:vertical {
    background: #18181f; width: 7px; border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #38384a; border-radius: 3px; min-height: 18px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QFrame[frameShape="4"], QFrame[frameShape="5"] {   /* HLine / VLine */
    color: #2b2b38;
}
"""


# ═══════════════════════════════════════════════════════════════════════════
# PreviewWidget  – custom widget with safe-zone overlay
# ═══════════════════════════════════════════════════════════════════════════
class PreviewWidget(QWidget):
    """
    Displays a video frame preview with:
    - Proper aspect-ratio scaling on resize
    - Optional safe-zone guide overlay (title-safe 80 %, action-safe 90 %)
    - 'Loading…' label while a new frame is being generated
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self._show_safe_zone = False
        self._aspect_ratio = "16:9"   # "16:9" | "9:16"
        self._loading = False

        self.setMinimumSize(480, 270)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(
            "background:#0a0a0e;"
            "border:1px solid #2b2b38;"
            "border-radius:10px;"
        )

    # ── public API ──────────────────────────────────────────────────────

    def set_pixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self._loading = False
        self.update()

    def set_loading(self, loading: bool):
        self._loading = loading
        if loading:
            self._pixmap = None
        self.update()

    def set_safe_zone(self, enabled: bool):
        self._show_safe_zone = enabled
        self.update()

    def set_aspect_ratio(self, ar: str):
        self._aspect_ratio = ar
        self.update()

    def clear(self):
        self._pixmap = None
        self._loading = False
        self.update()

    # ── paint ────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        w, h = self.width(), self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor("#0a0a0e"))

        if self._pixmap and not self._pixmap.isNull():
            # Scale preserving aspect ratio
            scaled = self._pixmap.scaled(
                QSize(w, h), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            x = (w - scaled.width())  // 2
            y = (h - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)

            if self._show_safe_zone:
                self._draw_safe_zones(painter, x, y, scaled.width(), scaled.height())

        elif self._loading:
            painter.setPen(QColor("#555568"))
            painter.setFont(QFont("Arial", 13))
            painter.drawText(
                QRect(0, 0, w, h), Qt.AlignCenter, "Generating preview…"
            )
        else:
            painter.setPen(QColor("#404055"))
            painter.setFont(QFont("Arial", 13))
            painter.drawText(
                QRect(0, 0, w, h), Qt.AlignCenter,
                "Drop a video file\nor click '+ Video'"
            )

        painter.end()

    def _draw_safe_zones(self, painter: QPainter, ox: int, oy: int, pw: int, ph: int):
        """
        Draw title-safe (80 %) and action-safe (90 %) rectangle guides.
        Coordinates are relative to the displayed image rect (ox, oy, pw, ph).
        """
        for pct, color, label in [
            (0.90, QColor(255, 200, 0,  160), "Action Safe 90%"),
            (0.80, QColor(255, 80,  80,  160), "Title Safe 80%"),
        ]:
            mw = pw * (1 - pct) / 2
            mh = ph * (1 - pct) / 2
            rect = QRectF(ox + mw, oy + mh, pw - 2*mw, ph - 2*mh)

            pen = QPen(color, 1.2, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)

            # Label
            painter.setPen(color)
            painter.setFont(QFont("Arial", 8, QFont.Bold))
            painter.drawText(
                QRectF(rect.x() + 4, rect.y() + 2, 140, 14),
                Qt.AlignLeft | Qt.AlignVCenter,
                label,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Main Window
# ═══════════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    render_progress_signal = Signal(float, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GreenSub Pro")
        self.resize(1340, 820)
        self.setStyleSheet(DARK_STYLE)

        self.video_path:    str | None = None
        self.subtitle_path: str | None = None
        self.duration:      float = 0.0
        self.sub_color:     str = "#FFFFFF"
        self.outline_color: str = "#000000"
        self.bg_color_hex:  str = "00FF00"

        self._preview_timer = QTimer()
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._do_update_preview)

        self.render_progress_signal.connect(self._on_progress)
        self._build_ui()

    # ═══════════════════════════════════════════════════════════════════
    # UI Construction
    # ═══════════════════════════════════════════════════════════════════

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        rl = QVBoxLayout(root)
        rl.setSpacing(8)
        rl.setContentsMargins(14, 10, 14, 10)

        # ── Header ──────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.addWidget(QLabel(
            "<span style='color:#b3ff00;font-size:19px;font-weight:700;"
            "letter-spacing:-0.5px;'>GreenSub Pro</span>"
        ))
        hdr.addStretch()
        hw = QLabel("⚡ Apple Silicon" if platform.processor() == 'arm' else "🖥 Standard CPU")
        hw.setStyleSheet(
            "color:#b3ff00;font-size:11px;" if platform.processor() == 'arm'
            else "color:#888;font-size:11px;"
        )
        hdr.addWidget(hw)
        rl.addLayout(hdr)

        # ── Splitter ─────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle{background:#2b2b38;}")

        # ── LEFT PANEL ──────────────────────────────────────────────────
        left_w = QWidget()
        left_v = QVBoxLayout(left_w)
        left_v.setContentsMargins(0, 0, 0, 0)
        left_v.setSpacing(6)

        # File slots
        files_grp = QGroupBox("Media Files")
        files_v = QVBoxLayout(files_grp)
        files_v.setSpacing(6)

        # Video slot
        vid_row = QHBoxLayout()
        self._video_slot_label = QLabel("No video")
        self._video_slot_label.setStyleSheet("color:#666;font-size:11px;")
        self._video_slot_label.setWordWrap(True)
        add_vid_btn = QPushButton("+ Video")
        add_vid_btn.setFixedWidth(80)
        add_vid_btn.clicked.connect(self._browse_video)
        self._remove_vid_btn = QPushButton("✕")
        self._remove_vid_btn.setFixedWidth(30)
        self._remove_vid_btn.setEnabled(False)
        self._remove_vid_btn.setToolTip("Remove video")
        self._remove_vid_btn.setStyleSheet(
            "QPushButton{color:#ff5555;border-color:#5a2222;background:#2a1818;}"
            "QPushButton:hover{background:#3a2020;}"
            "QPushButton:disabled{color:#444;border-color:#252525;background:#1b1b22;}"
        )
        self._remove_vid_btn.clicked.connect(self._remove_video)
        vid_row.addWidget(self._video_slot_label, 1)
        vid_row.addWidget(add_vid_btn)
        vid_row.addWidget(self._remove_vid_btn)

        # Subtitle slot
        sub_row = QHBoxLayout()
        self._sub_slot_label = QLabel("No subtitle")
        self._sub_slot_label.setStyleSheet("color:#666;font-size:11px;")
        self._sub_slot_label.setWordWrap(True)
        add_sub_btn = QPushButton("+ Subtitle")
        add_sub_btn.setFixedWidth(80)
        add_sub_btn.clicked.connect(self._browse_subtitle)
        self._remove_sub_btn = QPushButton("✕")
        self._remove_sub_btn.setFixedWidth(30)
        self._remove_sub_btn.setEnabled(False)
        self._remove_sub_btn.setToolTip("Remove subtitle")
        self._remove_sub_btn.setStyleSheet(
            "QPushButton{color:#ff5555;border-color:#5a2222;background:#2a1818;}"
            "QPushButton:hover{background:#3a2020;}"
            "QPushButton:disabled{color:#444;border-color:#252525;background:#1b1b22;}"
        )
        self._remove_sub_btn.clicked.connect(self._remove_subtitle)
        sub_row.addWidget(self._sub_slot_label, 1)
        sub_row.addWidget(add_sub_btn)
        sub_row.addWidget(self._remove_sub_btn)

        files_v.addLayout(vid_row)
        files_v.addLayout(sub_row)

        # Drag-drop area (still useful for dropping both files at once)
        self.queue_list = DragDropListWidget()
        self.queue_list.setMaximumHeight(60)
        self.queue_list.files_dropped.connect(self._on_files_dropped)
        self.queue_list.setToolTip("Drag & drop video and subtitle files here")
        drop_hint = QLabel("← drag & drop files here")
        drop_hint.setStyleSheet("color:#444;font-size:10px;")
        files_v.addWidget(drop_hint)
        files_v.addWidget(self.queue_list)

        # Subtitle cue list
        cue_grp = QGroupBox("Subtitle Cues")
        cue_v = QVBoxLayout(cue_grp)
        self.cue_list = QListWidget()
        self.cue_list.itemClicked.connect(self._jump_to_cue)
        cue_v.addWidget(self.cue_list)

        left_v.addWidget(files_grp)
        left_v.addWidget(cue_grp, 1)

        # ── CENTER PANEL ─────────────────────────────────────────────────
        center_w = QWidget()
        center_v = QVBoxLayout(center_w)
        center_v.setContentsMargins(0, 0, 0, 0)
        center_v.setSpacing(6)

        # Preview widget
        self.preview = PreviewWidget()

        # Safe-zone controls row
        sz_row = QHBoxLayout()
        self.safezone_chk = QCheckBox("Show safe zones")
        self.safezone_chk.setChecked(False)
        self.safezone_chk.toggled.connect(self._on_safezone_toggled)
        self.aspect_combo = QComboBox()
        self.aspect_combo.addItems(["16:9 Landscape", "9:16 Portrait"])
        self.aspect_combo.setFixedWidth(130)
        self.aspect_combo.currentIndexChanged.connect(self._on_aspect_changed)
        sz_lbl = QLabel("Aspect:")
        sz_lbl.setStyleSheet("color:#666;font-size:11px;")
        sz_row.addWidget(self.safezone_chk)
        sz_row.addSpacing(12)
        sz_row.addWidget(sz_lbl)
        sz_row.addWidget(self.aspect_combo)
        sz_row.addStretch()

        # Timeline
        self.timeline_slider = QSlider(Qt.Horizontal)
        self.timeline_slider.setMinimum(0)
        self.timeline_slider.setMaximum(1000)
        self.timeline_slider.valueChanged.connect(self._on_slider_moved)
        self.timeline_slider.setEnabled(False)

        time_row = QHBoxLayout()
        self.time_label = QLabel("00:00:00 / 00:00:00")
        self.time_label.setStyleSheet("color:#666;font-size:11px;")
        time_row.addStretch()
        time_row.addWidget(self.time_label)

        center_v.addWidget(self.preview, 1)
        center_v.addLayout(sz_row)
        center_v.addWidget(self.timeline_slider)
        center_v.addLayout(time_row)

        # ── RIGHT PANEL ──────────────────────────────────────────────────
        right_w = QWidget()
        right_v = QVBoxLayout(right_w)
        right_v.setContentsMargins(0, 0, 0, 0)
        right_v.setSpacing(8)

        # ─ Subtitle Style ─
        style_grp = QGroupBox("Subtitle Style")
        form = QFormLayout(style_grp)
        form.setLabelAlignment(Qt.AlignRight)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(7)

        self.font_combo = QComboBox()
        for fam in QFontDatabase().families():
            self.font_combo.addItem(fam)
        self.font_combo.setCurrentText("Arial")
        self.font_combo.currentTextChanged.connect(self._trigger_preview)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(10, 200)
        self.size_spin.setValue(48)
        self.size_spin.valueChanged.connect(self._trigger_preview)

        font_style_row = QHBoxLayout()
        self.bold_chk = QCheckBox("Bold")
        self.italic_chk = QCheckBox("Italic")
        self.bold_chk.toggled.connect(self._trigger_preview)
        self.italic_chk.toggled.connect(self._trigger_preview)
        font_style_row.addWidget(self.bold_chk)
        font_style_row.addWidget(self.italic_chk)
        font_style_row.addStretch()

        self.color_btn = self._swatch("#FFFFFF")
        self.color_btn.clicked.connect(self._pick_text_color)

        # Outline row: swatch + size spin
        outline_row = QHBoxLayout()
        outline_row.setSpacing(6)
        self.outline_btn = self._swatch("#000000")
        self.outline_btn.clicked.connect(self._pick_outline_color)
        self.outline_size_spin = QSpinBox()
        self.outline_size_spin.setRange(0, 10)
        self.outline_size_spin.setValue(0)          # no outline by default
        self.outline_size_spin.setToolTip("Stroke width (0 = no outline)")
        self.outline_size_spin.valueChanged.connect(self._trigger_preview)
        outline_row.addWidget(self.outline_btn)
        outline_row.addWidget(self.outline_size_spin)
        outline_row.addWidget(QLabel("px"))

        # Outline opacity
        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(6)
        self.outline_opacity_slider = QSlider(Qt.Horizontal)
        self.outline_opacity_slider.setRange(0, 100)
        self.outline_opacity_slider.setValue(100)   # 100% = fully opaque
        self.outline_opacity_slider.valueChanged.connect(self._trigger_preview)
        self._outline_opacity_lbl = QLabel("100%")
        self._outline_opacity_lbl.setFixedWidth(34)
        self.outline_opacity_slider.valueChanged.connect(
            lambda v: self._outline_opacity_lbl.setText(f"{v}%")
        )
        opacity_row.addWidget(self.outline_opacity_slider)
        opacity_row.addWidget(self._outline_opacity_lbl)

        self.shadow_spin = QSpinBox()
        self.shadow_spin.setRange(0, 20)
        self.shadow_spin.setValue(2)
        self.shadow_spin.valueChanged.connect(self._trigger_preview)

        pos_row = QHBoxLayout()
        pos_row.setSpacing(6)
        self.pos_slider = QSlider(Qt.Horizontal)
        self.pos_slider.setRange(0, 100)
        self.pos_slider.setValue(10)
        self.pos_slider.valueChanged.connect(self._trigger_preview)
        self._pos_lbl = QLabel("10")
        self._pos_lbl.setFixedWidth(24)
        self.pos_slider.valueChanged.connect(lambda v: self._pos_lbl.setText(str(v)))
        pos_row.addWidget(self.pos_slider)
        pos_row.addWidget(self._pos_lbl)

        form.addRow("Font:", self.font_combo)
        form.addRow("Size:", self.size_spin)
        form.addRow("Style:", font_style_row)
        form.addRow("Text color:", self.color_btn)
        form.addRow("Outline:", outline_row)
        form.addRow("Outline opacity:", opacity_row)
        form.addRow("Shadow:", self.shadow_spin)
        form.addRow("Y-Margin:", pos_row)

        # ─ Render Settings ─
        render_grp = QGroupBox("Render Settings")
        rform = QFormLayout(render_grp)
        rform.setLabelAlignment(Qt.AlignRight)
        rform.setHorizontalSpacing(10)
        rform.setVerticalSpacing(7)

        # Background
        bg_row = QHBoxLayout()
        bg_row.setSpacing(6)
        self.bg_combo = QComboBox()
        self.bg_combo.addItems(["Green (#00FF00)", "Blue (#0000FF)", "Custom…"])
        self.bg_combo.currentIndexChanged.connect(self._on_bg_changed)
        self._bg_swatch = self._swatch("#00FF00", clickable=False)
        self._bg_swatch.setFixedSize(28, 26)
        bg_row.addWidget(self.bg_combo)
        bg_row.addWidget(self._bg_swatch)

        self.codec_combo = QComboBox()
        self.codec_combo.addItems([
            "h264_videotoolbox", "hevc_videotoolbox", "libx264", "libx265",
        ])

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Low", "Medium", "Best"])
        self.quality_combo.setCurrentText("Medium")

        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP4 (.mp4)", "MOV (.mov)", "MKV (.mkv)"])

        rform.addRow("Background:", bg_row)
        rform.addRow("Encoder:", self.codec_combo)
        rform.addRow("Quality:", self.quality_combo)
        rform.addRow("Format:", self.format_combo)

        right_v.addWidget(style_grp)
        right_v.addWidget(render_grp)
        right_v.addStretch()

        # ── Assemble splitter ─────────────────────────────────────────
        splitter.addWidget(left_w)
        splitter.addWidget(center_w)
        splitter.addWidget(right_w)
        splitter.setSizes([240, 660, 300])
        rl.addWidget(splitter, 1)

        # ── Footer ───────────────────────────────────────────────────────
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        rl.addWidget(sep)

        footer = QHBoxLayout()
        footer.setSpacing(8)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color:#666;font-size:11px;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        self.cancel_btn = self._action_btn("Cancel", "#ffb300", "#3a2c00", "#6b5200")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_render)

        self.start_btn = QPushButton("▶  Start Rendering")
        self.start_btn.setEnabled(False)
        self.start_btn.setMinimumHeight(36)
        self.start_btn.setStyleSheet(
            "QPushButton{"
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7acc00,stop:1 #b3ff00);"
            "color:#000;font-weight:700;font-size:13px;border:none;border-radius:8px;}"
            "QPushButton:hover{background:#ccff33;}"
            "QPushButton:disabled{background:#23232d;color:#484858;border:1px solid #2b2b38;}"
        )
        self.start_btn.clicked.connect(self._start_render)

        footer.addWidget(self.status_label)
        footer.addWidget(self.progress_bar, 1)
        footer.addWidget(self.cancel_btn)
        footer.addWidget(self.start_btn)
        rl.addLayout(footer)

    # ═══════════════════════════════════════════════════════════════════
    # Widget factories
    # ═══════════════════════════════════════════════════════════════════

    def _swatch(self, color: str, clickable: bool = True) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(32, 26)
        self._apply_swatch_style(btn, color)
        if not clickable:
            btn.setEnabled(False)
        return btn

    def _apply_swatch_style(self, btn: QPushButton, color: str):
        btn.setStyleSheet(
            f"background:{color};border:1px solid #3a3a50;border-radius:5px;"
        )

    def _action_btn(self, text: str, fg: str, bg: str, border: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(
            f"QPushButton{{background:{bg};border:1px solid {border};color:{fg};"
            f"border-radius:7px;padding:6px 14px;}}"
            f"QPushButton:hover{{background:{border};}}"
            f"QPushButton:disabled{{background:#1b1b22;color:#484858;"
            f"border-color:#252530;}}"
        )
        return btn

    # ═══════════════════════════════════════════════════════════════════
    # File management
    # ═══════════════════════════════════════════════════════════════════

    def _browse_video(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "Open Video", "",
            "Video / Audio Files (*.mp4 *.mov *.mkv *.avi *.webm *.mp3 *.wav *.m4a *.aac)"
        )
        if p:
            self._set_video(p)

    def _browse_subtitle(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "Open Subtitle", "",
            "Subtitle Files (*.srt *.ass *.vtt)"
        )
        if p:
            self._set_subtitle(p)

    def _on_files_dropped(self, files: list):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in ('.mp4', '.mov', '.mkv', '.avi', '.webm', '.mp3', '.wav', '.m4a', '.aac'):
                self._set_video(f)
            elif ext in ('.srt', '.ass', '.vtt'):
                self._set_subtitle(f)

    def _set_video(self, path: str):
        self.video_path = path
        name = os.path.basename(path)
        self._video_slot_label.setText(name)
        self._video_slot_label.setStyleSheet("color:#b3ff00;font-size:11px;")
        self._remove_vid_btn.setEnabled(True)

        info = MediaEngine.get_media_info(path)
        self.duration = info.get('duration', 0.0)
        self.timeline_slider.setEnabled(True)
        self.start_btn.setEnabled(True)
        self._update_time_label(0)
        self._trigger_preview()

    def _set_subtitle(self, path: str):
        self.subtitle_path = path
        name = os.path.basename(path)
        self._sub_slot_label.setText(name)
        self._sub_slot_label.setStyleSheet("color:#b3ff00;font-size:11px;")
        self._remove_sub_btn.setEnabled(True)
        self._load_cue_list(path)
        self._trigger_preview()

    def _remove_video(self):
        self.video_path = None
        self.duration = 0.0
        self._video_slot_label.setText("No video")
        self._video_slot_label.setStyleSheet("color:#666;font-size:11px;")
        self._remove_vid_btn.setEnabled(False)
        self.timeline_slider.setValue(0)
        self.timeline_slider.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.time_label.setText("00:00:00 / 00:00:00")
        self.preview.clear()

    def _remove_subtitle(self):
        self.subtitle_path = None
        self._sub_slot_label.setText("No subtitle")
        self._sub_slot_label.setStyleSheet("color:#666;font-size:11px;")
        self._remove_sub_btn.setEnabled(False)
        self.cue_list.clear()
        self._trigger_preview()

    def _load_cue_list(self, path: str):
        from core.subtitle_manager import SubtitleManager
        cues = SubtitleManager().parse_srt_cues(path)
        self.cue_list.clear()
        for cue in cues:
            s = cue['start_ms'] / 1000
            tc = f"{int(s//3600):02d}:{int((s%3600)//60):02d}:{int(s%60):02d}"
            text = cue['text'].replace('\n', ' ')
            if len(text) > 58:
                text = text[:55] + '…'
            item = QListWidgetItem(f"[{tc}]  {text}")
            item.setData(Qt.UserRole, cue['start_ms'] / 1000.0)
            self.cue_list.addItem(item)

    def _jump_to_cue(self, item: QListWidgetItem):
        t = item.data(Qt.UserRole)
        if self.duration > 0:
            self.timeline_slider.setValue(int(t / self.duration * 1000))

    # ═══════════════════════════════════════════════════════════════════
    # Color pickers
    # ═══════════════════════════════════════════════════════════════════

    def _pick_text_color(self):
        c = QColorDialog.getColor(QColor(self.sub_color), self, "Text Color")
        if c.isValid():
            self.sub_color = c.name()
            self._apply_swatch_style(self.color_btn, self.sub_color)
            self._trigger_preview()

    def _pick_outline_color(self):
        c = QColorDialog.getColor(QColor(self.outline_color), self, "Outline Color")
        if c.isValid():
            self.outline_color = c.name()
            self._apply_swatch_style(self.outline_btn, self.outline_color)
            self._trigger_preview()

    def _on_bg_changed(self, _idx: int):
        presets = {"Green (#00FF00)": "00FF00", "Blue (#0000FF)": "0000FF"}
        text = self.bg_combo.currentText()
        if text in presets:
            self.bg_color_hex = presets[text]
        elif text == "Custom…":
            c = QColorDialog.getColor(QColor(f"#{self.bg_color_hex}"), self, "Background Color")
            if c.isValid():
                self.bg_color_hex = c.name().lstrip('#')
            else:
                self.bg_combo.blockSignals(True)
                self.bg_combo.setCurrentIndex(0)
                self.bg_combo.blockSignals(False)
                self.bg_color_hex = "00FF00"
        self._apply_swatch_style(self._bg_swatch, f"#{self.bg_color_hex}")
        self._trigger_preview()

    # ═══════════════════════════════════════════════════════════════════
    # Safe-zone / aspect ratio
    # ═══════════════════════════════════════════════════════════════════

    def _on_safezone_toggled(self, checked: bool):
        self.preview.set_safe_zone(checked)

    def _on_aspect_changed(self, _idx: int):
        ar = "9:16" if "9:16" in self.aspect_combo.currentText() else "16:9"
        self.preview.set_aspect_ratio(ar)
        self._trigger_preview()

    def _current_resolution(self) -> str:
        if "9:16" in self.aspect_combo.currentText():
            return "1080x1920"
        return "1920x1080"

    # ═══════════════════════════════════════════════════════════════════
    # Timeline
    # ═══════════════════════════════════════════════════════════════════

    def _on_slider_moved(self, value: int):
        self._update_time_label(value)
        self._preview_timer.start(220)

    def _update_time_label(self, v: int):
        cur = (v / 1000.0) * self.duration
        self.time_label.setText(
            f"{self._t(cur)} / {self._t(self.duration)}"
        )

    @staticmethod
    def _t(sec: float) -> str:
        sec = max(0.0, sec)
        return f"{int(sec//3600):02d}:{int((sec%3600)//60):02d}:{int(sec%60):02d}"

    def _trigger_preview(self):
        self._preview_timer.start(250)

    def _do_update_preview(self):
        if not self.video_path:
            return
        self.preview.set_loading(True)
        time_sec = (self.timeline_slider.value() / 1000.0) * self.duration
        tmp = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'preview.jpg'
        )
        styles   = self._build_style_string()
        res      = self._current_resolution()
        success  = MediaEngine.extract_preview_frame(
            self.video_path, self.subtitle_path,
            time_sec, tmp, styles, self.bg_color_hex, res,
        )
        if success and os.path.exists(tmp):
            pix = QPixmap(tmp)
            self.preview.set_pixmap(pix)
            try:
                os.remove(tmp)
            except Exception:
                pass
        else:
            self.preview.set_loading(False)

    # ═══════════════════════════════════════════════════════════════════
    # Style string
    # ═══════════════════════════════════════════════════════════════════

    def _build_style_string(self) -> str:
        # Opacity: slider 0–100 → ASS 0–255 (inverted: 100% opaque = 0)
        opacity_pct    = self.outline_opacity_slider.value()   # 100 = fully opaque
        outline_alpha  = int((100 - opacity_pct) / 100 * 255)  # 0 = opaque in ASS
        margin_v       = self.pos_slider.value()               # 0-100 (mapped ×2 in builder)
        return (
            f"FontName={self.font_combo.currentText()},"
            f"FontSize={self.size_spin.value()},"
            f"Bold={'-1' if self.bold_chk.isChecked() else '0'},"
            f"Italic={'-1' if self.italic_chk.isChecked() else '0'},"
            f"PrimaryColour={self.sub_color},"
            f"OutlineColour={self.outline_color},"
            f"OutlineAlpha={outline_alpha},"
            f"Outline={self.outline_size_spin.value()},"
            f"Shadow={self.shadow_spin.value()},"
            f"MarginV={margin_v}"
        )

    # ═══════════════════════════════════════════════════════════════════
    # Render
    # ═══════════════════════════════════════════════════════════════════

    def _on_progress(self, val: float, msg: str = ""):
        if val == -1:
            QMessageBox.critical(
                self, "Render Error",
                f"An error occurred during rendering.\n\n{msg}"
            )
            self.progress_bar.setValue(0)
            self.status_label.setText("Failed")
            self.start_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
        elif val >= 101:
            self.progress_bar.setValue(100)
            self.status_label.setText("✅  Completed!")
            QMessageBox.information(self, "Done", "Rendering completed successfully!")
            self.start_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
        else:
            self.progress_bar.setValue(int(val))
            self.status_label.setText(f"Rendering… {int(val)}%")

    def _start_render(self):
        if not self.video_path:
            return
        fmt_map = {"MP4 (.mp4)": ".mp4", "MOV (.mov)": ".mov", "MKV (.mkv)": ".mkv"}
        ext = fmt_map.get(self.format_combo.currentText(), ".mp4")
        out, _ = QFileDialog.getSaveFileName(
            self, "Save Output Video", "", f"Video Files (*{ext})"
        )
        if not out:
            return
        if not out.endswith(ext):
            out += ext

        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Queued…")

        MediaEngine.render_green_sub(
            video_path=self.video_path,
            subtitle_path=self.subtitle_path,
            output_path=out,
            bg_color=self.bg_color_hex,
            sub_styles=self._build_style_string(),
            progress_callback=self.render_progress_signal.emit,
            codec=self.codec_combo.currentText(),
            quality=self.quality_combo.currentText(),
            resolution=self._current_resolution(),
        )

    def _cancel_render(self):
        MediaEngine.get_queue().cancel_current_job()
        self.status_label.setText("Cancelling…")
        self.cancel_btn.setEnabled(False)
