<template>
    <div class="drone-control" @keydown="handleKeyDown" @keyup="handleKeyUp" tabindex="0" ref="droneControlRef">
        <div class="header-controls">
            <h2>Tello 无人机控制</h2>
            <el-button @click="openTutorial" class="tutorial-button" :circle="true" color="#6c757d"
                size="small">?</el-button>
        </div>

        <div class="connection-section">
            <el-button @click="isConnected ? disconnectDrone() : connectDrone()" :loading="connecting" size="large"
                color="#006eff" class="connect-button">
                {{ connecting ? '处理中...' : (isConnected ? '断开连接' : '连接无人机') }}
            </el-button>
        </div>

        <img :src="videoFrameSrc" alt="无人机视频流" v-if="videoFrameSrc" @error="handleVideoError" />
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, h, watch } from 'vue';
import { ElMessageBox } from 'element-plus';
import { fetch } from '@tauri-apps/plugin-http';
import WebSocket from '@tauri-apps/plugin-websocket';
import { BACKEND_API_URL, BACKEND_WS_URL } from '../config/api';

const emit = defineEmits(['updateStatus'])

const droneControlRef = ref<HTMLElement | null>(null);
const isConnected = ref(false);
const connecting = ref(false);
const connectionStatus = ref('未连接无人机');
const videoFrameSrc = ref<string | null>(null); // 用于显示通过WebSocket接收的JPEG帧 (base64)
let videoSocket: WebSocket | null = null;
let wsUnsubscribe: (() => void) | null = null; // WebSocket监听器取消订阅函数

watch(connectionStatus, (newStatus) => {
    emit('updateStatus', newStatus);
});

let keyState: { [key: string]: boolean } = {};

const openTutorial = () => {
    ElMessageBox(
        {
            title: '无人机操控教程',
            message: h('div', { class: 'tutorial-content' }, [
                h('p', '请确保无人机已连接并处于安全环境中。点击控制区域以激活键盘控制。'),
                h('ul', [
                    h('li', [h('strong', 'W:'), ' 前进']),
                    h('li', [h('strong', 'S:'), ' 后退']),
                    h('li', [h('strong', 'A:'), ' 左移']),
                    h('li', [h('strong', 'D:'), ' 右移']),
                    h('li', [h('strong', 'Q:'), ' 逆时针旋转']),
                    h('li', [h('strong', 'E:'), ' 顺时针旋转']),
                    h('li', [h('strong', '↑(方向上键):'), ' 起飞 (一次性指令)']),
                    h('li', [h('strong', '↓(方向下键):'), ' 降落 (一次性指令)']),
                    h('li', [h('strong', 'Space:'), ' 上升']),
                    h('li', [h('strong', 'Ctrl:'), ' 下降']),
                ])
            ])
        }
    )
}

const connectDrone = async () => {
    if (isConnected.value || connecting.value) return;
    connecting.value = true;
    connectionStatus.value = '正在尝试连接无人机...';
    videoFrameSrc.value = null;

    try {
        const response = await fetch(`${BACKEND_API_URL}/api/drone/connect`, {
            method: 'POST',
        });

        if (response.ok) {
            isConnected.value = true;
            connectionStatus.value = '无人机连接成功！';
            console.log('无人机连接成功');
            await initWebSocket();
            await nextTick();
            droneControlRef.value?.focus();
        } else {
            const errorData = await response.json().catch(() => ({ message: '连接失败，无法解析错误信息。' }));
            isConnected.value = false;
            connectionStatus.value = `连接失败: ${response.status} ${errorData.message || response.statusText}`;
            console.error('连接无人机失败:', errorData.message || response.statusText);
        }
    } catch (error) {
        isConnected.value = false;
        connectionStatus.value = `连接异常: ${error instanceof Error ? error.message : String(error)}`;
        console.error('连接无人机异常:', error);
    } finally {
        connecting.value = false;
    }
}

