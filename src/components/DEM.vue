<template>
    <Viewer3D data-type="dem" api-endpoint="/api/dem" control-panel-title="DEM控制面板" loading-text="正在加载DEM数据..."
        @update-status="emit('updateStatus', $event)" @viewer-ready="onViewerReady">
        <!-- DEM特有的控制选项 -->
        <template #custom-controls>
            <div class="control-group">
                <h4>地形设置</h4>
                <el-row :gutter="10">
                    <el-col :span="24">
                        <div class="control-item">
                            <span class="control-label-small">高程缩放: </span>
                            <el-slider v-model="heightScale" :min="1" :max="10" :step="0.1"
                                @change="updateHeightScale" />
                            <span class="slider-value">{{ heightScale }}x</span>
                        </div>
                    </el-col>
                </el-row>

                <el-row :gutter="10" style="margin-top: 15px;" justify="space-between">
                    <el-col :span="9">
                        <el-button @click="toggleWireframe" :type="wireframeMode ? 'primary' : 'default'" size="small">
                            {{ wireframeMode ? '实体模式' : '线框模式' }}
                        </el-button>
                    </el-col>
                    <el-col :span="9">
                        <el-button @click="toggleTexture" :type="showTexture ? 'success' : 'default'" size="small">
                            {{ showTexture ? '高程映射' : '原始纹理' }}
                        </el-button>
                    </el-col>
                </el-row> <el-row :gutter="10" style="margin-top: 15px;">
                    <el-col :span="24"> <el-button @click="showSaveDialog" type="success" size="large"
                            style="width: 100%;">
                            📥 保存DEM数据
                        </el-button>
                    </el-col>
                </el-row>
            </div>
        </template>
        <!-- 自定义模型信息显示 -->
        <template #model-info="{ modelInfo }">
            <p>尺寸: {{ modelInfo.dimensions }}</p>
            <p>分辨率: {{ modelInfo.resolution }}</p>
            <p>坐标系: {{ modelInfo.crs || 'Unknown' }}</p>
        </template>
    </Viewer3D>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { save } from '@tauri-apps/plugin-dialog'
import * as THREE from 'three'
import { fetch } from '@tauri-apps/plugin-http'
import { BACKEND_API_URL } from '../config/api'
import Viewer3D, { type ViewerAPI } from './3DViewer.vue'

// 事件定义
const emit = defineEmits(['updateStatus'])

// 响应式数据
const heightScale = ref(1.0)
const wireframeMode = ref(false)
const showTexture = ref(true)

let viewerAPI: ViewerAPI | null = null
let demMesh: THREE.Mesh | null = null
let demMaterial: THREE.MeshLambertMaterial | null = null
let elevationData: Float32Array | null = null
let originalElevation: Float32Array | null = null
let originalTexture: THREE.DataTexture | null = null
let elevationColorTexture: THREE.DataTexture | null = null

// 当3D查看器准备好时的回调
const onViewerReady = (api: ViewerAPI) => {
    viewerAPI = api
    // 自动加载DEM数据
    autoLoadDEMFromAPI()
}

// 更新高程缩放
const updateHeightScale = (newScale: number | number[]) => {
    const scale = Array.isArray(newScale) ? newScale[0] : newScale
    if (!elevationData || !originalElevation || !demMesh) return

    // 重新计算高程数据
    for (let i = 0; i < elevationData.length; i++) {
        elevationData[i] = originalElevation[i] * scale
    }    // 更新几何体 - 获取原始的DEM尺寸
    const geometry = demMesh.geometry as THREE.PlaneGeometry
    const positionAttribute = geometry.getAttribute('position')

    // 从几何体的userData中获取原始尺寸
    const demWidth = geometry.userData.demWidth
    const demHeight = geometry.userData.demHeight    // 更新Y坐标（高程）
    for (let y = 0; y < demHeight; y++) {
        for (let x = 0; x < demWidth; x++) {
            const vertexIndex = y * demWidth + x
            const elevationIndex = y * demWidth + x

            if (vertexIndex < positionAttribute.count && elevationIndex < elevationData.length) {
                // 由于几何体旋转到XZ平面，高程应该影响Z坐标
                positionAttribute.setY(vertexIndex, elevationData[elevationIndex])
            }
        }
    } positionAttribute.needsUpdate = true
    geometry.computeVertexNormals()    // 重新生成高程色彩映射纹理（因为高程值改变了）
    if (demMesh && demMaterial) {
        const geometry = demMesh.geometry as THREE.PlaneGeometry
        const demWidth = geometry.userData.demWidth
        const demHeight = geometry.userData.demHeight

        // 释放旧的高程色彩纹理
        if (elevationColorTexture) {
            elevationColorTexture.dispose()
        }
        
        elevationColorTexture = createElevationColorTexture(demWidth, demHeight)

        // 如果当前显示的是高程映射，更新纹理
        if (!showTexture.value && elevationColorTexture) {
            demMaterial.map = elevationColorTexture
            demMaterial.needsUpdate = true
        }
    }
}

