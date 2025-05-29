# 点云到DEM（GeoTIFF）再到OBJ模型流程

## 1. 点云生成DEM（GeoTIFF）

运行`run_generate.py`，将点云文件转换为DEM高程GeoTIFF文件，并可选保留颜色信息。

### 命令示例：

默认会读取`../pcd_data/point_cloud.ply`，输出 DEM 到`../output_dem.tif`。

可根据需要修改`run_generate.py`里的`file_path`和参数。

```
file_path = "../pcd_data//point_cloud.ply"
ground_fliter = None  # 是否进行地面点提取
color_data = True  # 是否保留颜色信息
method = "idw"  # "idw" or "kriging"
grid_size = 100  # 网格大小
```

### 主要流程：

- 读取点云（支持`.ply`,`.pcd`,`.las`,`.laz`）。
- 可选地进行地面点提取与颜色提取。
- 采用 IDW 或 Kriging 插值生成规则DEM网格。
- 保存为 GeoTIFF 文件（包含高程和颜色）。

## 2. DEM（GeoTIFF）转厚底OBJ模型

运行`run_dem_to_obj.py`，将DEM GeoTIFF文件转换为带厚底的三维OBJ模型，并生成纹理贴图。

### 命令示例：
```
python src/run_generate.py
```

- 默认读取`../output_dem.tif`
- 输出 OBJ 到`../output_thick.obj`
- 纹理为`../output_thick.png`

可在脚本内调整厚度等参数。

### 主要流程：

- 读取DEM高程和颜色数据。
- 生成顶面、底面和四周侧壁的三维网格。
- 生成MTL材质文件和PNG纹理贴图。
- 支持PyVista可视化模型和纹理。

## 3. 可选：DEM（GeoTIFF）转普通OBJ网格

如果只需表面网格（无厚底），可运行：
```
python src/run_dem_to_mesh.py
```

默认读取`../output_dem.tif`，输出`../output.obj`。

## 4. 依赖环境

请确保已安装以下Python库：
```
pip install numpy open3d laspy rasterio tqdm pyvista imageio
```

## 5. 文件结构参考

- 点云数据：`point_cloud.ply`（或其他格式）
- DEM输出：`output_dem.tif`
- OBJ输出：`output_thick.obj`、`output_thick.png`、`output_thick.mtl`

## 6. 可视化
运行命令：
```
python src/run_obj_thick_visualize.py
```

OBJ模型可用PyVista工具直接可视化。

如需自定义参数（如插值方法、网格大小、厚度等），可直接修改对应脚本的参数。

## 7. DEM评估

运行命令：（还未写）
```
python src/run_evaluate.py
```
## 流程图

```
点云(.ply/.las/.pcd)
      │
      ▼
run_generate.py
      │
      ▼
DEM GeoTIFF(.tif)
      │
      ▼
run_dem_to_obj.py
      │
      ▼
三维OBJ模型(.obj + .mtl + .png)
      │
      ▼
run_obj_thick_visualize.py
```