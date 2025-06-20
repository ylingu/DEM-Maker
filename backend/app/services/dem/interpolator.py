import numpy as np
import os
from scipy.spatial import cKDTree
from joblib import Parallel, delayed
from pykrige.ok import OrdinaryKriging
from multiprocessing import Pool

# 克里金插值
def _krige_single_row(i, grid_x_row, grid_y_row, tree, points, k_neighbors):
    row_vals = []
    for j, (gx, gy) in enumerate(zip(grid_x_row, grid_y_row)):
        dists, idxs = tree.query([gx, gy], k=k_neighbors, distance_upper_bound=30.0)
        idxs = idxs[np.isfinite(dists)]
        if len(idxs) < 3:
            row_vals.append(np.nan)
            continue
        local_pts = points[idxs]
        try:
            OK = OrdinaryKriging(
                local_pts[:, 0], local_pts[:, 1], local_pts[:, 2],
                variogram_model="linear", pseudo_inv=True, verbose=False
            )
            z, _ = OK.execute('points', np.array([gx]), np.array([gy]))
            row_vals.append(z[0])
        except Exception as e:
            row_vals.append(np.nan)
    return i, row_vals

#_local_parallel
def kriging_interpolation(points, grid_x, grid_y, k_neighbors=50, n_jobs=os.cpu_count()):
    # print("Parallel Local Kriging interpolation...")
    dem = np.full(grid_x.shape, np.nan)
    tree = cKDTree(points[:, :2])
    rows = grid_x.shape[0]

    results = Parallel(n_jobs=n_jobs, prefer="threads")(
        delayed(_krige_single_row)(i, grid_x[i], grid_y[i], tree, points, k_neighbors)
        for i in range(rows)
    )
    for i, row_vals in results:
        dem[i, :] = row_vals
    return dem

# IDW 插值
def process_row_parallel(args):
    i, grid_x_row, grid_y_row, points, k, power, min_points, tree = args
    row_result = np.full(len(grid_x_row), np.nan)
    for j in range(len(grid_x_row)):
        gx, gy = grid_x_row[j], grid_y_row[j]
        dists, idxs = tree.query([gx, gy], k=k)
        if len(np.atleast_1d(idxs)) < min_points:
            continue
        neighbor_points = points[idxs]
        zs = neighbor_points[:, 2]
        dists = np.atleast_1d(dists)
        dists[dists == 0] = 1e-12
        weights = 1 / (dists ** power)
        row_result[j] = np.sum(weights * zs) / np.sum(weights)
    return i, row_result

def idw_interpolation(points, grid_x, grid_y, power=2, k=10, min_points=3, n_jobs=os.cpu_count()):
    # print("IDW interpolation (multiprocessing)...")
    dem = np.full(grid_x.shape, np.nan)
    rows, cols = grid_x.shape

    # 建立 KDTree
    xy = points[:, :2]
    tree = cKDTree(xy)

    # 分配每一行的任务（注意只传递每行的小量数据）
    tasks = [(i, grid_x[i, :], grid_y[i, :], points, k, power, min_points, tree) for i in range(rows)]

    with Pool(processes=n_jobs) as pool:
        for i, row_result in pool.imap_unordered(process_row_parallel, tasks):
            dem[i, :] = row_result

    return dem

# 并行最近邻颜色插值
def _query_nearest(idx, flat_grid, tree, colors):
    dist, nearest_idx = tree.query(flat_grid[idx])
    return idx, colors[nearest_idx]

def nearest_color_interpolation(points, colors, grid_x, grid_y, n_jobs=os.cpu_count()):
    """
    points: (N, 2)
    colors: (N, 3) float32 in 0~1 or uint8 in 0~255
    grid_x, grid_y: meshgrid
    """
    # print("Parallel Nearest Neighbor color interpolation...")

    # 归一化颜色到0~1
    if colors.dtype == np.uint8:
        colors = colors.astype(np.float32) / 255.0
    else:
        colors = colors.astype(np.float32)
        if colors.max() > 1.1:
            colors = colors / 255.0

    flat_grid = np.column_stack((grid_x.ravel(), grid_y.ravel()))
    grid_shape = grid_x.shape
    color_grid = np.full(grid_shape + (3,), np.nan, dtype=np.float32)

    tree = cKDTree(points[:, :2])

    results = Parallel(n_jobs=n_jobs, prefer="threads", verbose=0)(
        delayed(_query_nearest)(idx, flat_grid, tree, colors)
        for idx in range(flat_grid.shape[0])
    )

    for idx, color in results:
        i, j = np.unravel_index(idx, grid_shape)
        color_grid[i, j] = color

    color_grid = np.clip(color_grid * 255, 0, 255)
    color_grid = np.nan_to_num(color_grid, nan=0).astype(np.uint8)
    return color_grid
