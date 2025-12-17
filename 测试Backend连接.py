"""
测试Backend与Frontend连接
运行此脚本可以检查Backend模块是否能正确导入
"""

import sys
import os

# 获取Backend路径
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(current_dir, 'Backend')

print("=" * 60)
print("Backend连接测试")
print("=" * 60)
print(f"\n当前目录: {current_dir}")
print(f"Backend路径: {backend_path}")
print(f"Backend路径存在: {os.path.exists(backend_path)}")

# 添加Backend路径到sys.path
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
    print(f"✅ 已添加Backend路径到sys.path")
else:
    print(f"✅ Backend路径已在sys.path中")

print("\n" + "=" * 60)
print("测试1: 导入WindVibAnalysis模块")
print("=" * 60)

try:
    from WindVibAnalysis.main_workflow import run_image_analysis
    print("✅ 成功导入: run_image_analysis")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("\n尝试备用导入方式...")
    try:
        sys.path.insert(0, os.path.join(backend_path, 'WindVibAnalysis'))
        from main_workflow import run_image_analysis
        print("✅ 备用方式导入成功: run_image_analysis")
    except ImportError as e2:
        print(f"❌ 备用方式也失败: {e2}")

try:
    from WindVibAnalysis.data_structs.analysis_data import DisplacementSeries as ImageDisplacementSeries
    print("✅ 成功导入: DisplacementSeries (Image)")
except ImportError as e:
    print(f"❌ 导入失败: {e}")

print("\n" + "=" * 60)
print("测试2: 导入signal模块")
print("=" * 60)

try:
    from signal import DisplacementSeries as SignalDisplacementSeries, analyze_displacement_series
    print("✅ 成功导入: DisplacementSeries (Signal)")
    print("✅ 成功导入: analyze_displacement_series")
except ImportError as e:
    print(f"❌ 直接导入失败: {e}")
    print("\n尝试从文件路径导入...")
    try:
        signal_module_path = os.path.join(backend_path, 'signal.py')
        if os.path.exists(signal_module_path):
            print(f"✅ signal.py文件存在: {signal_module_path}")
            import importlib.util
            spec = importlib.util.spec_from_file_location("signal_analysis", signal_module_path)
            signal_analysis = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(signal_analysis)
            SignalDisplacementSeries = signal_analysis.DisplacementSeries
            analyze_displacement_series = signal_analysis.analyze_displacement_series
            print("✅ 从文件路径导入成功")
        else:
            print(f"❌ signal.py文件不存在: {signal_module_path}")
    except Exception as e2:
        print(f"❌ 从文件路径导入失败: {e2}")

print("\n" + "=" * 60)
print("测试3: 检查必要文件")
print("=" * 60)

files_to_check = [
    ('Backend/__init__.py', os.path.join(backend_path, '__init__.py')),
    ('Backend/WindVibAnalysis/__init__.py', os.path.join(backend_path, 'WindVibAnalysis', '__init__.py')),
    ('Backend/WindVibAnalysis/main_workflow.py', os.path.join(backend_path, 'WindVibAnalysis', 'main_workflow.py')),
    ('Backend/WindVibAnalysis/config/camera_params.json', os.path.join(backend_path, 'WindVibAnalysis', 'config', 'camera_params.json')),
    ('Backend/signal.py', os.path.join(backend_path, 'signal.py')),
]

for file_desc, file_path in files_to_check:
    if os.path.exists(file_path):
        print(f"✅ {file_desc}: 存在")
    else:
        print(f"❌ {file_desc}: 不存在 ({file_path})")

print("\n" + "=" * 60)
print("测试4: 检查依赖")
print("=" * 60)

dependencies = ['numpy', 'cv2', 'scipy', 'matplotlib']
for dep in dependencies:
    try:
        if dep == 'cv2':
            import cv2
        else:
            __import__(dep)
        print(f"✅ {dep}: 已安装")
    except ImportError:
        print(f"❌ {dep}: 未安装")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
print("\n如果所有测试都通过，Backend应该可以正常连接。")
print("如果仍有问题，请查看上面的错误信息。")