// 切换线框模式
const toggleWireframe = () => {
    if (demMaterial) {
        wireframeMode.value = !wireframeMode.value
        demMaterial.wireframe = wireframeMode.value
        demMaterial.needsUpdate = true
    }
}

// 切换纹理显示
const toggleTexture = () => {
    if (demMaterial) {
        showTexture.value = !showTexture.value
        if (showTexture.value && originalTexture) {
            // 显示原始纹理
            demMaterial.map = originalTexture
        } else if (!showTexture.value && elevationColorTexture) {
            // 显示高程色彩映射
            demMaterial.map = elevationColorTexture
        }
        demMaterial.needsUpdate = true
    }
}

// 生成高程色彩映射纹理
const createElevationColorTexture = (width: number, height: number) => {
    if (!elevationData) return null

    // 计算高程数据的最小值和最大值
    let minElevation = Infinity
    let maxElevation = -Infinity
    for (let i = 0; i < elevationData.length; i++) {
        minElevation = Math.min(minElevation, elevationData[i])
        maxElevation = Math.max(maxElevation, elevationData[i])
    }

    // 创建色彩映射纹理数据
    const colorTextureData = new Uint8Array(height * width * 4) // RGBA格式

    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            const pixelIndex = y * width + x
            const textureIndex = pixelIndex * 4

            // 归一化高程值到0-1范围
            const elevation = elevationData[pixelIndex]
            const normalizedElevation = (elevation - minElevation) / (maxElevation - minElevation)

            // 使用色彩映射：蓝色(低) -> 绿色(中) -> 红色(高)
            let r, g, b
            if (normalizedElevation < 0.5) {
                // 从蓝色到绿色
                const t = normalizedElevation * 2
                r = 0
                g = Math.floor(t * 255)
                b = Math.floor((1 - t) * 255)
            } else {
                // 从绿色到红色
                const t = (normalizedElevation - 0.5) * 2
                r = Math.floor(t * 255)
                g = Math.floor((1 - t) * 255)
                b = 0
            }

            colorTextureData[textureIndex] = r
            colorTextureData[textureIndex + 1] = g
            colorTextureData[textureIndex + 2] = b
            colorTextureData[textureIndex + 3] = 255 // Alpha通道
        }
    }    // 创建纹理
    const texture = new THREE.DataTexture(colorTextureData, width, height, THREE.RGBAFormat)
    texture.flipY = true
    texture.wrapS = THREE.ClampToEdgeWrapping
    texture.wrapT = THREE.ClampToEdgeWrapping
    texture.minFilter = THREE.LinearMipmapLinearFilter
    texture.magFilter = THREE.LinearFilter
    texture.type = THREE.UnsignedByteType
    texture.generateMipmaps = true
    texture.needsUpdate = true

    return texture
}

