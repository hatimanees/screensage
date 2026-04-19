from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

_FONT = "'Segoe UI Variable', 'Segoe UI', 'Inter', Arial, sans-serif"

_STYLES = f"""
    QLabel {{
        font-family: {_FONT};
        background: transparent;
        border: none;
    }}
    QLabel#title {{
        color: #818cf8;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1.4px;
    }}
    QLabel#query_label {{
        color: #475569;
        font-size: 11px;
        font-style: italic;
    }}
    QLabel#content {{
        color: #cbd5e1;
        font-size: 13px;
        line-height: 1.7;
        padding: 0px;
    }}
    QFrame#divider {{
        background: rgba(255,255,255,10);
        border: none;
        max-height: 1px;
        min-height: 1px;
    }}
    QPushButton {{
        font-family: {_FONT};
        border: none;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton#close_x {{
        background: transparent;
        color: #334155;
        border-radius: 8px;
        font-size: 15px;
        padding: 1px 6px;
    }}
    QPushButton#close_x:hover {{ color: #94a3b8; background: rgba(255,255,255,12); }}

    QPushButton#ask_again_btn {{
        background: #4f46e5; color: #fff;
        border-radius: 14px; padding: 5px 20px;
    }}
    QPushButton#ask_again_btn:hover   {{ background: #4338ca; }}
    QPushButton#ask_again_btn:pressed {{ background: #3730a3; }}

    QPushButton#done_btn {{
        background: rgba(255,255,255,14); color: #64748b;
        border-radius: 14px; padding: 5px 20px;
    }}
    QPushButton#done_btn:hover {{ background: rgba(255,255,255,22); color: #94a3b8; }}

    QPushButton#copy_btn {{
        background: rgba(255,255,255,10); color: #64748b;
        border-radius: 14px; padding: 5px 16px;
    }}
    QPushButton#copy_btn:hover   {{ background: rgba(255,255,255,20); color: #94a3b8; }}
    QPushButton#copy_btn:pressed {{ background: rgba(255,255,255,28); }}

    QScrollArea {{ background: transparent; border: none; }}
    QScrollBar:vertical {{
        background: transparent; width: 4px; margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(255,255,255,28); border-radius: 2px; min-height: 20px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""

_E = 6    # edge handle thickness
_C = 14   # corner handle size


class _ResizeHandle(QWidget):
    """Transparent drag zone for one edge or corner of a frameless window.

    w_factor / h_factor: +1 = grows that dimension when dragging outward,
                         -1 = grows when dragging inward (left / top handles),
                          0 = dimension unchanged.
    move_x / move_y: True for left / top handles — window position must shift
                     so the opposite edge stays anchored.
    scroll_area: forwarded target for wheel events.
    """

    def __init__(self, parent, w_factor, h_factor, move_x, move_y, cursor,
                 scroll_area=None):
        super().__init__(parent)
        self._wf   = w_factor
        self._hf   = h_factor
        self._mx   = move_x
        self._my   = move_y
        self._sa   = scroll_area
        self._origin     = None
        self._start_geom = None
        self.setCursor(cursor)
        self.setStyleSheet("background: transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin     = event.globalPosition().toPoint()
            self._start_geom = self.parent().geometry()
        event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._origin:
            d  = event.globalPosition().toPoint() - self._origin
            g  = self._start_geom
            p  = self.parent()
            mw = p.minimumWidth()
            mh = p.minimumHeight()

            new_w = max(g.width()  + d.x() * self._wf, mw) if self._wf else g.width()
            new_h = max(g.height() + d.y() * self._hf, mh) if self._hf else g.height()

            # For left / top handles the opposite edge must stay anchored
            new_x = g.x() + g.width()  - new_w if self._mx else g.x()
            new_y = g.y() + g.height() - new_h if self._my else g.y()

            p.setGeometry(new_x, new_y, new_w, new_h)
        event.accept()

    def mouseReleaseEvent(self, event):
        self._origin     = None
        self._start_geom = None
        event.accept()

    def wheelEvent(self, event):
        # Forward scroll wheel to the scroll area so scrolling still works
        # even when the mouse is over a resize handle near the edge.
        if self._sa:
            sb = self._sa.verticalScrollBar()
            sb.setValue(sb.value() - event.angleDelta().y() // 3)
            event.accept()
        else:
            event.ignore()


class ResultOverlay(QWidget):
    ask_again = pyqtSignal()

    def __init__(self, text: str, query: str, bar: QWidget):
        super().__init__()
        self._bar      = bar
        self._text     = text
        self._drag_pos = None
        self._build(text, query)

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build(self, text: str, query: str):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
            # No WindowDoesNotAcceptFocus — allows click-to-focus for text selection
        )
        # Show without stealing focus; user can still click in to select text
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(_STYLES)

        self.setMinimumWidth(300)
        self.setMinimumHeight(180)
        self.resize(460, 340)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 14, 20, 10)
        outer.setSpacing(8)

        # ── Header ────────────────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(0)

        title = QLabel("SCREENSAGE")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()

        drag_hint = QLabel("⠿")
        drag_hint.setToolTip("Drag to move")
        drag_hint.setStyleSheet("color: #1e293b; font-size: 14px; background: transparent;")
        header.addWidget(drag_hint)

        close_x = QPushButton("✕")
        close_x.setObjectName("close_x")
        close_x.setFixedSize(26, 26)
        close_x.setCursor(Qt.CursorShape.PointingHandCursor)
        close_x.clicked.connect(self._on_done)
        header.addWidget(close_x)
        outer.addLayout(header)

        # ── Query echo (selectable) ───────────────────────────────────────────
        if query:
            q_label = QLabel(f'"{query}"')
            q_label.setObjectName("query_label")
            q_label.setWordWrap(True)
            q_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse |
                Qt.TextInteractionFlag.TextSelectableByKeyboard
            )
            q_label.setCursor(Qt.CursorShape.IBeamCursor)
            outer.addWidget(q_label)

        # ── Divider ───────────────────────────────────────────────────────────
        div = QFrame()
        div.setObjectName("divider")
        div.setFrameShape(QFrame.Shape.HLine)
        outer.addWidget(div)

        # ── Scrollable content ────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 4, 6, 4)

        content_label = QLabel(text)
        content_label.setObjectName("content")
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        content_label.setCursor(Qt.CursorShape.IBeamCursor)
        content_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        content_layout.addWidget(content_label)
        content_layout.addStretch()

        scroll.setWidget(content_widget)
        scroll.viewport().setStyleSheet("background: transparent;")
        outer.addWidget(scroll)

        # ── Divider ───────────────────────────────────────────────────────────
        div2 = QFrame()
        div2.setObjectName("divider")
        div2.setFrameShape(QFrame.Shape.HLine)
        outer.addWidget(div2)

        # ── Footer: buttons ───────────────────────────────────────────────────
        footer = QHBoxLayout()
        footer.setSpacing(8)

        ask_again_btn = QPushButton("▶  Ask Again")
        ask_again_btn.setObjectName("ask_again_btn")
        ask_again_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ask_again_btn.clicked.connect(self._on_ask_again)
        footer.addWidget(ask_again_btn)

        done = QPushButton("Done")
        done.setObjectName("done_btn")
        done.setCursor(Qt.CursorShape.PointingHandCursor)
        done.clicked.connect(self._on_done)
        footer.addWidget(done)

        self._copy_btn = QPushButton("Copy")
        self._copy_btn.setObjectName("copy_btn")
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.clicked.connect(self._on_copy)
        footer.addWidget(self._copy_btn)

        footer.addStretch()
        outer.addLayout(footer)

        # ── All 8 resize handles (raised above content) ───────────────────────
        C = Qt.CursorShape
        self._handles = [
            # corners
            _ResizeHandle(self, -1, -1, True,  True,  C.SizeFDiagCursor, scroll),
            _ResizeHandle(self, +1, -1, False, True,  C.SizeBDiagCursor, scroll),
            _ResizeHandle(self, +1, +1, False, False, C.SizeFDiagCursor, scroll),
            _ResizeHandle(self, -1, +1, True,  False, C.SizeBDiagCursor, scroll),
            # edges
            _ResizeHandle(self,  0, -1, False, True,  C.SizeVerCursor,   scroll),
            _ResizeHandle(self, +1,  0, False, False, C.SizeHorCursor,   scroll),
            _ResizeHandle(self,  0, +1, False, False, C.SizeVerCursor,   scroll),
            _ResizeHandle(self, -1,  0, True,  False, C.SizeHorCursor,   scroll),
        ]
        self._place_handles()

        QTimer.singleShot(0, self._position_and_show)

    # ── Resize handle placement ───────────────────────────────────────────────

    def _place_handles(self):
        w, h = self.width(), self.height()
        tl, tr, br, bl, top, right, bottom, left = self._handles
        # corners
        tl    .setGeometry(0,        0,        _C, _C)
        tr    .setGeometry(w - _C,   0,        _C, _C)
        br    .setGeometry(w - _C,   h - _C,   _C, _C)
        bl    .setGeometry(0,        h - _C,   _C, _C)
        # edges (between corners)
        top   .setGeometry(_C,       0,        w - 2*_C, _E)
        right .setGeometry(w - _E,   _C,       _E,       h - 2*_C)
        bottom.setGeometry(_C,       h - _E,   w - 2*_C, _E)
        left  .setGeometry(0,        _C,       _E,       h - 2*_C)
        for h_ in self._handles:
            h_.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place_handles()

    # ── Positioning ───────────────────────────────────────────────────────────

    def _position_and_show(self):
        from ui.recording_bar import RecordingBar
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        bar_top = screen.height() - RecordingBar.BAR_H - 52
        y = max(bar_top - self.height() - 10, 10)
        self.move(x, y)
        self.show()

    # ── Drag to move (clicking on overlay bg / header area) ───────────────────

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

    # ── Custom background ─────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 16, 16)

        painter.setBrush(QColor(10, 10, 20, 240))
        painter.setPen(QColor(255, 255, 255, 18))
        painter.drawPath(path)

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _on_copy(self):
        QApplication.clipboard().setText(self._text)
        self._copy_btn.setText("Copied!")
        QTimer.singleShot(1500, lambda: self._copy_btn.setText("Copy"))

    def _on_done(self):
        self._bar.set_idle()
        self.close()

    def _on_ask_again(self):
        self.ask_again.emit()
        self._bar.set_idle()
        self.close()