const disconnectDrone = async () => {
    if (!isConnected.value || connecting.value) return;
    connecting.value = true;
    connectionStatus.value = '正在断开连接...';

    if (videoSocket) {
        if (wsUnsubscribe) {
            wsUnsubscribe();
            wsUnsubscribe = null;
        }
        await videoSocket.disconnect().catch(() => { });
        videoSocket = null;
    }

    try {
        const response = await fetch(`${BACKEND_API_URL}/api/drone/disconnect`, {
            method: 'POST',
        });
        if (response.ok) {
            connectionStatus.value = '无人机已断开连接。';
        } else {
            const errorData = await response.json().catch(() => ({ message: '断开连接请求失败。' }));
            console.error('断开连接失败:', errorData.message || response.statusText);
            connectionStatus.value = `断开失败: ${response.status} ${errorData.message || response.statusText}`;
        }
    } catch (error) {
        connectionStatus.value = `断开连接异常: ${error instanceof Error ? error.message : String(error)}`;
        console.error('断开连接异常:', error);
    } finally {
        isConnected.value = false;
        connecting.value = false;

        // 清理blob URL以防内存泄漏
        if (videoFrameSrc.value && videoFrameSrc.value.startsWith('blob:')) {
            URL.revokeObjectURL(videoFrameSrc.value);
        }
        videoFrameSrc.value = null;
        keyState = {};
        if (!isConnected.value) { // 确保在最终断开后更新状态
            connectionStatus.value = '未连接';
        }
    }
}

const initWebSocket = async () => {
    // 清理之前的连接
    if (videoSocket) {
        if (wsUnsubscribe) {
            wsUnsubscribe();
            wsUnsubscribe = null;
        }
        await videoSocket.disconnect().catch(() => { });
        videoSocket = null;
    }

    try {
        connectionStatus.value = '正在连接视频流...';
        console.log('正在建立 WebSocket 连接...');

        // 使用 Tauri v2 WebSocket API 连接
        videoSocket = await WebSocket.connect(`${BACKEND_WS_URL}/ws/video`);
        console.log('视频流 WebSocket 已连接');
        connectionStatus.value = '视频流已连接，等待数据...';        // 添加消息监听器
        wsUnsubscribe = videoSocket.addListener((message) => {
            switch (message.type) {
                case 'Binary':
                    // 处理二进制数据
                    const uint8Array = new Uint8Array(message.data);
                    const blob = new Blob([uint8Array], { type: 'image/jpeg' });
                    const imageUrl = URL.createObjectURL(blob);

                    // 释放之前的URL以防内存泄漏
                    if (videoFrameSrc.value && videoFrameSrc.value.startsWith('blob:')) {
                        URL.revokeObjectURL(videoFrameSrc.value);
                    }

                    videoFrameSrc.value = imageUrl;
                    if (isConnected.value && connectionStatus.value !== '视频流传输中') {
                        connectionStatus.value = '视频流传输中';
                    }
                    break;
                case 'Close':
                    // 处理关闭消息
                    console.log('视频流 WebSocket 已关闭:', message.data);
                    if (isConnected.value) {
                        connectionStatus.value = '视频流连接已断开。';
                    } else {
                        connectionStatus.value = '视频流已关闭。';
                    }

                    // 清理blob URL
                    if (videoFrameSrc.value && videoFrameSrc.value.startsWith('blob:')) {
                        URL.revokeObjectURL(videoFrameSrc.value);
                    }
                    videoFrameSrc.value = null;
                    break;
                default:
                    console.log('收到未知类型消息:', message);
            }
        });

    } catch (error) {
        console.error('视频流 WebSocket 连接错误:', error);
        connectionStatus.value = '视频流连接错误。请检查后端服务。';
        videoFrameSrc.value = null;
    }
}

const handleVideoError = () => {
    console.error('加载视频帧失败。');
    connectionStatus.value = '视频帧加载失败。';
}

