import os
from typing import Literal, TypedDict

import numpy as np
import open3d as o3d
import rasterio
from affine import Affine
from pydantic import BaseModel
from rasterio.transform import from_origin

from .interpolator import (
    idw_interpolation,
    kriging_interpolation,
    nearest_color_interpolation,
)


class DemConfig(BaseModel):
    colors_data: bool = True
    method: Literal["idw", "kriging"] = "idw"
    grid_size: int = 500


class Profile(TypedDict):
    driver: str
    dtype: str
    count: int
    height: int
    width: int
    crs: str
    transform: Affine
    compress: str
    tiled: bool
    blockxsize: int
    blockysize: int


class DemService:
    def __init__(self):
        self.dem: np.ndarray | None = None
        self.grid_x: np.ndarray
        self.grid_y: np.ndarray
        self.color_grid: np.ndarray
        self.profile: Profile | None = None

    @staticmethod
    def read_pointcloud(pcd_path: str):
        ext = os.path.splitext(pcd_path)[1].lower()
        if ext in [".ply", ".pcd"]:
            pcd = o3d.io.read_point_cloud(pcd_path)
            xyz = np.asarray(pcd.points)
            rgb = np.asarray(pcd.colors) if len(pcd.colors) > 0 else None
        else:
            raise ValueError(f"Unsupported file format: {ext}")
        return xyz, rgb

    def generate_dem(self, pcd_path: str, config: DemConfig):
        # 读取点云数据
        if config.colors_data is not None:
            ground_points, ground_colors = self.read_pointcloud(pcd_path)
        else:
            ground_points, _ = self.read_pointcloud(pcd_path)
            ground_colors = None

        # 网格大小设置
        min_x, max_x = ground_points[:, 0].min(), ground_points[:, 0].max()
        min_y, max_y = ground_points[:, 1].min(), ground_points[:, 1].max()
        self.grid_x, self.grid_y = np.meshgrid(
            np.linspace(min_x, max_x, config.grid_size),
            np.linspace(min_y, max_y, config.grid_size),
        )

        if config.method == "idw":
            self.dem = idw_interpolation(ground_points, self.grid_x, self.grid_y)
        elif config.method == "kriging":
            self.dem = kriging_interpolation(ground_points, self.grid_x, self.grid_y)

        # 颜色插值
        if ground_colors is not None:
            self.color_grid = nearest_color_interpolation(
                ground_points, ground_colors, self.grid_x, self.grid_y
            )

    def save_dem(self, output_path: str):
        # 保存 DEM 为 GeoTIFF 格式
        profile, elevation, rgb = self.export_dem()
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(elevation, 1)
            if rgb is not None:
                dst.write(rgb[0], 2)
                dst.write(rgb[1], 3)
                dst.write(rgb[2], 4)

    def export_dem(self):
        if self.dem is None:
            raise ValueError("DEM data has not been generated yet.")
        if self.profile is None:
            height, width = self.dem.shape
            xres = (self.grid_x.max() - self.grid_x.min()) / (width - 1)
            yres = (self.grid_y.max() - self.grid_y.min()) / (height - 1)
            lon0 = self.grid_x.min()
            lat0 = self.grid_y.max()
            transform = from_origin(lon0, lat0, xres, yres)
            crs = "EPSG:4326"
            # 如果rgb是(高, 宽, 3)，转为(3, 高, 宽)
            if self.color_grid.shape[-1] == 3:  # noqa: PLR2004
                self.color_grid = np.transpose(self.color_grid, (2, 0, 1))
            self.profile = Profile(
                driver="GTiff",
                dtype=self.dem.dtype.name,
                count=4,
                height=height,
                width=width,
                crs=crs,
                transform=transform,
                compress="lzw",
                tiled=True,
                blockxsize=256,
                blockysize=256,
            )
        return self.profile, self.dem, self.color_grid
