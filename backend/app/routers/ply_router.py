from fastapi import APIRouter, HTTPException, Query

from ..services.ply_service import PlyService

router = APIRouter(
    prefix="/ply",
    tags=["Point Cloud"],
)

@router.post("/generate")
async def generate_point_cloud(dataset_dir: str = Query(..., description="数据集文件夹路径")):
    """
    生成点云的 API 接口
    :param dataset_dir: 数据集文件夹路径
    """
    try:
        service = PlyService(working_dir=dataset_dir)  # 传入数据集文件夹路径
        result = service.main()  # 调用 PlyService 的主逻辑
        return {"message": "点云生成成功", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"点云生成失败: {str(e)}")