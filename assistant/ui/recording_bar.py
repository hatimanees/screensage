from enum import Enum, auto

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QWidget


class BarState(Enum):
    IDLE       = auto()
    RECORDING  = auto()
    PROCESSING = auto()


# ── Stylesheets ──────────────────────────────────────────────────────────────

_FONT = "'Segoe UI Variable', 'Segoe UI', 'Inter', Arial, sans-serif"

_STYLES = f"""
    QLabel {{
        font-family: {_FONT};
        background: transparent;
        border: none;
    }}
    QLabel#status      {{ color: #64748b; font-size: 13px; }}
    QLabel#status_rec  {{ color: #fca5a5; font-size: 13px; }}
    QLabel#status_proc {{ color: #818cf8; font-size: 13px; }}
    QLabel#spinner     {{ color: #818cf8; font-size: 13px; }}
    QLabel#collapsed   {{ color: #4b5563; font-size: 12px; font-weight: 600; letter-spacing: 0.5px; }}

    QPushButton {{
        font-family: {_FONT};
        border: none;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton#start_btn {{
        background: #4f46e5; color: #fff;
        border-radius: 14px; padding: 5px 18px;
    }}
    QPushButton#start_btn:hover   {{ background: #4338ca; }}
    QPushButton#start_btn:pressed {{ background: #3730a3; }}

    QPushButton#stop_btn {{
        background: #dc2626; color: #fff;
        border-radius: 14px; padding: 5px 18px;
    }}
    QPushButton#stop_btn:hover   {{ background: #b91c1c; }}
    QPushButton#stop_btn:pressed {{ background: #991b1b; }}

    QPushButton#delete_btn {{
        background: rgba(255,255,255,18); color: #64748b;
        border-radius: 14px; padding: 5px 14px;
    }}
    QPushButton#delete_btn:hover {{ background: rgba(255,255,255,28); color: #94a3b8; }}

    QPushButton#icon_btn {{
        background: transparent; color: #374151;
        border-radius: 10px; padding: 2px 8px; font-size: 13px;
    }}
    QPushButton#icon_btn:hover {{ color: #6b7280; background: rgba(255,255,255,10); }}
"""


# ── Bar widget ───────────────────────────────────────────────────────────────

