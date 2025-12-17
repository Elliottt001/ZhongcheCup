# Backend与Frontend连接配置指南

## 📋 目录结构要求

确保项目目录结构如下：

```
PythonProject/
├── Backend/
│   ├── __init__.py          # ✅ 需要（已创建）
│   ├── signal.py            # ✅ 信号分析模块
│   └── WindVibAnalysis/
│       ├── __init__.py      # ✅ 需要（已创建）
│       ├── main_workflow.py
│       ├── config/
│       │   └── camera_params.json
│       ├── data_structs/
│       │   ├── __init__.py
│       │   └── analysis_data.py
│       └── image_analysis/
│           ├── __init__.py
│           ├── tracking_core.py
│           └── displacement_calc.py
└── Frontend/
    ├── app.py
    ├── processor.py
    └── requirements.txt
```

## 🔧 配置步骤

### 步骤1: 检查目录结构

确保 `Backend` 和 `Frontend` 文件夹在同一个父目录下（`PythonProject`）。

### 步骤2: 创建必要的 `__init__.py` 文件

已自动创建以下文件：
- `Backend/__init__.py`
- `Backend/WindVibAnalysis/__init__.py`

如果这些文件不存在，请手动创建空文件。

### 步骤3: 检查Backend依赖

确保Backend模块的所有依赖都已安装：

```bash
# Backend需要的依赖
pip install numpy opencv-python scipy
```

### 步骤4: 验证配置文件

检查 `Backend/WindVibAnalysis/config/camera_params.json` 文件是否存在且格式正确。

### 步骤5: 测试导入

在Python中测试导入：

```python
import sys
import os

# 添加Backend路径
backend_path = r"D:\Pycharm_Data\PythonProject\Backend"
sys.path.insert(0, backend_path)

# 测试导入
try:
    from WindVibAnalysis.main_workflow import run_image_analysis
    print("✅ Backend图像分析模块导入成功！")
except ImportError as e:
    print(f"❌ 导入失败: {e}")

try:
    from signal import DisplacementSeries, analyze_displacement_series
    print("✅ Backend信号分析模块导入成功！")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
```

## 🐛 常见问题排查

### 问题1: "No module named 'WindVibAnalysis'"

**原因**: Backend路径未正确添加到sys.path

**解决方法**:
1. 检查 `Frontend/app.py` 中的 `backend_path` 是否正确
2. 确保Backend和Frontend在同一个父目录下
3. 检查 `Backend/__init__.py` 和 `Backend/WindVibAnalysis/__init__.py` 是否存在

### 问题2: "No module named 'signal'"

**原因**: signal.py文件路径问题或Python内置signal模块冲突

**解决方法**:
1. 确保 `Backend/signal.py` 文件存在
2. 如果存在命名冲突，Frontend代码会自动使用文件路径导入方式

### 问题3: "FileNotFoundError: Configuration file not found"

**原因**: camera_params.json配置文件不存在

**解决方法**:
1. 检查 `Backend/WindVibAnalysis/config/camera_params.json` 是否存在
2. 如果不存在，需要创建配置文件（参考Backend/WindVibAnalysis/README.md）

### 问题4: 导入成功但运行时出错

**可能原因**:
- Backend模块的依赖未安装
- 配置文件格式错误
- 代码版本不匹配

**解决方法**:
1. 安装所有依赖：`pip install numpy opencv-python scipy matplotlib`
2. 检查配置文件格式
3. 查看错误日志获取详细信息

## ✅ 验证连接

启动Frontend应用后，检查界面右上角：

- ✅ **Backend已连接** - 表示连接成功
- ⚠️ **Backend未连接** - 表示连接失败，查看警告信息

如果显示"Backend未连接"，请：
1. 查看页面上的警告信息
2. 检查Backend路径是否正确
3. 验证所有必要的文件是否存在
4. 运行上面的测试导入代码

## 📝 手动配置路径（如果需要）

如果自动路径检测失败，可以在 `Frontend/app.py` 中手动设置Backend路径：

```python
# 手动设置Backend路径
backend_path = r"D:\Pycharm_Data\PythonProject\Backend"  # 修改为你的实际路径
```

## 🔍 调试技巧

1. **查看详细错误信息**: Frontend界面会显示具体的导入错误
2. **使用Python交互式环境测试**: 在Python中直接测试导入
3. **检查文件权限**: 确保所有文件有读取权限
4. **检查Python版本**: 确保Python版本兼容（建议3.7+）

## 📞 获取帮助

如果仍然无法连接，请提供：
1. 完整的错误信息
2. 项目目录结构
3. Python版本信息
4. 已安装的依赖列表

