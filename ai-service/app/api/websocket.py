from fastapi import APIRouter, WebSocket

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json({"type": "CONNECTED"})
    await websocket.close()