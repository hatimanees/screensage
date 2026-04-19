import tempfile
from pathlib import Path
import mss
import mss.tools


def capture_screen(output_path: str | None = None) -> str:
    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        output_path = tmp.name
        tmp.close()

    with mss.mss() as sct:
        monitor = sct.monitors[0]  # full virtual screen (all monitors)
        shot = sct.grab(monitor)
        mss.tools.to_png(shot.rgb, shot.size, output=output_path)

    return output_path