const sendDroneCommand = async (command: object) => {
    if (!isConnected.value) {
        connectionStatus.value = '请先连接无人机';
        console.warn('指令发送失败：未连接无人机', command);
        return;
    }
    console.log(`发送指令:`, command);
    try {
        const response = await fetch(`${BACKEND_API_URL}/api/drone/command`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(command),
        });
        if (response.ok) {
            console.log(`指令发送成功:`, command);
        } else {
            const errorData = await response.json().catch(() => ({ message: '指令发送失败，无法解析错误信息。' }));
            console.error(`指令发送失败:`, command, errorData.message || response.statusText);
        }
    } catch (error) {
        console.error(`发送指令异常:`, command, error);
    }
}


const handleKeyDown = (event: KeyboardEvent) => {
    if (!isConnected.value) return;
    const key = event.key.toLowerCase(); // 'control' for Ctrl, ' ' for Space, 'arrowup', 'arrowdown'

    // 防止特定按键的默认行为，例如Space滚动页面
    if ([' ', 'arrowup', 'arrowdown', 'control', 'w', 'a', 's', 'd', 'q', 'e'].includes(key)) { // Corrected 'd ' to 'd'
        event.preventDefault();
    }

    if (keyState[key]) return;

    keyState[key] = true;

    switch (key) {
        case 'arrowup':
            sendDroneCommand({ action: 'takeoff' });
            break;
        case 'arrowdown':
            sendDroneCommand({ action: 'land' });
            break;
        case 'w':
        case 's':
        case 'a':
        case 'd':
        case 'q':
        case 'e':
        case ' ': // Space for RC up
        case 'control': // Ctrl for RC down
            sendDroneCommand({ action: 'press', key: key });
            break;
    }
}

const handleKeyUp = (event: KeyboardEvent) => {
    if (!isConnected.value) return;
    const key = event.key.toLowerCase();
    keyState[key] = false;

    if ([' ', 'arrowup', 'arrowdown', 'control', 'w', 'a', 's', 'd', 'q', 'e'].includes(key)) {
        event.preventDefault();
    }

    switch (key) {
        case 'w':
        case 's':
        case 'a':
        case 'd':
        case 'q':
        case 'e':
        case ' ': // Space
        case 'control': // Ctrl
            sendDroneCommand({ action: 'release', key: key });
            break;
    }
}

onMounted(() => {
    if (droneControlRef.value) {
        droneControlRef.value.focus();
    }
});

onUnmounted(async () => {
    if (videoSocket) {
        if (wsUnsubscribe) {
            wsUnsubscribe();
            wsUnsubscribe = null;
        }
        await videoSocket.disconnect().catch(() => { });
        videoSocket = null;
    }

    // 清理blob URL以防内存泄漏
    if (videoFrameSrc.value && videoFrameSrc.value.startsWith('blob:')) {
        URL.revokeObjectURL(videoFrameSrc.value);
    }
});

</script>

<style scoped>
.drone-control {
    padding: 20px;
    font-family: sans-serif;
    max-width: 1000px;
    max-height: 100%;
    margin: auto;
    background-color: #f9f9f9;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    outline: none;
    overflow-y: auto;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
}

.header-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: relative;
    border-bottom: 2px solid #eee;
}


h2,
h3 {
    color: #333;
    margin-top: 20px;
    user-select: none;
}

.connect-button {
    font-size: 16px;
    color: white;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    transition: background-color 0.3s ease;
    margin-right: 10px;
    margin-top: 10px;
}

.connect-button:hover {
    background-color: #0056b3;
}

.connection-section p {
    margin-top: 10px;
    color: #555;
}

.tutorial-button {
    font-size: 16px;
    font-weight: bold;
    cursor: pointer;
    display: flex;
    justify-content: center;
    align-items: center;
}

.tutorial-button:hover {
    background-color: #5a6268;
}

img {
    min-height: 0;
    margin-top: 20px;
    object-fit: contain;
}

.tutorial-content ul {
    list-style-type: none;
    padding-left: 0;
}

.tutorial-content li {
    margin-bottom: 8px;
    line-height: 1.6;
}
</style>
