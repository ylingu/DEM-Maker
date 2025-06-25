<template>
    <el-card class="process-console">
        <template #header>
            <div class="card-header">
                <span>处理控制台</span>
            </div>
        </template>

        <el-form :model="form" label-width="120px">
            <el-form-item label="数据路径">
                <el-input v-model="form.path" placeholder="选择文件夹或视频文件">
                    <template #prepend>
                        <el-select v-model="pathType" style="width: 100px">
                            <el-option label="文件夹" value="dir"></el-option>
                            <el-option label="文件" value="file"></el-option>
                        </el-select>
                    </template>
                    <template #append>
                        <el-button @click="selectPath">选择</el-button>
                    </template>
                </el-input>
            </el-form-item>

            <el-divider>参数配置</el-divider>

            <el-form-item label="生成颜色数据">
                <el-switch v-model="form.config.colors_data"></el-switch>
            </el-form-item>

            <el-form-item label="插值方法">
                <el-radio-group v-model="form.config.method">
                    <el-radio :value="'idw'">IDW</el-radio>
                    <el-radio :value="'kriging'">Kriging</el-radio>
                </el-radio-group>
            </el-form-item>

            <el-form-item label="网格大小">
                <el-slider v-model="form.config.grid_size" :min="100" :max="2000" show-input></el-slider>
            </el-form-item>

            <el-divider></el-divider>

            <el-form-item>
                <el-button type="primary" @click="startProcessing">开始处理</el-button>
            </el-form-item>
        </el-form>
    </el-card>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue';
import { open } from '@tauri-apps/plugin-dialog';
import { fetch } from '@tauri-apps/plugin-http';
import { ElMessage } from 'element-plus';
import { BACKEND_API_URL } from '../config/api'

const emit = defineEmits(['updateStatus'])
const pathType = ref<'dir' | 'file'>('dir');
const status = ref('');

watch(status, (newStatus) => {
    emit('updateStatus', newStatus);
});

interface DemConfig {
    colors_data: boolean;
    method: 'idw' | 'kriging';
    grid_size: number;
}

interface ProcessRequest {
    path: string;
    config: DemConfig;
}

const form = reactive<ProcessRequest>({
    path: 'Default',
    config: {
        colors_data: true,
        method: 'idw',
        grid_size: 500,
    },
});

const selectPath = async () => {
    try {
        const isDir = pathType.value === 'dir';
        const selected = await open({
            directory: isDir,
            multiple: false,
            filters: isDir ? undefined : [{ name: 'Video', extensions: ['mp4', 'avi', 'mov'] }]
        });
        if (typeof selected === 'string') {
            form.path = selected;
        }
    } catch (error) {
        status.value = '选择路径时出错';
        ElMessage.error('选择路径时出错');
    }
};

const startProcessing = async () => {
    try {
        const response = await fetch(`${BACKEND_API_URL}/api/process`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(form),
        });

        if (response.ok) {
            const result = await response.json();
            ElMessage.success(result.message || '处理任务已开始');
            status.value = '处理任务已开始';
        } else {
            const errorData = await response.json();
            ElMessage.error(errorData.detail || '处理失败');
            status.value = '处理失败';
        }
    } catch (error) {
        status.value = '请求失败';
        ElMessage.error('请求失败');
    }
};
</script>

<style scoped>
.process-console {
    max-width: 600px;
    margin: 20px auto;
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
</style>
