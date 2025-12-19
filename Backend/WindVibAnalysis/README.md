# WindVibAnalysis - 图像振动分析模块

本模块是“无人机风机振动监测平台”的核心组件之一，负责**图像振动分析**（步骤 2）。
它的主要功能是接收稳定后的视频帧序列，通过亚像素级视觉跟踪算法，提取风机叶片的物理振动位移时间序列。

## 📂 文件结构与职责

*   **`main_workflow.py`**: **[主入口]** 提供对外统一接口。负责加载配置、串联跟踪与计算流程。
*   **`config/camera_params.json`**: **[配置]** 存储相机内参、风机几何参数和跟踪算法参数。
*   **`image_analysis/`**:
    *   `tracking_core.py`: 实现 AruCo 标记物的识别与**亚像素级 (Sub-pixel)** 跟踪。
    *   `displacement_calc.py`: 负责像素坐标到物理坐标 (mm) 的转换，以及振动方向的分解（切向/轴向）。
*   **`data_structs/analysis_data.py`**: 定义标准数据结构 `DisplacementSeries`，确保与信号分析模块的数据交互规范。

---

## 🚀 接口调用办法

本模块设计为供上游（预处理模块）或主程序直接调用。

### 核心接口

#### 方法1: 从npz文件加载（推荐，用于处理Frontend生成的npz文件）

```python
from WindVibAnalysis.main_workflow import run_image_analysis_from_npz

def run_image_analysis_from_npz(npz_path: str) -> DisplacementSeries:
    ...
```

*   **输入**:
    *   `npz_path`: Frontend生成的npz文件路径
*   **输出**:
    *   返回一个 `DisplacementSeries` 对象，包含切向和轴向的物理位移序列。

#### 方法2: 直接传入帧序列

```python
from WindVibAnalysis.main_workflow import run_image_analysis

def run_image_analysis(stabilized_frames: list[np.ndarray], fs: int) -> DisplacementSeries:
    ...
```

*   **输入**:
    *   `stabilized_frames`: 包含图像帧 (`numpy.ndarray`) 的列表。建议图像已完成去抖动处理。
    *   `fs`: 视频的采样率 (FPS)，用于生成时间戳。
*   **输出**:
    *   返回一个 `DisplacementSeries` 对象，包含切向和轴向的物理位移序列。

### 调用示例

#### 示例1: 从Frontend生成的npz文件加载（推荐）

```python
from WindVibAnalysis.main_workflow import run_image_analysis_from_npz

# 直接使用Frontend生成的npz文件
npz_file = "video_frames_20240101_120000.npz"

try:
    result = run_image_analysis_from_npz(npz_file)

    # 获取结果
    print(f"采样率: {result.fs} Hz")
    print(f"数据长度: {len(result.time_stamps)}")
    
    # 获取物理位移 (单位: mm)
    flapwise = result.d_flapwise_mm  # 切向位移
    edgewise = result.d_edgewise_mm  # 轴向位移
    
    print(f"前5帧切向位移: {flapwise[:5]}")

except Exception as e:
    print(f"分析失败: {e}")
```

#### 示例2: 手动加载npz文件

```python
import numpy as np
from WindVibAnalysis.main_workflow import run_image_analysis, load_frames_from_npz

# 从npz文件加载数据
npz_file = "video_frames_20240101_120000.npz"
frames, fps = load_frames_from_npz(npz_file)

# 调用分析模块
try:
    result = run_image_analysis(frames, fps)

    # 获取结果
    print(f"采样率: {result.fs} Hz")
    print(f"数据长度: {len(result.time_stamps)}")
    
    # 获取物理位移 (单位: mm)
    flapwise = result.d_flapwise_mm  # 切向位移
    edgewise = result.d_edgewise_mm  # 轴向位移
    
    print(f"前5帧切向位移: {flapwise[:5]}")

except Exception as e:
    print(f"分析失败: {e}")
```

#### 示例3: 从视频文件读取（传统方式）