class RecordingBar(QWidget):
    start_clicked  = pyqtSignal()
    stop_clicked   = pyqtSignal()
    delete_clicked = pyqtSignal()

    # Expanded geometry
    BAR_W = 440
    BAR_H = 52
    # Collapsed geometry
    COLL_W = 158
    COLL_H = 40

    def __init__(self):
        super().__init__()
        self._state     = BarState.IDLE
        self._collapsed = False
        self._spin_frame = 0
        self._spin_timer = QTimer(self)
        self._spin_timer.timeout.connect(self._advance_spinner)
        self._drag_pos  = None
        self._build()
        self._position_center()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(_STYLES)

        # ── Collapsed layer ──────────────────────────────────────────────────
        self._coll_widget = QWidget(self)
        coll_layout = QHBoxLayout(self._coll_widget)
        coll_layout.setContentsMargins(14, 0, 10, 0)
        coll_layout.setSpacing(8)

        coll_label = QLabel("ScreenSage")
        coll_label.setObjectName("collapsed")
        coll_layout.addWidget(coll_label, 1)

        expand_btn = QPushButton("▸")
        expand_btn.setObjectName("icon_btn")
        expand_btn.setFixedWidth(26)
        expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        expand_btn.setToolTip("Expand")
        expand_btn.clicked.connect(self.toggle_collapse)
        coll_layout.addWidget(expand_btn)

        self._coll_widget.setVisible(False)

        # ── Expanded layer ───────────────────────────────────────────────────
        self._exp_widget = QWidget(self)
        exp_layout = QHBoxLayout(self._exp_widget)
        exp_layout.setContentsMargins(18, 0, 12, 0)
        exp_layout.setSpacing(10)

        # Collapse toggle
        collapse_btn = QPushButton("◂")
        collapse_btn.setObjectName("icon_btn")
        collapse_btn.setFixedWidth(22)
        collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        collapse_btn.setToolTip("Collapse")
        collapse_btn.clicked.connect(self.toggle_collapse)
        exp_layout.addWidget(collapse_btn)

        # Spinner (processing)
        self._spinner = QLabel("◐")
        self._spinner.setObjectName("spinner")
        self._spinner.setFixedWidth(16)
        self._spinner.setVisible(False)
        exp_layout.addWidget(self._spinner)

        # Status label
        self._label = QLabel("Ready")
        self._label.setObjectName("status")
        exp_layout.addWidget(self._label, 1)

        # Start
        self._start_btn = QPushButton("▶  Start")
        self._start_btn.setObjectName("start_btn")
        self._start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_btn.clicked.connect(self._on_start)
        exp_layout.addWidget(self._start_btn)

        # Stop (hidden initially)
        self._stop_btn = QPushButton("■  Stop")
        self._stop_btn.setObjectName("stop_btn")
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.clicked.connect(self._on_stop)
        self._stop_btn.setVisible(False)
        exp_layout.addWidget(self._stop_btn)

        # Delete / quit
        self._action_btn = QPushButton("Quit")
        self._action_btn.setObjectName("delete_btn")
        self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action_btn.clicked.connect(self._on_action)
        exp_layout.addWidget(self._action_btn)

        self._apply_expanded_size()

    # ── Sizing helpers ────────────────────────────────────────────────────────

    def _apply_expanded_size(self):
        self.setFixedSize(self.BAR_W, self.BAR_H)
        self._exp_widget.setGeometry(0, 0, self.BAR_W, self.BAR_H)
        self._exp_widget.setVisible(True)
        self._coll_widget.setVisible(False)

    def _apply_collapsed_size(self):
        self.setFixedSize(self.COLL_W, self.COLL_H)
        self._coll_widget.setGeometry(0, 0, self.COLL_W, self.COLL_H)
        self._coll_widget.setVisible(True)
        self._exp_widget.setVisible(False)

    def toggle_collapse(self):
        self._collapsed = not self._collapsed
        if self._collapsed:
            self._apply_collapsed_size()
        else:
            self._apply_expanded_size()
            self.set_state(self._state)   # re-apply current state visuals
        self.update()

    # ── Position ──────────────────────────────────────────────────────────────

    def _position_center(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = screen.height() - self.height() - 52
        self.move(x, y)

    # ── Drag support ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
        event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    # ── State machine ─────────────────────────────────────────────────────────

    def set_state(self, state: BarState):
        self._state = state
        self._spin_timer.stop()
        self._spinner.setVisible(False)

        if state == BarState.IDLE:
            self._label.setText("Ready")
            self._label.setObjectName("status")
            self._label.setStyleSheet("color: #64748b;")
            self._start_btn.setVisible(True)
            self._start_btn.setEnabled(True)
            self._stop_btn.setVisible(False)
            self._action_btn.setText("Quit")
            self._action_btn.setEnabled(True)

        elif state == BarState.RECORDING:
            self._label.setText("Listening…")
            self._label.setStyleSheet("color: #fca5a5;")
            self._start_btn.setVisible(False)
            self._stop_btn.setVisible(True)
            self._action_btn.setText("Delete")
            self._action_btn.setEnabled(True)

        elif state == BarState.PROCESSING:
            self._label.setText("Analyzing…")
            self._label.setStyleSheet("color: #818cf8;")
            self._start_btn.setVisible(False)
            self._stop_btn.setVisible(False)
            self._action_btn.setEnabled(False)
            self._spinner.setVisible(True)
            self._spin_timer.start(120)

        self.update()

    def set_idle(self):
        self.set_state(BarState.IDLE)

    def set_processing(self):
        self.set_state(BarState.PROCESSING)

    # ── Button handlers ───────────────────────────────────────────────────────

    def _on_start(self):
        self.set_state(BarState.RECORDING)
        self.start_clicked.emit()

    def _on_stop(self):
        self.set_state(BarState.PROCESSING)
        self.stop_clicked.emit()

    def _on_action(self):
        if self._state == BarState.RECORDING:
            self.set_state(BarState.IDLE)
            self.delete_clicked.emit()
        else:  # IDLE — Quit
            QApplication.quit()

    # ── Spinner animation ─────────────────────────────────────────────────────

    _FRAMES = ("◐", "◓", "◑", "◒")

    def _advance_spinner(self):
        self._spin_frame = (self._spin_frame + 1) % len(self._FRAMES)
        self._spinner.setText(self._FRAMES[self._spin_frame])

    # ── Custom background ─────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = self.height() // 2
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), r, r)

        if self._state == BarState.RECORDING:
            bg = QColor(28, 8, 8, 232)
        elif self._state == BarState.PROCESSING:
            bg = QColor(8, 8, 28, 232)
        else:
            bg = QColor(10, 10, 18, 228)

        painter.setBrush(bg)
        painter.setPen(QColor(255, 255, 255, 14))
        painter.drawPath(path)
