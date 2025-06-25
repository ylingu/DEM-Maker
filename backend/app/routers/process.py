import os
import shutil
from pathlib import Path

import cv2
import numpy as np
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..dependencies import get_dem_service, gettempdir
from ..services import DemConfig, DemService, PlyService

router = APIRouter(prefix="/api", tags=["process"])


class ProcessRequest(BaseModel):
    path: str
    config: DemConfig


def process_pipeline(config: DemConfig, dem_service: DemService, temp_dir: Path):
    """处理DEM的管道函数"""
    ply_service = PlyService(temp_dir)
    ply_service()
    dem_service.generate_dem(str(temp_dir / "fused.ply"), config)


def handle_images(path: str, temp_dir: Path):
    """保存上传的图片到临时文件夹"""
    image_dir = temp_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    # 清除之前的图片
    for existing_file in image_dir.glob("*"):
        if existing_file.is_file():
            existing_file.unlink()

    if path == "Default":
        path = str(temp_dir / "record.avi")

    # 检测path为文件夹还是文件
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"Path {path} does not exist")
    if os.path.isdir(path):
        # 将图片文件移动到image_dir
        for image_file in os.listdir(path):
            image = Path(path) / image_file
            if image.is_file() and image.suffix.lower() in {
                ".jpg",
                ".jpeg",
                ".png",
            }:
                # 生成新的文件名（保持原扩展名）
                file_extension = image.suffix
                filename = f"{image.stem}_{image.stat().st_mtime_ns}{file_extension}"
                new_file_path = image_dir / filename
                shutil.copy(image, new_file_path)
    # 如果是视频文件，每秒截取一帧保存到 image_dir
    elif os.path.isfile(path) and path.lower().endswith((".mp4", ".avi", ".mov")):
        cap = cv2.VideoCapture(path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps)
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_count % frame_interval == 0:
                # 生成新的文件名（保持原扩展名）
                filename = f"frame_{frame_count:08d}.jpg"
                file_path = image_dir / filename
                cv2.imwrite(str(file_path), frame)
            frame_count += 1

        cap.release()
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported path type: {path}")


@router.post("/process")
async def process_dem(
    request_data: ProcessRequest,
    background_tasks: BackgroundTasks,
    dem_service: DemService = Depends(get_dem_service),
    temp_dir: Path = Depends(gettempdir),
):
    try:
        handle_images(request_data.path, temp_dir)
        background_tasks.add_task(
            process_pipeline, request_data.config, dem_service, temp_dir
        )
        return {"message": "DEM processing started in the background."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing images: {str(e)}"
        )


# 点云数据路由
@router.get("/pointcloud")
async def get_pointcloud(temp_dir: Path = Depends(gettempdir)):
    """
    返回PLY点云文件
    """
    # 获取PLY文件路径
    ply_file_path = temp_dir / "fused.ply"

    # 检查文件是否存在
    if not os.path.exists(ply_file_path):
        raise HTTPException(status_code=404, detail="PLY文件未找到")

    # 返回文件响应，设置正确的MIME类型
    return FileResponse(
        path=ply_file_path,
        media_type="application/octet-stream",
        filename="fused.ply",
        headers={
            "Content-Disposition": "attachment; filename=fused.ply",
            "Cache-Control": "no-cache",  # 防止缓存问题
        },
    )


@router.get("/dem")
async def get_dem(dem_service: DemService = Depends(get_dem_service)):
    """
    返回DEM数据，包括高程信息和RGB纹理
    4波段：第1波段为高程，第2-4波段为RGB
    """
    try:
        profile, elevation, rgb = dem_service.export_dem()
        # 准备返回的数据
        response_data = {
            # === 核心数据 ===
            "width": profile["width"],
            "height": profile["height"],
            "elevation": elevation.tolist(),
            "texture": None,
            # === 地理空间信息（重要） ===
            "crs": profile["crs"],  # 坐标参考系统
            "resolution": {
                "x": abs(profile["transform"][0]),  # X方向分辨率（米/像素）
                "y": abs(profile["transform"][4]),  # Y方向分辨率（米/像素）
            },
        }

        # 处理4波段格式：第1波段为高程，第2-4波段为RGB
        # 高程数据 (第1波段，索引0)
        elevation_data = elevation.astype(np.float32)
        elevation_data = np.nan_to_num(elevation_data, nan=0.0)

        response_data["elevation"] = elevation_data.tolist()
        # RGB纹理数据 (第2-4波段，索引1-3)
        rgb_data = rgb.astype(np.uint8)  # Shape: (3, height, width)

        # 转换为 (height, width, 3) 格式
        rgb_normalized = np.transpose(rgb_data, (1, 2, 0))
        response_data["texture"] = rgb_normalized.tolist()

        return response_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理DEM文件时出错: {str(e)}")


class DemSaveRequest(BaseModel):
    format: str
    height_scale: float
    file_path: str


@router.get("/dem/save")
async def save_dem(
    request_data: DemSaveRequest,
    dem_service: DemService = Depends(get_dem_service),
):
    """
    保存生成的DEM数据为GeoTIFF格式
    """
    try:
        # 保存DEM文件到临时目录
        dem_service.save_dem(request_data.file_path)

        return {"message": "DEM saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving DEM: {str(e)}")
