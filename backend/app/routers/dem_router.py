from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from app.services.dem_service import DemService
import tempfile
import shutil
import os

router = APIRouter()

def remove_file(path: str):
    os.remove(path)

@router.post("/dem/generate")
async def generate_dem(
    file: UploadFile = File(...),
    colors_data: bool = Form(True),
    method: str = Form("idw"),
    grid_size: int = Form(500),
    background_tasks: BackgroundTasks = None
):
    # 保存上传的点云文件到临时目录
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    # 实例化服务
    dem_service = DemService()
    # 生成DEM
    dem, color_grid, grid_x, grid_y = dem_service.generate_dem(
        pcd_path=tmp_path,
        colors_data=colors_data,
        method=method,
        grid_size=grid_size
    )

    # 生成输出文件路径
    out_path = tmp_path + "_dem.tif"
    # 保存DEM为GeoTIFF
    dem_service.save_dem(dem, grid_x, grid_y, out_path, color_grid)

    # 删除上传的临时点云文件
    os.remove(tmp_path)

    background_tasks.add_task(remove_file, out_path)
    return FileResponse(
        out_path,
        filename="dem.tif",
        media_type="image/tiff",
        background=background_tasks
    )