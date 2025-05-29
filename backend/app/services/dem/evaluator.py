import rasterio
from rasterio.warp import reproject, Resampling
import numpy as np

def load_dem(dem_path, ref_path):
    # 打开参考 DEM（真值 DEM）
    with rasterio.open(ref_path) as ref_ds:
        ref_data = ref_ds.read(1)
        ref_transform = ref_ds.transform
        ref_crs = ref_ds.crs
        ref_shape = ref_data.shape

    # 打开待对齐的 DEM（生成的 DEM）
    with rasterio.open(dem_path) as dem_ds:
        dem_data = dem_ds.read(1)
        dem_transform = dem_ds.transform
        dem_crs = dem_ds.crs

        # 创建与参考 DEM 相同形状和类型的数组
        aligned_dem = np.empty(ref_shape, dtype=dem_data.dtype)

        # 重采样到参考 DEM 的空间分辨率和大小
        reproject(
            source=dem_data,
            destination=aligned_dem,
            src_transform=dem_transform,
            src_crs=dem_crs,
            dst_transform=ref_transform,
            dst_crs=ref_crs,
            resampling=Resampling.bilinear
        )

    return aligned_dem, ref_data

def compute_rmse(pred, gt):
    mask = ~np.isnan(gt) & ~np.isnan(pred)
    diff = pred[mask] - gt[mask]
    return np.sqrt(np.mean(diff ** 2))
