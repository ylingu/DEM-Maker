import tempfile
from pathlib import Path

import cv2


class RecordService:
    def __init__(self):
        self.is_recording = False
        self.writer: cv2.VideoWriter | None = None
        self.temp_dir = Path(tempfile.gettempdir()) / "dem"
        self.temp_dir.mkdir(exist_ok=True)

    def start_recording(self):
        if not self.is_recording:
            self.writer = cv2.VideoWriter(
                str(self.temp_dir / "record.avi"),
                cv2.VideoWriter_fourcc(*"XVID"), # type: ignore
                30.0,
                (960, 720),
            )
            self.is_recording = True
        else:
            raise Exception("Recording is already in progress.")
        
    def stop_recording(self):
        if self.is_recording:
            if self.writer:
                self.writer.release()
                self.writer = None
            self.is_recording = False

    def record_frame(self, frame: cv2.Mat):
        if self.is_recording and self.writer:
            self.writer.write(frame)
        else:
            raise Exception("Recording is not in progress.")
        