// 从后端API加载DEM数据
const autoLoadDEMFromAPI = async () => {
    if (!viewerAPI) return

    emit('updateStatus', '正在从后端加载DEM数据...')

    try {
        // 调用统一的DEM API端点
        const response = await fetch(`${BACKEND_API_URL}/api/dem`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        })

        if (!response.ok) {
            throw new Error(`Failed to load DEM data: ${response.status}`)
        }

        const demData = await response.json()

        // 验证数据完整性 - 增强验证
        if (!demData.elevation || !demData.width || !demData.height) {
            throw new Error('DEM数据格式不完整：缺少必要的elevation、width或height字段')
        }

        // 验证数据尺寸一致性
        if (!Array.isArray(demData.elevation) || demData.elevation.length !== demData.height) {
            throw new Error('DEM高程数据尺寸与声明的高度不一致')
        }

        if (demData.elevation[0] && demData.elevation[0].length !== demData.width) {
            throw new Error('DEM高程数据尺寸与声明的宽度不一致')
        }        // 验证纹理数据（如果存在）
        if (demData.texture && Array.isArray(demData.texture)) {
            if (demData.texture.length !== demData.height) {
                console.warn('纹理数据高度与高程数据不一致，可能影响渲染效果')
            }
        }// 创建DEM网格
        createDEMMesh(demData)

        const successMsg = `DEM数据加载成功! 尺寸: ${demData.width}×${demData.height}`
        emit('updateStatus', successMsg)
        ElMessage.success('DEM数据加载成功!')
    } catch (error) {
        console.error('Error loading DEM from API:', error)
        const errorDetails = error instanceof Error ? error.message : '未知错误'
        const errorMsg = `从后端获取DEM数据失败: ${errorDetails}`
        emit('updateStatus', errorMsg)
        ElMessage.error(errorMsg)
    }
}

// 显示保存DEM数据的对话框
const showSaveDialog = async () => {
    if (!demMesh) {
        ElMessage.warning('请先加载DEM数据')
        return
    }

    try {
        const filePath = await save({
            title: '保存DEM数据',
            defaultPath: 'dem_output.tif',
            filters: [{
                name: 'GeoTIFF',
                extensions: ['tif', 'tiff']
            }]
        })

        if (filePath) {
            console.log('选择的保存路径:', filePath)
            // 直接启动保存
            await saveDEMData(filePath)
        }
    } catch (error) {
        console.error('选择保存路径失败:', error)
        ElMessage.error('选择保存路径失败')
    }
}

// 保存DEM数据
const saveDEMData = async (filePath: string) => {
    if (!demMesh) {
        ElMessage.error('没有可保存的DEM数据')
        return
    }

    try {
        emit('updateStatus', '正在保存DEM数据为 GeoTIFF 格式...')

        const requestBody = {
            format: 'geotiff',
            height_scale: heightScale.value,
            file_path: filePath
        }

        const response = await fetch(`${BACKEND_API_URL}/api/dem/save`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        })

        if (!response.ok) {
            throw new Error(`保存失败: ${response.status}`)
        }

        const result = await response.json()
        if (result.success) {
            ElMessage.success('DEM数据已成功保存为 GeoTIFF 格式')
            emit('updateStatus', `DEM数据保存成功: ${result.filename || filePath || '未知文件名'}`)
        } else {
            throw new Error(result.error || '保存失败')
        }
    } catch (error) {
        console.error('保存DEM数据时出错:', error)
        ElMessage.error(`保存失败: ${error instanceof Error ? error.message : '未知错误'}`)
        emit('updateStatus', '保存DEM数据失败')
    }
}

