<template>
    <div class="point-cloud-viewer" v-loading="!isModelLoaded" element-loading-text="正在加载PLY文件...">
        <!-- 控制面板 -->
        <div v-if="isModelLoaded" class="control-panel">
            <el-card class="controls-card">
                <template #header>
                    <span>控制面板</span>
                </template>

                <!-- 变换控制 -->
                <div class="control-group">
                    <h4>变换操作</h4>
                    <el-row :gutter="10" justify="space-between">
                        <el-col :span="9">
                            <el-button @click="resetView" type="primary" size="small">
                                重置视角
                            </el-button>
                        </el-col>
                        <el-col :span="9">
                            <el-button @click="fitToView" type="success" size="small">
                                适配视图
                            </el-button>
                        </el-col>
                    </el-row>
                </div>
                <!-- 鼠标控制说明 -->
                <div class="control-group">
                    <h4>鼠标控制说明</h4>
                    <div class="mouse-controls-info">
                        <div class="control-item">
                            <span class="control-label">🖱️ 左键拖拽：</span>
                            <span class="control-desc">旋转视角</span>
                        </div>
                        <div class="control-item">
                            <span class="control-label">🖲️ 中键拖拽：</span>
                            <span class="control-desc">平移视图</span>
                        </div>
                        <div class="control-item">
                            <span class="control-label">🛞 滚轮：</span>
                            <span class="control-desc">缩放视图</span>
                        </div>
                        <div class="control-item">
                            <span class="control-label">🖱️ 双击：</span>
                            <span class="control-desc">重置视角</span>
                        </div>
                    </div>
                </div>

                <!-- 模型信息 -->
                <div v-if="modelInfo" class="model-info">
                    <h4>模型信息</h4>
                    <p>点数量: {{ modelInfo.pointCount }}</p>
                    <p>文件大小: {{ modelInfo.fileSize }}</p>
                </div>
            </el-card>
        </div>

        <!-- 3D渲染区域 -->
        <div class="render-container">
            <div ref="threeContainer" class="three-container"></div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader.js'
import { fetch } from '@tauri-apps/plugin-http'
import { BACKEND_API_URL } from '../config/api'

// 添加emit定义
const emit = defineEmits(['updateStatus'])

// 响应式数据
const threeContainer = ref<HTMLElement>()
const isModelLoaded = ref(false)
const modelInfo = ref<{
    pointCount: number
    fileSize: string
} | null>(null)

// Three.js 对象
let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let controls: OrbitControls
let pointCloud: THREE.Points | null = null
let currentMaterial: THREE.PointsMaterial | null = null

// 初始化Three.js场景
const initThreeJS = async () => {
    if (!threeContainer.value) return

    // 创建场景
    scene = new THREE.Scene()
    scene.background = new THREE.Color(0x1a1a1a)

    // 创建相机
    const container = threeContainer.value
    camera = new THREE.PerspectiveCamera(
        75,
        container.clientWidth / container.clientHeight,
        0.1,
        1000
    )
    camera.position.set(5, 5, 5)

    // 创建渲染器
    renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(container.clientWidth, container.clientHeight)
    renderer.setPixelRatio(window.devicePixelRatio)
    container.appendChild(renderer.domElement)
    // 创建轨道控制器 - 支持完整的鼠标控制
    controls = new OrbitControls(camera, renderer.domElement)

    // 基础设置
    controls.enableDamping = true
    controls.dampingFactor = 0.05
    controls.screenSpacePanning = false

    // 鼠标控制设置
    // 左键：旋转控制
    controls.enableRotate = true
    controls.rotateSpeed = 1.0
    controls.mouseButtons.LEFT = THREE.MOUSE.ROTATE

    // 中键：平移控制
    controls.enablePan = true
    controls.panSpeed = 1.0
    controls.mouseButtons.MIDDLE = THREE.MOUSE.PAN

    // 右键：禁用（避免右键菜单冲突）
    controls.mouseButtons.RIGHT = null

    // 滚轮：缩放控制
    controls.enableZoom = true
    controls.zoomSpeed = 1.0
    controls.minDistance = 0.1
    controls.maxDistance = 1000
    // 旋转限制
    controls.minPolarAngle = 0 // 垂直旋转的最小角度
    controls.maxPolarAngle = Math.PI // 垂直旋转的最大角度

    // 添加鼠标事件监听
    setupMouseEvents()

    // 添加灯光
    const ambientLight = new THREE.AmbientLight(0x404040, 0.6)
    scene.add(ambientLight)

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8)
    directionalLight.position.set(10, 10, 5)
    scene.add(directionalLight)

    // 开始渲染循环
    animate()

    // 监听窗口大小变化
    window.addEventListener('resize', onWindowResize)
}

// 动画循环
const animate = () => {
    requestAnimationFrame(animate)

    if (controls) {
        controls.update()
    }

    if (renderer && scene && camera) {
        renderer.render(scene, camera)
    }
}

// 窗口大小变化处理
const onWindowResize = () => {
    if (!threeContainer.value || !camera || !renderer) return

    const container = threeContainer.value
    camera.aspect = container.clientWidth / container.clientHeight
    camera.updateProjectionMatrix()
    renderer.setSize(container.clientWidth, container.clientHeight)
}

