"""SVG utility functions"""

from PySide6.QtCore import QByteArray, Qt, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


def svg_icon_with_palette_color(svg_path: str, color: QColor) -> QIcon:
    """Change SVG currentColor to match the given color

    Args:
        svg_path (str): The file path to the SVG file.
        color (QColor): The color to replace currentColor in the SVG.

    Returns:
        QIcon: The generated icon from the SVG.
    """
    with open(file=svg_path, mode="r", encoding="utf-8") as f:
        svg_data: str = f.read()
    svg_data: str = svg_data.replace("currentColor", color.name())

    # Render SVG to pixmap
    renderer = QSvgRenderer(QByteArray(svg_data.encode(encoding="utf-8")))
    size: QSize = renderer.defaultSize()
    pixmap = QPixmap(size)
    pixmap.fill(fillColor=Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    return QIcon(pixmap)
