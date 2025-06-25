<template>
    <el-header>
        <el-text tag="h1"><el-image src="/Token.svg" class="logo" />DEMaker</el-text>
    </el-header>
    <el-container>
        <el-aside>
            <el-menu>
                <el-menu-item index="1" @click="$router.push('/drone')">
                    <el-icon>
                        <TravelIcon />
                    </el-icon>
                    无人机
                </el-menu-item>
                <el-menu-item index="2" @click="$router.push('/dashboard')">
                    <el-icon>
                        <DashboardIcon />
                    </el-icon>
                    仪表板
                </el-menu-item>
                <el-sub-menu index="3">
                    <template #title>
                        <el-icon>
                            <ViewArrayIcon />
                        </el-icon>
                        视图
                    </template>
                    <el-menu-item index="3-1" @click="$router.push('/views/origin')">
                        <el-icon>
                            <ImageIcon />
                        </el-icon>
                        原始图像
                    </el-menu-item>
                    <el-menu-item index="3-2" @click="$router.push('/views/pointcloud')">
                        <el-icon>
                            <Icon3d />
                        </el-icon>
                        点云
                    </el-menu-item>
                    <el-menu-item index="3-3" @click="$router.push('/views/dem')">
                        <el-icon>
                            <ViewInArIcon />
                        </el-icon>
                        DEM
                    </el-menu-item>
                </el-sub-menu>
            </el-menu>
        </el-aside>
        <el-main>
            <RouterView @update-status="handleStatusUpdate" />
        </el-main>
    </el-container>
    <el-footer>
        <el-text type="info">{{ currentStatus }}</el-text>
    </el-footer>
</template>

<script lang="ts" setup>
import { ref } from 'vue';
import TravelIcon from '../assets/icons/IconTravel.vue';
import DashboardIcon from '../assets/icons/IconDashboard.vue';
import ViewArrayIcon from '../assets/icons/IconViewArray.vue';
import ImageIcon from '../assets/icons/IconImage.vue';
import Icon3d from '../assets/icons/Icon3d.vue';
import ViewInArIcon from '../assets/icons/IconViewInAr.vue';

const currentStatus = ref('未连接');

const handleStatusUpdate = (status: string) => {
    currentStatus.value = status;
};

</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Funnel+Sans:wght@500&display=swap');

.el-header {
    height: 40px;
    background-color: #f5f5f5;
    display: flex;
    align-items: center;
    padding-left: 10px;
    user-select: none;
    border-bottom: 1px solid #eaeaea;
}

.logo {
    width: 32px;
    height: 32px;
}

h1 {
    font-family: "Funnel Sans", sans-serif;
    font-optical-sizing: auto;
    font-weight: 500;
    font-style: normal;
    font-size: 28px;
    display: flex;
    align-items: center;
}

.el-aside {
    width: 200px;
    user-select: none;
    background-color: #f5f5f5;
    border-right: 1px solid #eaeaea;
}

.el-container {
    overflow-y: hidden;
}

.el-main {
    max-height: 100%;
    padding: 20px;
    background-color: #fff;
    overflow-y: auto;
}

.el-footer {
    height: 20px;
    background-color: #f5f5f5;
    display: flex;
    justify-content: flex-end;
    align-items: center;
    padding-right: 20px;
    user-select: none;
    border-top: 1px solid #eaeaea;
}
</style>