// 创建DEM网格
const createDEMMesh = (demData: any) => {
    if (!viewerAPI) return

    try {
        // 清除之前的网格
        if (demMesh) {
            viewerAPI.removeObject(demMesh)
            if (demMaterial) {
                demMaterial.dispose()
            }
            if (demMesh.geometry) {
                demMesh.geometry.dispose()
            }
        }        // 解析API返回的DEM数据
        const {
            width,
            height,
            elevation: elevationArray,
            texture: textureArray,
            resolution,
            crs } = demData

        emit('updateStatus', '正在处理DEM数据...')

        // 转换高程数据 - 将2D数组展平为1D数组（手动展平避免性能问题）
        const flatElevationData = []
        for (let y = 0; y < elevationArray.length; y++) {
            for (let x = 0; x < elevationArray[y].length; x++) {
                flatElevationData.push(elevationArray[y][x])
            }
        }
        elevationData = new Float32Array(flatElevationData)
        originalElevation = new Float32Array(elevationData) // 保存原始数据        // 创建平面几何体 - 使用合理的世界单位尺寸而不是像素数量
        // 将DEM缩放到合适的世界尺寸便于查看（例如100x100单位）
        const worldSize = 100
        const aspectRatio = width / height
        const worldWidth = worldSize
        const worldHeight = worldSize / aspectRatio

        const geometry = new THREE.PlaneGeometry(
            worldWidth, worldHeight,
            width - 1, height - 1
        )// 将几何体从XY平面旋转到XZ平面
        geometry.rotateX(-Math.PI / 2)

        // 保存DEM尺寸到geometry的userData中，用于后续的高程缩放
        geometry.userData.demWidth = width
        geometry.userData.demHeight = height        // 设置高程数据
        const positionAttribute = geometry.getAttribute('position')

        // PlaneGeometry顶点按行排列，需要正确映射到elevation数据
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const vertexIndex = y * width + x
                const elevationIndex = y * width + x

                if (vertexIndex < positionAttribute.count && elevationIndex < elevationData.length) {
                    // 设置高程数据到Y坐标（因为几何体已旋转到XZ平面，Y轴是高程方向）
                    positionAttribute.setY(vertexIndex, elevationData[elevationIndex] * heightScale.value)
                }
            }
        }        // 重新计算法线
        geometry.computeVertexNormals()// 创建材质 - 使用LambertMaterial获得更好的光照效果
        demMaterial = new THREE.MeshLambertMaterial({
            color: 0xffffff,
            wireframe: wireframeMode.value,
            side: THREE.DoubleSide  // 修复角度显示问题
        })        // 处理纹理数据
        if (textureArray && textureArray.length > 0) {
            try {
                // textureArray 格式是 [height][width][3] 的3D数组
                const textureData = new Uint8Array(height * width * 4) // 改为RGBA格式，多一个Alpha通道

                for (let y = 0; y < height; y++) {
                    for (let x = 0; x < width; x++) {
                        const pixelIndex = y * width + x
                        const textureIndex = pixelIndex * 4 // 改为RGBA，每个像素4个字节

                        // textureArray[y][x] 是一个包含 [R, G, B] 的数组
                        const pixel = textureArray[y] && textureArray[y][x] ? textureArray[y][x] : [0, 0, 0]
                        const r = Math.max(0, Math.min(255, pixel[0] || 0))
                        const g = Math.max(0, Math.min(255, pixel[1] || 0))
                        const b = Math.max(0, Math.min(255, pixel[2] || 0))

                        textureData[textureIndex] = r      // R
                        textureData[textureIndex + 1] = g  // G
                        textureData[textureIndex + 2] = b  // B
                        textureData[textureIndex + 3] = 255 // A (Alpha通道，完全不透明)
                    }
                }                // 创建原始纹理
                originalTexture = new THREE.DataTexture(textureData, width, height, THREE.RGBAFormat)
                originalTexture.flipY = true
                originalTexture.wrapS = THREE.ClampToEdgeWrapping
                originalTexture.wrapT = THREE.ClampToEdgeWrapping
                originalTexture.minFilter = THREE.LinearMipmapLinearFilter
                originalTexture.magFilter = THREE.LinearFilter
                originalTexture.type = THREE.UnsignedByteType
                originalTexture.generateMipmaps = true
                originalTexture.needsUpdate = true

                demMaterial.userData.originalMap = originalTexture // 保存原始纹理引用
            } catch (textureError) {
                console.warn('处理纹理数据时出现错误:', textureError)
                // 继续不使用纹理
            }
        }

        // 生成高程色彩映射纹理
        elevationColorTexture = createElevationColorTexture(width, height)

        // 根据当前状态设置纹理
        if (showTexture.value && originalTexture) {
            demMaterial.map = originalTexture
        } else if (!showTexture.value && elevationColorTexture) {
            demMaterial.map = elevationColorTexture
        }// 创建网格
        demMesh = new THREE.Mesh(geometry, demMaterial)
        viewerAPI.addObject(demMesh)

        // 设置模型信息
        viewerAPI.setModelInfo({
            dimensions: `${width} × ${height} 像素`,
            resolution: resolution ? `${resolution.x.toFixed(3)}m × ${resolution.y.toFixed(3)}m/像素` : 'Unknown',
            crs: crs || 'Unknown'
        })

        // 自动适配视图
        viewerAPI.fitToView()
        viewerAPI.setLoadedState(true)

    } catch (error) {
        console.error('Error creating DEM mesh:', error)
        const errorMsg = '创建DEM地形失败'
        emit('updateStatus', errorMsg)
        ElMessage.error(errorMsg)
    }
}

</script>

<style scoped>
.control-label-small {
    font-size: 13px;
    font-weight: 400;
    color: #606266;
    white-space: nowrap;
    min-width: 70px;
}

.slider-value {
    text-align: center;
    font-size: 12px;
    color: #606266;
    margin-left: 10px;
    min-width: 20px;
}
</style>