```python
import cv2
import numpy as np
from WindVibAnalysis.main_workflow import run_image_analysis

# 1. 准备数据 (读取视频帧)
frames = []
cap = cv2.VideoCapture('video.mp4')
while True:
    ret, frame = cap.read()
    if not ret: break
    frames.append(frame)
fs = int(cap.get(cv2.CAP_PROP_FPS))
cap.release()

# 2. 调用分析模块
try:
    result = run_image_analysis(frames, fs=fs)

    # 3. 获取结果
    print(f"采样率: {result.fs} Hz")
    print(f"数据长度: {len(result.time_stamps)}")
    
    # 获取物理位移 (单位: mm)
    flapwise = result.d_flapwise_mm  # 切向位移
    edgewise = result.d_edgewise_mm  # 轴向位移
    
    print(f"前5帧切向位移: {flapwise[:5]}")

except Exception as e:
    print(f"分析失败: {e}")
```

---

## 📦 处理Frontend生成的npz文件

### 从npz文件直接分析（推荐）

Frontend会生成包含视频帧序列的npz文件，Backend可以直接处理：

```python
from WindVibAnalysis.main_workflow import run_image_analysis_from_npz

# 一步完成：加载和分析
result = run_image_analysis_from_npz("video_frames_20240101_120000.npz")

# 获取结果
print(f"采样率: {result.fs} Hz")
print(f"切向位移: {result.d_flapwise_mm}")
print(f"轴向位移: {result.d_edgewise_mm}")
```

### npz文件格式

Frontend生成的npz文件包含：
- **`frames`**: `numpy.ndarray` (object类型) - 视频帧序列
- **`fps`**: `numpy.ndarray` (int32类型) - 视频帧率

### 手动加载npz文件

如果需要先检查数据再分析：

```python
from WindVibAnalysis.main_workflow import load_frames_from_npz, run_image_analysis

# 加载npz文件
frames, fps = load_frames_from_npz("video_frames_20240101_120000.npz")

# 执行分析
result = run_image_analysis(frames, fps)
```

---

## ⚙️ 配置文件详解

配置文件位于 `WindVibAnalysis/config/camera_params.json`，用于适配不同的拍摄设备和场景。

### 1. `camera` (相机参数)
用于描述拍摄用的相机特性。
*   **`K`**: **相机内参矩阵** (3x3)。
    *   包含焦距 ($f_x, f_y$) 和光心坐标 ($c_x, c_y$)。
    *   格式：`[[fx, 0, cx], [0, fy, cy], [0, 0, 1]]`。
*   **`D`**: **畸变系数**。
    *   用于校正镜头畸变，通常为 5 个参数 `[k1, k2, p1, p2, k3]`。若视频已校正畸变，可设为全 0。

### 2. `fan_geometry` (风机与拍摄几何)
用于将像素运动转换为真实的物理运动。
*   **`drone_height_m`**: 无人机拍摄时距离目标的距离（或高度），单位：米。
*   **`leaf_angle_deg`**: **叶片倾角**，单位：度。
    *   指叶片主轴相对于图像垂直方向的夹角。
    *   **作用**：用于构建旋转矩阵，将水平/垂直的像素位移分解为叶片的**切向 (Flapwise)** 和 **轴向 (Edgewise)** 振动。
*   **`pixel_to_mm_ratio`**: **像素-毫米比例尺** (mm/pixel)。
    *   表示图像中 1 个像素代表实际物理世界中的多少毫米。
    *   *注：该值通常由标定板或已知尺寸的物体计算得出。*

### 3. `tracking` (跟踪算法参数)
控制视觉跟踪算法的行为。
*   **`marker_id`**: **标记物 ID**。
    *   指定要跟踪的 AruCo 标记的 ID 编号（例如 42）。算法会自动在画面中搜索该 ID。
*   **`subpix_win_size`**: **亚像素搜索窗口大小**。
    *   例如 `11` 代表使用 11x11 的窗口进行亚像素角点优化。
    *   窗口越大计算越慢但对噪声越不敏感，通常取 5-11 之间的奇数。
