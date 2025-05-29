import rasterio
import numpy as np
import os
import open3d as o3d
import imageio
import pyvista as pv
import argparse

def tif_to_thick_obj(tif_path, obj_path="output_thick.obj", thickness=10.0):
    """
    Convert a DEM GeoTIFF into a 3D OBJ mesh with a flat bottom and side walls.

    Parameters:
        tif_path: str, path to the input DEM GeoTIFF file.
        obj_path: str, path to save the output OBJ file.
        thickness: float, vertical offset below the minimum elevation to create a base thickness.
    """
    # Read DEM and RGB if available
    with rasterio.open(tif_path) as src:
        data = src.read()  # (bands, H, W)
        transform = src.transform
        H, W = src.height, src.width

        elevation = data[0].astype(np.float32)
        rgb = None
        if data.shape[0] >= 4:
            # Bands: (1=elev, 2=R, 3=G, 4=B)
            rgb = np.stack([data[1], data[2], data[3]], axis=-1).astype(np.uint8)

    # Generate geographic coordinates for each pixel
    xs = np.arange(W)
    ys = np.arange(H)
    gx, gy = np.meshgrid(xs, ys)
    # 直接用 transform 变换
    lon, lat = rasterio.transform.xy(transform, gy, gx, offset='center')
    lon = np.array(lon).reshape(H, W)
    lat = np.array(lat).reshape(H, W)

    # Compute base elevation
    z_min = float(np.nanmin(elevation))
    base_z = z_min - thickness

    vertices_top = []
    colors_top = []
    for i in range(H):
        for j in range(W):
            vertices_top.append((lon[i,j], lat[i,j], float(elevation[i,j])))
            if rgb is not None:
                r, g, b = rgb[i,j]
                colors_top.append((r/255.0, g/255.0, b/255.0))
            else:
                colors_top.append((0.5, 0.5, 0.5))

    # Bottom vertices (flat)
    vertices_bottom = [(lon[i,j], lat[i,j], base_z)
                       for i in range(H) for j in range(W)]
    # Give bottom vertices a uniform color (e.g. gray)
    colors_bottom = [(0.5, 0.5, 0.5)] * (H*W)

    # Combine
    vertices = vertices_top + vertices_bottom
    colors = colors_top + colors_bottom

    # Faces: top surface
    def idx_top(i, j): return i*W + j + 1
    def idx_bot(i, j): return H*W + i*W + j + 1

    faces = []
    # Top faces (counter-clockwise viewed from above)
    for i in range(H-1):
        for j in range(W-1):
            v1 = idx_top(i, j)
            v2 = idx_top(i, j+1)
            v3 = idx_top(i+1, j)
            v4 = idx_top(i+1, j+1)
            faces.append((v1, v2, v3))
            faces.append((v2, v4, v3))

    # Bottom faces (clockwise viewed from below)
    for i in range(H-1):
        for j in range(W-1):
            v1 = idx_bot(i, j)
            v2 = idx_bot(i+1, j)
            v3 = idx_bot(i, j+1)
            v4 = idx_bot(i+1, j+1)
            faces.append((v1, v2, v3))
            faces.append((v2, v4, v3))

    # Side walls
    # Four edges: north, south, west, east
    # North edge (i=0)
    for j in range(W-1):
        t1 = idx_top(0, j)
        t2 = idx_top(0, j+1)
        b1 = idx_bot(0, j)
        b2 = idx_bot(0, j+1)
        faces.append((t1, b2, b1))
        faces.append((t1, t2, b2))
    # South edge (i=H-1)
    for j in range(W-1):
        t1 = idx_top(H-1, j)
        t2 = idx_top(H-1, j+1)
        b1 = idx_bot(H-1, j)
        b2 = idx_bot(H-1, j+1)
        faces.append((t1, b1, b2))
        faces.append((t1, b2, t2))
    # West edge (j=0)
    for i in range(H-1):
        t1 = idx_top(i, 0)
        t2 = idx_top(i+1, 0)
        b1 = idx_bot(i, 0)
        b2 = idx_bot(i+1, 0)
        faces.append((t1, b2, b1))
        faces.append((t1, t2, b2))
    # East edge (j=W-1)
    for i in range(H-1):
        t1 = idx_top(i, W-1)
        t2 = idx_top(i+1, W-1)
        b1 = idx_bot(i, W-1)
        b2 = idx_bot(i+1, W-1)
        faces.append((t1, b1, b2))
        faces.append((t1, b2, t2))

    # Write OBJ
    texture_path = obj_path.replace('.obj', '.png')
    mtl_path = obj_path.replace('.obj', '.mtl')
    # 保存纹理贴图（需上下翻转，保证与UV一致）
    if rgb is not None:
        imageio.imwrite(texture_path, np.flipud(rgb))  # 上下翻转

    # 生成UV坐标（左上为(0,0)，右下为(1,1)）
    uvs = []
    for i in range(H):
        for j in range(W):
            u = j / (W - 1)
            v = i / (H - 1)  # 注意这里v不再1-i/(H-1)，而是i/(H-1)
            uvs.append((u, v))
    uvs = uvs * 2  # 顶面和底面都用

    # 写MTL文件
    with open(mtl_path, 'w') as f:
        f.write(f"newmtl material_0\n")
        f.write(f"map_Kd {os.path.basename(texture_path)}\n")

    # 写OBJ文件
    with open(obj_path, 'w') as f:
        f.write(f"mtllib {os.path.basename(mtl_path)}\n")
        for (x, y, z) in vertices:
            f.write(f"v {x} {y} {z}\n")
        for (u, v) in uvs:
            f.write(f"vt {u} {v}\n")
        f.write("usemtl material_0\n")
        for face in faces:
            # OBJ索引从1开始，顶点和UV索引一致
            f.write(f"f {face[0]}/{face[0]} {face[1]}/{face[1]} {face[2]}/{face[2]}\n")
    print(f"OBJ+MTL+PNG saved!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Convert DEM GeoTIFF to 3D OBJ mesh with thickness.")
    parser.add_argument("--tif_path", type=str, default='../output_dem.tif', help="Path to the input DEM GeoTIFF file.")
    parser.add_argument("--obj_path", type=str, default='../output_thick.obj', help="Path to save the output OBJ file.")
    parser.add_argument("--thickness", type=float, default=5.0, help="Thickness of the base below the minimum elevation.")
    args = parser.parse_args()

    tif_to_thick_obj(args.tif_path, args.obj_path, args.thickness)

    mesh = pv.read("../output_thick.obj")
    texture = pv.read_texture("../output_thick.png")
    plotter = pv.Plotter()
    plotter.add_mesh(mesh, texture=texture, show_edges=False)
    plotter.show()
