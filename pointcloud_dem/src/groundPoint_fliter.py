# 地面点筛选
import numpy as np
import json
from osgeo import gdal
import pdal
import laspy
import os
from tqdm import tqdm

def filter_pointcloud(pointcloud, colors=None):
    """
    使用PDAL的progressive morphological filter提取地面点，
    并对地面点缺陷区域进行补齐（用最近邻z值填补）。
    """
    print("Filtering point cloud (ground extraction)...")
    import tempfile
    from scipy.spatial import cKDTree

    # 1. 写入临时LAS文件（保持原始精度）
    with tempfile.NamedTemporaryFile(suffix=".las", delete=False) as tmp:
        tmp_input = tmp.name
    header = laspy.LasHeader(point_format=3, version="1.2")
    las = laspy.LasData(header)
    las.x, las.y, las.z = pointcloud[:, 0], pointcloud[:, 1], pointcloud[:, 2]
    las.write(tmp_input)

    # 2. PDAL地面点提取
    pipeline = {
        "pipeline": [
            tmp_input,
            {
                "type": "filters.pmf",
                "max_window_size": 33,
                "slope": 1.0,
                "initial_distance": 0.5,
                "cell_size": 1.0
            },
            {
                "type": "filters.range",
                "limits": "Classification[2:2]"
            }
        ]
    }

    p = pdal.Pipeline(json.dumps(pipeline))
    p.execute()
    arrays = p.arrays[0]
    ground_points = np.vstack((arrays['X'], arrays['Y'], arrays['Z'])).T

    os.remove(tmp_input)

    # 3. 补齐缺陷区域（如有空洞，用最近邻补齐）
    if ground_points.shape[0] < pointcloud.shape[0] * 0.2:
        print("Warning: Too few ground points detected, skipping filling.")
        return ground_points

    # 用cKDTree查找未被分为地面点的区域
    tree = cKDTree(ground_points[:, :2])
    dist, idx = tree.query(pointcloud[:, :2], k=1)
    fill_mask = dist > 2.0  # 2米外认为是缺陷
    if np.any(fill_mask):
        print(f"Filling {np.sum(fill_mask)} missing ground points...")
        filled_points = pointcloud[fill_mask].copy()
        # tqdm用在替换Z的地方
        tree = cKDTree(ground_points[:, :2])
        _, idx = tree.query(pointcloud[:, :2], k=1)
        with tqdm(total=np.sum(fill_mask), desc="Filling ground points", ncols=80) as pbar:
            filled_points[:, 2] = ground_points[idx[fill_mask], 2]
            pbar.update(np.sum(fill_mask))
        ground_points = np.vstack([ground_points, filled_points])

    # 匹配地面点颜色
    if colors is not None and pointcloud.shape[0] == colors.shape[0]:
        tree = cKDTree(pointcloud[:, :3])
        ground_colors = np.empty_like(ground_points)
        idx = np.empty(ground_points.shape[0], dtype=int)
        with tqdm(total=ground_points.shape[0], desc="Matching colors", ncols=80) as pbar:
            # 分批处理以显示进度条
            batch_size = 10000
            for start in range(0, ground_points.shape[0], batch_size):
                end = min(start + batch_size, ground_points.shape[0])
                _, idx[start:end] = tree.query(ground_points[start:end], k=1)
                pbar.update(end - start)
        ground_colors = colors[idx]
    else:
        ground_colors = None
    
    return ground_points, ground_colors