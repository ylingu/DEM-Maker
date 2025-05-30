<template>
    <div class="viewer-3d" v-loading="!isModelLoaded" :element-loading-text="loadingText">
        <!-- 控制面板 -->
        <div v-if="isModelLoaded" class="control-panel">
            <el-card class="controls-card">
                <template #header>
                    <span>{{ controlPanelTitle }}</span>
                    <el-button @click="openTutorial" class="tutorial-button" :circle="true" color="#6c757d"
                        size="small">?</el-button>
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

                <!-- 插槽：自定义控制选项 -->
                <slot name="custom-controls"></slot>

                <!-- 模型信息 -->
                <div v-if="modelInfo" class="model-info">
                    <h4>模型信息</h4>
                    <slot name="model-info" :modelInfo="modelInfo">
                        <!-- 默认模型信息显示 -->
                        <p v-for="(value, key) in modelInfo" :key="key">
                            {{ key }}: {{ value }}
                        </p>
                    </slot>
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
import { ref, onMounted, onUnmounted, nextTick, h } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

// Props定义
interface Props {
    dataType: 'pointcloud' | 'dem'
    apiEndpoint: string
    controlPanelTitle?: string
    loadingText?: string
}

withDefaults(defineProps<Props>(), {
    controlPanelTitle: '控制面板',
    loadingText: '正在加载数据...'
})

// 事件定义
const emit = defineEmits<{
    updateStatus: [status: string]
    modelLoaded: [data: any]
    viewerReady: [viewer: ViewerAPI]
}>()

// 响应式数据
const threeContainer = ref<HTMLElement>()
const isModelLoaded = ref(false)
const modelInfo = ref<Record<string, any> | null>(null)

// Three.js 对象
let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let controls: OrbitControls
let currentObject: THREE.Object3D | null = null
let currentMaterial: THREE.Material | null = null

// 暴露给父组件的API
export interface ViewerAPI {
    scene: THREE.Scene
    camera: THREE.PerspectiveCamera
    renderer: THREE.WebGLRenderer
    controls: OrbitControls
    addObject: (object: THREE.Object3D) => void
    removeObject: (object: THREE.Object3D) => void
    clearScene: () => void
    setModelInfo: (info: Record<string, any>) => void
    setLoadedState: (loaded: boolean) => void
    resetView: () => void
    fitToView: () => void
}

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

    // 创建轨道控制器
    controls = new OrbitControls(camera, renderer.domElement)
    setupControls()

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
    window.addEventListener('resize', onWindowResize)    // 暴露API给父组件
    const viewerAPI: ViewerAPI = {
        scene,
        camera,
        renderer,
        controls,
        addObject: (object: THREE.Object3D) => {
            scene.add(object)
            currentObject = object
        },
        removeObject: (object: THREE.Object3D) => {
            scene.remove(object)
        },
        clearScene: () => {
            if (currentObject) {
                scene.remove(currentObject)
                if (currentMaterial) {
                    currentMaterial.dispose()
                }
                if (currentObject instanceof THREE.Points || currentObject instanceof THREE.Mesh) {
                    currentObject.geometry.dispose()
                }
                currentObject = null
                currentMaterial = null
            }
        },
        setModelInfo: (info: Record<string, any>) => {
            modelInfo.value = info
        },
        setLoadedState: (loaded: boolean) => {
            isModelLoaded.value = loaded
        },
        resetView,
        fitToView
    }

    emit('viewerReady', viewerAPI)
}

// 设置控制器
const setupControls = () => {
    // 基础设置
    controls.enableDamping = true
    controls.dampingFactor = 0.05
    controls.screenSpacePanning = false

    // 鼠标控制设置
    controls.enableRotate = true
    controls.rotateSpeed = 1.0
    controls.mouseButtons.LEFT = THREE.MOUSE.ROTATE

    controls.enablePan = true
    controls.panSpeed = 1.0
    controls.mouseButtons.MIDDLE = THREE.MOUSE.PAN

    controls.mouseButtons.RIGHT = null

    controls.enableZoom = true
    controls.zoomSpeed = 1.0
    controls.minDistance = 0.1
    controls.maxDistance = 1000

    controls.minPolarAngle = 0
    controls.maxPolarAngle = Math.PI
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

    // 禁用右键菜单
    canvas.addEventListener('contextmenu', (event) => {
        event.preventDefault()
    })

    // 光标样式控制
    canvas.addEventListener('mouseenter', () => {
        canvas.style.cursor = 'grab'
    })

    canvas.addEventListener('mouseleave', () => {
        canvas.style.cursor = 'default'
    })

    canvas.addEventListener('mousedown', (event) => {
        if (event.button === 0) {
            canvas.style.cursor = 'grabbing'
        } else if (event.button === 1) {
            canvas.style.cursor = 'move'
        }
    })

    canvas.addEventListener('mouseup', () => {
        canvas.style.cursor = 'grab'
    })

    canvas.addEventListener('wheel', (event) => {
        event.preventDefault()
    }, { passive: false })
}