// 设置鼠标事件
const setupMouseEvents = () => {
    if (!renderer) return

    const canvas = renderer.domElement

    // 双击重置视角
    canvas.addEventListener('dblclick', (event) => {
        event.preventDefault()
        resetView()
        ElMessage.info('视角已重置')
    })

    // 禁用右键菜单（避免与控制冲突）
    canvas.addEventListener('contextmenu', (event) => {
        event.preventDefault()
    })

    // 鼠标进入时显示光标提示
    canvas.addEventListener('mouseenter', () => {
        canvas.style.cursor = 'grab'
    })

    // 鼠标离开时恢复光标
    canvas.addEventListener('mouseleave', () => {
        canvas.style.cursor = 'default'
    })

    // 鼠标按下时改变光标样式
    canvas.addEventListener('mousedown', (event) => {
        if (event.button === 0) { // 左键
            canvas.style.cursor = 'grabbing'
        } else if (event.button === 1) { // 中键
            canvas.style.cursor = 'move'
        }
    })

    // 鼠标松开时恢复光标
    canvas.addEventListener('mouseup', () => {
        canvas.style.cursor = 'grab'
    })

    // 滚轮事件的额外处理
    canvas.addEventListener('wheel', (event) => {
        // 阻止页面滚动
        event.preventDefault()

        // 可以在这里添加额外的缩放反馈
        if (event.deltaY > 0) {
            // 向外滚动（缩小）
        } else {
            // 向内滚动（放大）
        }
    }, { passive: false })
}

// 从后端API加载PLY文件
const autoLoadPLYFromAPI = async () => {
    emit('updateStatus', '正在从后端加载点云数据...')

    try {
        // 使用API请求工具，自动处理不同环境的URL
        const response = await fetch(`${BACKEND_API_URL}/api/pointcloud`, {
            method: 'GET',
            headers: {
                'Accept': 'application/octet-stream, model/ply, */*'
            }
        })

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`)
        }

        // 获取响应的arraybuffer
        const arrayBuffer = await response.arrayBuffer()

        // 使用PLYLoader解析数据
        const loader = new PLYLoader()

        try {
            const geometry = loader.parse(arrayBuffer)

            // 清除之前的点云
            if (pointCloud) {
                scene.remove(pointCloud)
                if (currentMaterial) {
                    currentMaterial.dispose()
                }
                if (pointCloud.geometry) {
                    pointCloud.geometry.dispose()
                }
            }

            // 计算几何体法线（如果需要）
            if (!geometry.attributes.normal) {
                geometry.computeVertexNormals()
            }

            // 居中几何体
            geometry.center()

            // 创建材质，使用固定的点大小
            currentMaterial = new THREE.PointsMaterial({
                size: 0.001, // 使用固定的0.001大小
                vertexColors: geometry.attributes.color ? true : false
            })

            // 如果没有颜色属性，使用默认白色
            if (!geometry.attributes.color) {
                currentMaterial.color.setHex(0xffffff)
            }

            // 创建点云对象
            pointCloud = new THREE.Points(geometry, currentMaterial)
            scene.add(pointCloud)

            // 设置模型信息
            const pointCount = geometry.attributes.position.count
            const fileSizeBytes = arrayBuffer.byteLength
            const fileSize = formatFileSize(fileSizeBytes)

            modelInfo.value = {
                pointCount,
                fileSize
            }

            // 自动适配视图
            fitToView()

            isModelLoaded.value = true

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

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 重置视角
const resetView = () => {
    if (!camera || !controls) return

    camera.position.set(5, 5, 5)
    camera.lookAt(0, 0, 0)
    controls.reset()
}

// 适配视图
const fitToView = () => {
    if (!pointCloud || !camera || !controls) return

    const box = new THREE.Box3().setFromObject(pointCloud)
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())

    const maxDim = Math.max(size.x, size.y, size.z)
    const fov = camera.fov * (Math.PI / 180)
    let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2))

    cameraZ *= 2 // 添加一些边距

    camera.position.set(center.x, center.y, center.z + cameraZ)
    camera.lookAt(center)
    controls.target.copy(center)
    controls.update()
}

// 生命周期钩子
onMounted(async () => {
    await nextTick()
    await initThreeJS()
    // 自动加载点云数据
    await autoLoadPLYFromAPI()
})

onUnmounted(() => {
    window.removeEventListener('resize', onWindowResize)

    // 清理Three.js资源
    if (renderer) {
        renderer.dispose()
    }
    if (currentMaterial) {
        currentMaterial.dispose()
    }
    if (pointCloud && pointCloud.geometry) {
        pointCloud.geometry.dispose()
    }
})
</script>

<style scoped>
.point-cloud-viewer {
    display: flex;
    height: calc(100vh - 100px);
    background: #f5f5f5;
}

.control-panel {
    width: 250px;
    padding: 20px;
    background: white;
    border-right: 1px solid #e4e7ed;
    overflow-y: auto;
}

.controls-card {
    margin-bottom: 20px;
}

.control-group {
    margin-bottom: 20px;
}

.control-group h4 {
    margin: 0 0 15px 0;
    color: #303133;
    font-size: 14px;
    font-weight: 600;
}

.model-info {
    padding: 15px;
    background: #f8f9fa;
    border-radius: 4px;
    margin-top: 15px;
}

.model-info h4 {
    margin: 0 0 10px 0;
    color: #303133;
    font-size: 14px;
    font-weight: 600;
}

.model-info p {
    margin: 5px 0;
    color: #606266;
    font-size: 12px;
}

.render-container {
    flex: 1;
    position: relative;
    overflow: hidden;
}

.three-container {
    width: 100%;
    height: 100%;
}

.mouse-controls-info {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 6px;
    border: 1px solid #e9ecef;
}

.control-item {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
    font-size: 14px;
}

.control-item:last-child {
    margin-bottom: 0;
}

.control-label {
    font-weight: 600;
    color: #495057;
    min-width: 120px;
    display: inline-block;
}

.control-desc {
    color: #6c757d;
}
</style>
