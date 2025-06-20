# DEM Maker - 无人机数字高程模型生成系统

一个基于 DJI Tello 无人机的数字高程模型（DEM）生成软件，集成了无人机实时控制、视频流传输和地形数据处理功能。

- [DEM Maker - 无人机数字高程模型生成系统](#dem-maker---无人机数字高程模型生成系统)
  - [✨ 主要功能](#-主要功能)
  - [🛠️ 技术架构](#️-技术架构)
  - [🌍 运行环境](#-运行环境)
  - [⚡️ 快速开始](#️-快速开始)
  - [📑 开发指南](#-开发指南)
    - [1. 安装](#1-安装)
    - [2. 启动](#2-启动)
    - [3. 构建](#3-构建)

## ✨ 主要功能

- 🚁 **无人机远程控制** - 支持 DJI Tello 无人机的实时控制，包括起飞、降落、移动、旋转等操作
- 🗺️ **DEM 生成** - 基于无人机捕获的视频流进行图像处理，生成高精度数字高程模型
- 📊 **数据可视化** - 预览处理过程的中间结果与最终DEM成品

## 🛠️ 技术架构

- **前端**: Vue 3 + TypeScript + Tauri - 现代化桌面应用界面
- **后端**: FastAPI + Python - 高性能异步 API 服务

## 🌍 运行环境

推荐环境：

- uv 0.7.8+
- pnpm 10.11.0+
- rust 1.87.0+
- DJI Tello 无人机

## ⚡️ 快速开始

1. **连接无人机**：
   - 确保 DJI Tello 无人机已开机
   - 连接到无人机的 WiFi 网络（TELLO-XXXXXX）
   - 在应用中点击"连接无人机"按钮

2. **操控无人机**：
   - `W/S/A/D` - 前进/后退/左移/右移
   - `Q/E` - 逆时针/顺时针旋转
   - `Space/Ctrl` - 上升/下降
   - `↑/↓` - 起飞/降落

3. **视频流监控**：
   - 连接成功后自动开始视频流传输
   - 实时查看无人机摄像头画面

4. **生成 DEM**：
   - 使用无人机采集目标区域的视频数据
   - 系统自动处理视频流生成数字高程模型

## 📑 开发指南

### 1. 安装

克隆本项目并进入项目根目录：

```bash
git clone https://github.com/ylingu/DEM-Maker.git
cd DEM-Maker
```

### 2. 启动

启动后端 API 服务：

```bash
cd backend
uv run fastapi dev
```

启动前端应用：

```bash
pnpm tauri dev
```

### 3. 构建

后端构建：
```bash
cd backend
uv run nuitka backend-x86_64-pc-windows-msvc.py
```

应用构建：
```bash
pnpm tauri build
```

### 4.COLMAP安装
请先确保你已经在系统中正确安装了 COLMAP（https://colmap.github.io），并添加到系统 PATH 中。