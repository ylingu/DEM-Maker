import asyncio
from typing import Literal

from djitellopy import Tello
from pydantic import BaseModel

from .record_service import RecordService


class DroneCommand(BaseModel):
    action: Literal["takeoff", "land", "press", "release"]
    key: Literal["w", "s", "a", "d", "q", "e", " ", "control"] | None = None


class DroneService:
    SPEED = 60

    def __init__(self, record_service: RecordService):
        self.drone = Tello()
        self.record_service = record_service
        self.for_back_velocity = 0
        self.left_right_velocity = 0
        self.up_down_velocity = 0
        self.yaw_velocity = 0
        self.speed = 10
        self.send_rc_control = False

    async def connect(self):
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, self.drone.connect)
            await loop.run_in_executor(None, self.drone.set_speed, self.speed)
            await loop.run_in_executor(None, self.drone.streamon)
            self.record_service.start_recording()
        except Exception as e:
            raise Exception(f"Failed to connect to drone: {str(e)}")

    async def disconnect(self):
        await asyncio.get_event_loop().run_in_executor(None, self.drone.land)
        self.record_service.stop_recording()

    def _update(self):
        if self.send_rc_control:
            self.drone.send_rc_control(
                self.left_right_velocity,
                self.for_back_velocity,
                self.up_down_velocity,
                self.yaw_velocity,
            )

    def _handle_press(self, key: str):
        match key:
            case "w":
                self.for_back_velocity = self.SPEED
            case "s":
                self.for_back_velocity = -self.SPEED
            case "a":
                self.left_right_velocity = -self.SPEED
            case "d":
                self.left_right_velocity = self.SPEED
            case "q":
                self.yaw_velocity = -self.SPEED
            case "e":
                self.yaw_velocity = self.SPEED
            case " ":
                self.up_down_velocity = self.SPEED
            case "control":
                self.up_down_velocity = -self.SPEED

    def _handle_release(self, key: str):
        match key:
            case "w" | "s":
                self.for_back_velocity = 0
            case "a" | "d":
                self.left_right_velocity = 0
            case "q" | "e":
                self.yaw_velocity = 0
            case " " | "control":
                self.up_down_velocity = 0

    async def execute_command(self, command: DroneCommand):
        loop = asyncio.get_event_loop()
        try:
            if command.action == "takeoff":
                await loop.run_in_executor(None, self.drone.takeoff)
                self.send_rc_control = True
            elif command.action == "land":
                await loop.run_in_executor(None, self.drone.land)
                self.send_rc_control = False
            elif command.action == "press":
                self._handle_press(command.key)  # type: ignore
                loop.run_in_executor(None, self._update)
            elif command.action == "release":
                self._handle_release(command.key)  # type: ignore
                loop.run_in_executor(None, self._update)
        except Exception as e:
            raise Exception(f"Failed to execute command: {str(e)}")
