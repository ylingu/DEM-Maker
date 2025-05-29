import rasterio
import numpy as np
import os
import open3d as o3d
import argparse

def tif_to_obj(tif_path, obj_path):
    with rasterio.open(tif_path) as src:
        data = src.read()  # shape: (band, height, width)
        transform = src.transform
        height, width = src.height, src.width

        # 读取高程和颜色
        elevation = data[0]
        if data.shape[0] >= 4:
            rgb = np.stack([data[1], data[2], data[3]], axis=0)
        else:
            rgb = None

        # 生成网格坐标
        xs = np.arange(width)
        ys = np.arange(height)
        grid_x, grid_y = np.meshgrid(xs, ys)
        lon, lat = rasterio.transform.xy(transform, grid_y, grid_x)
        lon = np.array(lon).reshape(height, width)
        lat = np.array(lat).reshape(height, width)

        # 构建顶点和颜色
        vertices = []
        colors = []
        for i in range(height):
            for j in range(width):
                x = lon[i, j]
                y = lat[i, j]
                z = elevation[i, j]
                vertices.append((x, y, z))
                if rgb is not None:
                    r = rgb[0, i, j]
                    g = rgb[1, i, j]
                    b = rgb[2, i, j]
                    colors.append((r / 255.0, g / 255.0, b / 255.0))
                else:
                    colors.append((1, 1, 1))

        # 构建面
        def idx(i, j):
            return i * width + j + 1  # obj索引从1开始

        faces = []
        for i in range(height - 1):
            for j in range(width - 1):
                v1 = idx(i, j)
                v2 = idx(i, j + 1)
                v3 = idx(i + 1, j)
                v4 = idx(i + 1, j + 1)
                faces.append((v1, v2, v3))
                faces.append((v2, v4, v3))

        # 写入obj文件
        with open(obj_path, "w") as f:
            for v, c in zip(vertices, colors):
                f.write(f"v {v[0]} {v[1]} {v[2]} {c[0]} {c[1]} {c[2]}\n")
            for face in faces:
                f.write(f"f {face[0]} {face[1]} {face[2]}\n")
        print(f"OBJ file saved at: {os.path.abspath(obj_path)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert DEM GeoTIFF to Mesh.")
    parser.add_argument("--tif_path", type=str, help="Path to the input DEM GeoTIFF file.")
    parser.add_argument("--obj_path", type=str, help="Path to save the output OBJ file.")
    args = parser.parse_args()
    tif_to_obj(args.tif_path, args.obj_path)

    # 可视化OBJ
    mesh = o3d.io.read_triangle_mesh(args.obj_path)
    mesh.compute_vertex_normals()
    o3d.visualization.draw_geometries([mesh], window_name="DEM OBJ Visualization")