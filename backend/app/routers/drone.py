from fastapi import APIRouter, Depends

from ..dependencies import get_drone_service
from ..services.drone_service import DroneCommand, DroneService

router = APIRouter(
    prefix="/api/drone",
    tags=["drone"],
)


@router.post("/connect")
async def connect_drone(drone_service: DroneService = Depends(get_drone_service)):
    """连接无人机"""
    try:
        await drone_service.connect()
    except Exception as e:
        return {"message": f"Failed to connect drone: {str(e)}"}


@router.post("/disconnect")
async def disconnect_drone(drone_service: DroneService = Depends(get_drone_service)):
    """断开无人机连接"""
    try:
        await drone_service.disconnect()
    except Exception as e:
        return {"message": f"Failed to disconnect drone: {str(e)}"}


@router.post("/command")
async def send_drone_command(
    command: DroneCommand, drone_service: DroneService = Depends(get_drone_service)
):
    """发送无人机指令"""
    try:
        await drone_service.execute_command(command)
    except Exception as e:
        return {"message": f"Failed to send command to drone: {str(e)}"}
