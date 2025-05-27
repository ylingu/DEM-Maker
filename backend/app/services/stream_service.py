import asyncio

import cv2
from fastapi import WebSocket

from .drone_service import DroneService
from .record_service import RecordService


class StreamService:
    def __init__(self, drone_service: DroneService, record_service: RecordService):
        self.drone_service = drone_service
        self.record_service = record_service
        self.is_streaming = False
        self.websocket: WebSocket | None = None
        self.stream_task: asyncio.Task | None = None

    async def connect_client(self, websocket: WebSocket):
        if self.websocket is not None and self.websocket.client_state == 1:
            await self.websocket.close()
        await websocket.accept()
        self.websocket = websocket
        self.stream_task = asyncio.create_task(self.stream_frames())
        self.is_streaming = True

    async def stream_frames(self):
        frame_read = self.drone_service.drone.get_frame_read()
        while self.is_streaming and self.websocket is not None:
            frame = frame_read.frame
            if frame is not None:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if self.record_service.is_recording:
                    self.record_service.record_frame(frame)
                _, buffer = cv2.imencode(".jpg", frame)
                try:
                    await self.websocket.send_bytes(buffer.tobytes())
                except Exception:
                    self.is_streaming = False
                    break
                await asyncio.sleep(1 / 30)

    async def disconnect_client(self):
        if self.websocket is not None and self.websocket.client_state == 1:  # CONNECTED
            self.is_streaming = False
            await self.websocket.close()
            self.websocket = None
            if self.stream_task and not self.stream_task.done():
                try:
                    await asyncio.wait_for(self.stream_task, timeout=1)
                except (TimeoutError, asyncio.CancelledError):
                    if not self.stream_task.cancelled():
                        self.stream_task.cancel()
                    try:
                        await self.stream_task
                    except asyncio.CancelledError:
                        pass
                self.stream_task = None
