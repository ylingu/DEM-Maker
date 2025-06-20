from fastapi import APIRouter, HTTPException

from ..services.ply_service import PlyService

router = APIRouter(
    prefix="/ply",
    tags=["Point Cloud"],
)

@router.post("/generate")
async def generate_point_cloud():
    """
    生成点云的 API 接口
    """
    try:
        service = PlyService()
        result = service.main()  # 调用 PlyService 的主逻辑
        return {"message": "点云生成成功", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"点云生成失败: {str(e)}")