// 重置视角
const resetView = () => {
    if (!camera || !controls) return

    // 如果有加载的对象，根据对象尺寸设置相机位置
    if (currentObject) {
        const box = new THREE.Box3().setFromObject(currentObject)
        const center = box.getCenter(new THREE.Vector3())
        const size = box.getSize(new THREE.Vector3())

        const maxDim = Math.max(size.x, size.y, size.z)
        const fov = camera.fov * (Math.PI / 180)
        let cameraDistance = Math.abs(maxDim / 2 / Math.tan(fov / 2))

        cameraDistance *= 1.5 // 添加一些边距

        // 设置相机到对象的斜上方（45度角度），便于观察DEM地形
        const cameraHeight = cameraDistance * 0.7
        const cameraHorizontal = cameraDistance * 0.7

        camera.position.set(
            center.x + cameraHorizontal,
            center.y + cameraHeight,
            center.z + cameraHorizontal
        )
        camera.lookAt(center)
        controls.target.copy(center)
    } else {
        // 如果没有对象，使用默认位置
        camera.position.set(5, 5, 5)
        camera.lookAt(0, 0, 0)
        controls.target.set(0, 0, 0)
    }

    controls.update()
}

// 适配视图
const fitToView = () => {
    if (!currentObject || !camera || !controls) return

    const box = new THREE.Box3().setFromObject(currentObject)
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

// 设置加载状态
const setLoadedState = (loaded: boolean) => {
    isModelLoaded.value = loaded
}

const openTutorial = () => {
    ElMessageBox(
        {
            message: h('div', { class: 'mouse-control-info' }, [
                h('h4', {
                    style: {
                        color: '#303133',
                        fontSize: '18px',
                        fontWeight: '600',
                        textAlign: 'center',
                    }
                }, '鼠标控制说明'),
                h('div', { class: 'control-item' }, [
                    h('span', { class: 'control-label' }, '🖱️ 左键拖拽：'),
                    h('span', { class: 'control-desc' }, '旋转视角')
                ]), h('div', { class: 'control-item' }, [
                    h('span', { class: 'control-label' }, '🖲️ 中键拖拽：'),
                    h('span', { class: 'control-desc' }, '平移视图')
                ]), h('div', { class: 'control-item' }, [
                    h('span', { class: 'control-label' }, '🛞 滚轮：'),
                    h('span', { class: 'control-desc' }, '缩放视图')
                ]), h('div', { class: 'control-item' }, [
                    h('span', { class: 'control-label' }, '🖱️ 双击：'),
                    h('span', { class: 'control-desc' }, '平移视图')
                ])
            ]),
            center: true,
        }
    )
}

// 暴露方法给父组件
defineExpose({
    setLoadedState,
    resetView,
    fitToView
})

// 生命周期钩子
onMounted(async () => {
    await nextTick()
    await initThreeJS()
})

onUnmounted(() => {
    window.removeEventListener('resize', onWindowResize)

    // 清理Three.js资源 - 按正确的顺序    
    // 1. 先清理材质的纹理引用
    if (currentMaterial) {
        if ('map' in currentMaterial && currentMaterial.map) {
            currentMaterial.map = null
        }
        currentMaterial.needsUpdate = true
    }

    // 2. 清理场景中的对象
    if (currentObject) {
        if (scene) {
            scene.remove(currentObject)
        }
        if (currentObject instanceof THREE.Points || currentObject instanceof THREE.Mesh) {
            if (currentObject.geometry) {
                currentObject.geometry.dispose()
            }
        }
    }

    // 3. 清理材质
    if (currentMaterial) {
        currentMaterial.dispose()
    }

    // 4. 清理场景
    if (scene) {
        scene.clear()
    }

    // 5. 最后清理渲染器
    if (renderer) {
        if (renderer.domElement && renderer.domElement.parentNode) {
            renderer.domElement.parentNode.removeChild(renderer.domElement)
        }
        renderer.dispose()
    }
})
</script>

<style scoped>
.viewer-3d {
    display: flex;
    height: calc(100vh - 100px);
    background: #f5f5f5;
}

.control-panel {
    min-width: 250px;
    padding: 20px;
    background: white;
    border-right: 1px solid #e4e7ed;
    overflow-y: auto;
}

.controls-card {
    margin-bottom: 20px;
}

.controls-card :deep(.el-card__header) {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 10px;
    position: relative;
    border-bottom: 1px solid #e4e7ed;
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

.model-info :deep(p) {
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

.mouse-control-info {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 6px;
    border: 1px solid #e9ecef;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
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

.tutorial-button {
    font-size: 16px;
    font-weight: bold;
    cursor: pointer;
    display: flex;
    justify-content: center;
    align-items: center;
}
</style>
<style>
.control-group {
    margin-bottom: 20px;
}

.control-group h4 {
    margin: 0 0 15px 0;
    color: #303133;
    font-size: 18px;
    font-weight: 600;
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
</style>