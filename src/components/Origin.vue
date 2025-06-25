<template>
    <el-card class="image-viewer">
        <template #header>
            <div class="card-header">
                <span>原始图像查看</span>
            </div>
        </template>

        <div class="image-container">
            <img v-if="imageUrl" :src="imageUrl" alt="Image" class="image-display" />
            <div v-else class="image-placeholder">
                <span>加载中或无可用图片...</span>
            </div>
        </div>

        <div class="controls">
            <el-button @click="prevImage" :disabled="currentImageId <= 1">上一张</el-button>
            <span class="image-counter">{{ currentImageId }} / {{ totalImages }}</span>
            <el-button @click="nextImage" :disabled="currentImageId >= totalImages">下一张</el-button>
        </div>

        <div class="jump-control">
            <el-input-number v-model="jumpId" :min="1" :max="totalImages" size="small" controls-position="right" />
            <el-button @click="jumpToImage" style="margin-left: 10px;">跳转</el-button>
        </div>
    </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { fetch } from '@tauri-apps/plugin-http';
import { ElMessage } from 'element-plus';
import { BACKEND_API_URL } from '../config/api';

const emit = defineEmits(['updateStatus'])
const status = ref('');
const totalImages = ref(1);
const currentImageId = ref(1);
const jumpId = ref(1);
const imageUrl = ref('');

watch(status, (newStatus) => {
    emit('updateStatus', newStatus);
});

const fetchTotalImages = async () => {
    try {
        const response = await fetch(`${BACKEND_API_URL}/api/image/number`);
        if (response.ok) {
            const data = await response.json();
            totalImages.value = data.number || 0;
            status.value = `加载成功，共${totalImages.value}张图片`;
        } else {
            ElMessage.error('获取图片总数失败');
            totalImages.value = 0;
        }
    } catch (error) {
        console.error('Error fetching total images:', error);
        ElMessage.error('请求图片总数失败');
        totalImages.value = 0;
    }
};

const fetchImage = async (id: number) => {
    if (id < 1 || (totalImages.value > 0 && id > totalImages.value)) {
        ElMessage.warning('图片序号无效');
        return;
    }
    try {
        const response = await fetch(`${BACKEND_API_URL}/api/image?id=${id}`);
        if (response.ok) {
            const imageBlob = await response.blob();
            if (imageUrl.value) {
                URL.revokeObjectURL(imageUrl.value);
            }
            imageUrl.value = URL.createObjectURL(imageBlob);
            currentImageId.value = id;
            jumpId.value = id;
        } else {
            const errorData = await response.json().catch(() => ({ detail: '获取图片失败' }));
            ElMessage.error(errorData.detail || '获取图片失败');
        }
    } catch (error) {
        console.error(`Error fetching image ${id}:`, error);
        ElMessage.error('请求图片失败');
    }
};

const prevImage = () => {
    if (currentImageId.value > 1) {
        fetchImage(currentImageId.value - 1);
    }
};

const nextImage = () => {
    if (currentImageId.value < totalImages.value) {
        fetchImage(currentImageId.value + 1);
    }
};

const jumpToImage = () => {
    fetchImage(jumpId.value);
};

onMounted(async () => {
    await fetchTotalImages();
    if (totalImages.value > 0) {
        await fetchImage(currentImageId.value);
    } else {
        currentImageId.value = 0;
    }
});
</script>

<style scoped>
.image-viewer {
    max-width: 800px;
    margin: 20px auto;
    text-align: center;
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.image-container {
    width: 100%;
    min-height: 400px;
    display: flex;
    justify-content: center;
    align-items: center;
    background-color: #f5f7fa;
    margin-bottom: 20px;
    border: 1px solid #ebeef5;
    border-radius: 4px;
}

.image-display {
    max-width: 100%;
    max-height: 600px;
    object-fit: contain;
}

.image-placeholder {
    color: #909399;
}

.controls {
    display: flex;
    justify-content: center;
    align-items: center;
    margin-bottom: 20px;
}

.image-counter {
    margin: 0 20px;
    font-size: 16px;
    min-width: 80px;
    display: inline-block;
}

.jump-control {
    display: flex;
    justify-content: center;
    align-items: center;
}
</style>
