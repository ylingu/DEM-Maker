import laspy
import numpy as np
import os
from typing import Literal
import open3d as o3d
o3d.utility.set_verbosity_level(o3d.utility.VerbosityLevel.Error)

from .dem.interpolator import idw_interpolation, kriging_interpolation, nearest_color_interpolation
from .dem.saver import save_geotiff
from .dem.evaluator import load_dem, compute_rmse

class DemService:
    def __init__(self):
        self.pcd_path: str = None
        self.ground_fliter: bool = None
        self.colors_data: bool = True
        self.method: str = "idw"  # idw or kriging
        self.grid_size: int = 500
        self.dem: np.ndarray = None
        self.grid_x: np.ndarray = None
        self.grid_y: np.ndarray = None
        self.color_grid: np.ndarray = None
        self.obj_path: str = None

    def read_pointcloud(self, pcd_path):
        print("Reading point cloud...")
        ext = os.path.splitext(pcd_path)[1].lower()
        if ext in ['.las', '.laz']:
            with laspy.open(pcd_path) as f:
                pointcloud = f.read()
            xyz = np.vstack((pointcloud.x, pointcloud.y, pointcloud.z)).T
            if hasattr(pointcloud, 'red') and hasattr(pointcloud, 'green') and hasattr(pointcloud, 'blue'):
                rgb = np.vstack((pointcloud.red, pointcloud.green, pointcloud.blue)).T
                rgb = rgb / 65535.0 if rgb.max() > 255 else rgb / 255.0
            else:
                rgb = None
        elif ext in ['.ply', '.pcd']:
            pcd = o3d.io.read_point_cloud(pcd_path)
            xyz = np.asarray(pcd.points)
            rgb = np.asarray(pcd.colors) if len(pcd.colors) > 0 else None
        else:
            raise ValueError(f"Unsupported file format: {ext}")
        return xyz, rgb

    def visualize_pointcloud(self, points, colors=None, title="Point Cloud"):
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        if colors is not None:
            pcd.colors = o3d.utility.Vector3dVector(colors)
        o3d.visualization.draw_geometries([pcd], window_name=title)

    def generate_dem(
        self, 
        pcd_path: str,
        colors_data: bool = True,
        method: Literal["idw", "kriging"] = "idw",
        grid_size: int = 500
    ) -> np.ndarray:
        
        # 读取点云数据
        if colors_data is not None:
            points, colors = self.read_pointcloud(pcd_path)
        else:
            points, _ = self.read_pointcloud(pcd_path)
            colors = None

        # 不进行地面点筛选
        ground_points = points
        ground_colors = colors

        # 网格大小设置
        min_x, max_x = ground_points[:, 0].min(), ground_points[:, 0].max()
        min_y, max_y = ground_points[:, 1].min(), ground_points[:, 1].max()
        grid_x, grid_y = np.meshgrid(
            np.linspace(min_x, max_x, grid_size),
            np.linspace(min_y, max_y, grid_size)
        )

        if method == "idw":
            dem = idw_interpolation(ground_points, grid_x, grid_y)
            print("DEM generated using IDW.")
        elif method == "kriging":
            dem = kriging_interpolation(ground_points, grid_x, grid_y)
            print("DEM generated using Kriging.")
        else:
            raise ValueError("Invalid interpolation method. Choose 'idw' or 'kriging'.")
        
        # 颜色插值
        if ground_colors is not None:
            color_grid = nearest_color_interpolation(ground_points, ground_colors, grid_x, grid_y)
        else:
            color_grid = None

        return dem, color_grid, grid_x, grid_y

    def dem_visualization(
        self, 
        dem: np.ndarray, 
        grid_x: np.ndarray, 
        grid_y: np.ndarray, 
        color_grid: np.ndarray = None
    ):
        # 可视化 DEM 数据
        dem_points = np.column_stack((grid_x.ravel(), grid_y.ravel(), dem.ravel()))
        dem_points = dem_points[~np.isnan(dem_points[:, 2])]
        if color_grid is not None:
            flat_colors = color_grid.reshape(-1, 3).astype(np.float32) / 255.0
        else:
            flat_colors = None
        self.visualize_pointcloud(dem_points, flat_colors, title="DEM Surface")

    def save_dem(
        self,
        dem: np.ndarray,
        grid_x: np.ndarray,
        grid_y: np.ndarray,
        output_path: str,
        color_grid: np.ndarray = None
    ):
        # 保存 DEM 为 GeoTIFF 格式
        save_geotiff(dem, color_grid, grid_x, grid_y, output_path)

    def evaluate(
        self, 
        dem: np.ndarray, 
        ground_truth: np.ndarray
    ) -> dict:
        # 对比生成的DEM与参考DEM，输出评估指标（RMSE）
        aligned_pred, aligned_gt = load_dem(dem, ground_truth)
        rmse = compute_rmse(aligned_pred, aligned_gt)
        print(f"RMSE between generated DEM and ground truth DEM: {rmse:.4f}")
        return rmse