from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from ..dependencies import get_stream_service
from ..services.stream_service import StreamService

router = APIRouter(prefix="/ws", tags=["websockets"])


@router.websocket("/video")
async def video_stream(
    websocket: WebSocket, stream_service: StreamService = Depends(get_stream_service)
):
    try:
        await stream_service.connect_client(websocket)
        if stream_service.stream_task:
            await stream_service.stream_task
    except WebSocketDisconnect:
        pass
    except Exception as e:
        raise Exception(f"WebSocket error: {str(e)}")
    finally:
        await stream_service.disconnect_client()
