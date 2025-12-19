# 风机叶片振动监测平台

无人机风机叶片健康监测系统的完整解决方案，包括视频预处理和振动分析。

## 📂 项目结构

```
PythonProject/
├── Frontend/              # 视频预处理前端
│   ├── app.py            # Streamlit Web应用
│   ├── processor.py     # 视频处理核心
│   ├── requirements.txt  # 依赖列表
│   └── README.md         # Frontend使用说明
│
├── Backend/              # 振动分析后端
│   ├── WindVibAnalysis/ # 图像振动分析模块
│   │   ├── main_workflow.py
│   │   ├── config/
│   │   └── README.md
│   ├── signal.py         # 信号分析模块
│   └── 使用npz文件示例.py # 使用示例
│
└── README.md             # 本文件
```

## 🚀 快速开始

### 1. Frontend - 视频预处理

处理视频文件，生成Backend所需的npz格式文件。

```bash
cd Frontend
pip install -r requirements.txt
streamlit run app.py --server.maxUploadSize=2048
```

详细说明请参考：[Frontend/README.md](Frontend/README.md)

### 2. Backend - 振动分析

使用Frontend生成的npz文件进行振动分析。

```python
from Backend.WindVibAnalysis.main_workflow import run_image_analysis_from_npz

# 分析npz文件
result = run_image_analysis_from_npz("video_frames_20240101_120000.npz")

# 获取结果
print(f"切向位移: {result.d_flapwise_mm}")
print(f"轴向位移: {result.d_edgewise_mm}")
```

详细说明请参考：[Backend/WindVibAnalysis/README.md](Backend/WindVibAnalysis/README.md)

## 📋 工作流程

1. **Frontend处理视频**
   - 上传视频文件
   - 提取所有视频帧
   - 生成.npz文件（包含frames和fps）
   - 下载到本地

2. **Backend分析振动**
   - 加载npz文件
   - 执行图像跟踪和位移提取
   - 进行频谱分析
   - 输出振动特征

## 🔧 配置要求

### Frontend依赖
- streamlit
- opencv-python
- numpy
- matplotlib
- scipy

### Backend依赖
- numpy
- opencv-python
- scipy

### Backend配置
需要配置文件：`Backend/WindVibAnalysis/config/camera_params.json`

包含：
- 相机内参（K矩阵、畸变系数D）
- 风机几何参数（高度、叶片倾角、像素比例尺）
- 跟踪算法参数（标记ID、亚像素窗口大小）

## 📖 文档

- [Frontend使用说明](Frontend/README.md)
- [Backend使用说明](Backend/WindVibAnalysis/README.md)
- [Backend使用示例](Backend/使用npz文件示例.py)

## 💡 使用示例

### 完整流程示例

```python
# 1. Frontend已生成npz文件：video_frames_20240101_120000.npz

# 2. Backend分析
from Backend.WindVibAnalysis.main_workflow import run_image_analysis_from_npz
from Backend.signal import DisplacementSeries, analyze_displacement_series

# 图像分析
image_result = run_image_analysis_from_npz("video_frames_20240101_120000.npz")

# 信号分析（切向方向）
signal_disp = DisplacementSeries(
    time_stamps=image_result.time_stamps,
    d_t_mm=image_result.d_flapwise_mm,
    fs=int(image_result.fs),
    fan_id="fan_001"
)

# 频谱分析
analysis_result = analyze_displacement_series(
    disp_series=signal_disp,
    low_cut=0.2,
    high_cut=5.0,
    f_search_min=0.3,
    f_search_max=4.5
)

print(f"主频: {analysis_result.f_dominant_hz} Hz")
print(f"峰峰值: {analysis_result.A_pp_mm} mm")
```

## 📝 注意事项

- Frontend生成的npz文件格式完全兼容Backend
- 确保Backend配置文件正确设置
- 处理大视频文件时注意内存使用
- 视频文件损坏时，系统会自动跳过损坏帧

## 📄 许可证

本项目用于风机叶片健康监测研究。

