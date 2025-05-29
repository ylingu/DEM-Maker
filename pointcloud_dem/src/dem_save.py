import numpy as np
import rasterio

def save_geotiff(elevation, rgb, grid_x, grid_y, out_path="..\output_dem.tif"):
    """
    elevation: 高程二维数组
    rgb: 颜色三维数组 (高, 宽, 3) 或 (3, 高, 宽)
    grid_x, grid_y: 网格坐标
    out_path: 输出路径
    """
    from rasterio.transform import from_origin
    import numpy as np

    height, width = elevation.shape
    xres = (grid_x.max() - grid_x.min()) / (width - 1)
    yres = (grid_y.max() - grid_y.min()) / (height - 1)
    lon0 = grid_x.min()
    lat0 = grid_y.max()
    transform = from_origin(lon0, lat0, xres, yres)
    crs = "EPSG:4326"

    # 如果rgb是(高, 宽, 3)，转为(3, 高, 宽)
    if rgb is not None and rgb.shape[-1] == 3:
        rgb = np.transpose(rgb, (2, 0, 1))

    profile = {
        'driver': 'GTiff',
        'dtype': elevation.dtype,
        'count': 4,
        'height': height,
        'width': width,
        'crs': crs,
        'transform': transform,
        'compress': 'lzw',
        'tiled': True,
        'blockxsize': 256,
        'blockysize': 256,
    }

    with rasterio.open(out_path, 'w', **profile) as dst:
        dst.write(elevation, 1)
        if rgb is not None:
            dst.write(rgb[0], 2)
            dst.write(rgb[1], 3)
            dst.write(rgb[2], 4)
    print(f"GeoTIFF saved at: {out_path}")
