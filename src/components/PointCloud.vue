<template>
    <Viewer3D data-type="pointcloud" api-endpoint="/api/pointcloud" control-panel-title="点云控制面板"
        loading-text="正在加载PLY文件..." @update-status="emit('updateStatus', $event)" @viewer-ready="onViewerReady">
        <!-- 自定义模型信息显示 -->
        <template #model-info="{ modelInfo }">
            <p>点数量: {{ modelInfo.pointCount }}</p>
            <p>文件大小: {{ modelInfo.fileSize }}</p>
        </template>
    </Viewer3D>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import * as THREE from 'three'
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader.js'
import { fetch } from '@tauri-apps/plugin-http'
import { BACKEND_API_URL } from '../config/api'
import Viewer3D, { type ViewerAPI } from './3DViewer.vue'

// 事件定义
const emit = defineEmits(['updateStatus'])

// 响应式数据
let viewerAPI: ViewerAPI | null = null
let pointCloud: THREE.Points | null = null
let currentMaterial: THREE.PointsMaterial | null = null

// 当3D查看器准备好时的回调
const onViewerReady = (api: ViewerAPI) => {
    viewerAPI = api
    // 自动加载点云数据
    autoLoadPLYFromAPI()
}

// 从后端API加载PLY文件
const autoLoadPLYFromAPI = async () => {
    if (!viewerAPI) return

    emit('updateStatus', '正在从后端加载点云数据...')

    try {
        const response = await fetch(`${BACKEND_API_URL}/api/pointcloud`, {
            method: 'GET',
            headers: {
                'Accept': 'application/octet-stream, model/ply, */*'
            }
        })

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
        }

        const arrayBuffer = await response.arrayBuffer()
        const loader = new PLYLoader()

        try {
            const geometry = loader.parse(arrayBuffer)

            // 清除之前的点云
            if (pointCloud) {
                viewerAPI.removeObject(pointCloud)
                if (currentMaterial) {
                    currentMaterial.dispose()
                }
                if (pointCloud.geometry) {
                    pointCloud.geometry.dispose()
                }
            }

            // 计算几何体法线
            if (!geometry.attributes.normal) {
                geometry.computeVertexNormals()
            }

            // 居中几何体
            geometry.center()

            // 创建材质
            currentMaterial = new THREE.PointsMaterial({
                size: 0.001,
                vertexColors: geometry.attributes.color ? true : false
            })

            if (!geometry.attributes.color) {
                currentMaterial.color.setHex(0xffffff)
            }

            // 创建点云对象
            pointCloud = new THREE.Points(geometry, currentMaterial)
            viewerAPI.addObject(pointCloud)

            // 设置模型信息
            const pointCount = geometry.attributes.position.count
            const fileSizeBytes = arrayBuffer.byteLength
            const fileSize = formatFileSize(fileSizeBytes)

            viewerAPI.setModelInfo({
                pointCount,
                fileSize
            })            // 自动适配视图
            viewerAPI.fitToView()
            viewerAPI.setLoadedState(true)

            const successMsg = '点云数据加载成功!'
            emit('updateStatus', successMsg)
            ElMessage.success(successMsg)

        } catch (parseError) {
            console.error('Error parsing PLY data:', parseError)
            const errorMsg = '解析PLY数据失败，文件格式可能不正确'
            emit('updateStatus', errorMsg)
            ElMessage.error(errorMsg)
        }

    } catch (error) {
        console.error('Error loading PLY from API:', error)
        const errorMsg = '从后端获取点云数据失败，请检查网络连接和后端服务'
        emit('updateStatus', errorMsg)
        ElMessage.error(errorMsg)
    }
}

const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
};

</script>

