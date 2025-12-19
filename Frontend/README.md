# 风机叶片视频预处理系统

这是一个基于Streamlit的风机叶片视频预处理系统，用于处理无人机采集的M4V/MP4视频，提取视频帧序列并保存为Backend所需的npz格式文件。

## 功能特性

- 🎥 视频帧提取（直接读取，无额外处理）
- 💾 输出Backend格式（.npz文件，包含frames和fps）
- ⬇️ 一键下载处理结果
- 🌐 现代化的Web界面
- 📁 支持大文件上传（最大2GB）

## 快速开始

### 1. 环境要求

- Python 3.7+
- pip

### 2. 安装依赖

```bash
cd Frontend
pip install -r requirements.txt
```

**注意**：直接使用系统Python安装即可，**不需要虚拟环境**。

### 3. 启动应用

```bash
# Windows PowerShell
streamlit run app.py --server.maxUploadSize=2048

# 或使用Python模块方式（如果上面命令不工作）
python -m streamlit run app.py --server.maxUploadSize=2048
```

### 4. 访问应用

应用启动后，在浏览器中访问：
- **本地URL**: http://localhost:8501
- 如果端口被占用，会自动使用其他端口

### ⚠️ 关于项目中的 PythonProject 文件夹

如果项目根目录下有 `PythonProject/` 文件夹：
- **这是什么**：这是之前创建的Python虚拟环境目录（包含python.exe和pip.exe）
- **是否需要**：**不需要**，可以直接使用系统Python运行程序
- **可以删除**：如果不需要虚拟环境，可以删除此文件夹，不影响项目运行

## 使用说明

### 基本操作流程

1. **上传视频文件**
   - 支持格式：.m4v, .mp4, .mov
   - 最大支持2GB文件

2. **开始处理**
   - 点击"🚀 开始处理"按钮
   - 系统会自动提取所有视频帧
   - 实时查看处理进度

3. **下载结果**
   - 处理完成后自动生成.npz文件
   - 点击"⬇️ 下载Backend格式文件"按钮
   - 保存到本地

### 输出格式

生成的.npz文件包含：
- **`frames`**: `list[np.ndarray]` - 所有视频帧序列
- **`fps`**: `int` - 视频帧率

**完全兼容Backend接口**：
```python
from Backend.WindVibAnalysis.main_workflow import run_image_analysis_from_npz
result = run_image_analysis_from_npz("your_file.npz")
```

## 在Backend中使用

下载npz文件后，可以在Backend中直接使用：

```python
from WindVibAnalysis.main_workflow import run_image_analysis_from_npz

# 直接分析npz文件
result = run_image_analysis_from_npz("video_frames_20240101_120000.npz")

# 获取结果
print(f"采样率: {result.fs} Hz")
print(f"切向位移: {result.d_flapwise_mm}")
print(f"轴向位移: {result.d_edgewise_mm}")
```

## 技术栈

- **Streamlit**: Web界面框架
- **OpenCV**: 视频处理
- **NumPy**: 数值计算和文件保存

## 故障排除

### 常见问题

1. **无法启动应用**
   - 检查Python版本 (需要3.7+)
   - 确认依赖已正确安装：`pip install -r requirements.txt`

2. **上传文件失败**
   - 检查文件大小是否超过2GB限制
   - 确认文件格式支持 (.m4v, .mp4, .mov)

3. **处理过程中出错**
   - 视频文件可能损坏，尝试使用其他视频文件
   - 检查系统内存是否充足
   - 查看错误信息中的具体提示

4. **端口被占用**
   ```bash
   # 使用其他端口
   streamlit run app.py --server.port 8502 --server.maxUploadSize=2048
   ```

## 注意事项

- 处理大视频文件时需要足够的内存
- 提取的帧会全部保存在内存中，超长视频可能占用大量内存
- 如果视频中有损坏的帧，系统会自动跳过并继续处理

## 许可证

本项目用于风机叶片健康监测研究。
