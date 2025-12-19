"""
使用Frontend生成的npz文件进行Backend分析的示例
"""

import numpy as np
import sys
import os

# 添加Backend路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from WindVibAnalysis.main_workflow import run_image_analysis_from_npz, load_frames_from_npz, run_image_analysis

def example_1_direct_from_npz():
    """
    示例1: 直接从npz文件分析（最简单的方式）
    """
    print("=" * 60)
    print("示例1: 直接从npz文件分析")
    print("=" * 60)
    
    # 替换为你的npz文件路径
    npz_file = "path/to/your/video_frames_20240101_120000.npz"
    
    if not os.path.exists(npz_file):
        print(f"❌ 文件不存在: {npz_file}")
        print("请将npz_file变量替换为实际的npz文件路径")
        return
    
    try:
        # 一步完成：加载和分析
        result = run_image_analysis_from_npz(npz_file)
        
        # 显示结果
        print(f"\n✅ 分析成功！")
        print(f"采样率: {result.fs} Hz")
        print(f"数据长度: {len(result.time_stamps)} 帧")
        print(f"时间范围: {result.time_stamps[0]:.2f} - {result.time_stamps[-1]:.2f} 秒")
        print(f"\n切向位移 (前5帧): {result.d_flapwise_mm[:5]}")
        print(f"轴向位移 (前5帧): {result.d_edgewise_mm[:5]}")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()


def example_2_load_then_analyze():
    """
    示例2: 先加载npz文件，再进行分析（可以检查数据）
    """
    print("\n" + "=" * 60)
    print("示例2: 先加载npz文件，再进行分析")
    print("=" * 60)
    
    # 替换为你的npz文件路径
    npz_file = "path/to/your/video_frames_20240101_120000.npz"
    
    if not os.path.exists(npz_file):
        print(f"❌ 文件不存在: {npz_file}")
        print("请将npz_file变量替换为实际的npz文件路径")
        return
    
    try:
        # 步骤1: 加载npz文件
        print("正在加载npz文件...")
        frames, fps = load_frames_from_npz(npz_file)
        
        print(f"✅ 加载成功！")
        print(f"  帧数: {len(frames)}")
        print(f"  帧率: {fps} FPS")
        if len(frames) > 0:
            print(f"  分辨率: {frames[0].shape[1]}x{frames[0].shape[0]}")
            print(f"  数据类型: {frames[0].dtype}")
        
        # 步骤2: 执行分析
        print("\n正在执行图像分析...")
        result = run_image_analysis(frames, fps)
        
        # 显示结果
        print(f"\n✅ 分析成功！")
        print(f"采样率: {result.fs} Hz")
        print(f"数据长度: {len(result.time_stamps)} 帧")
        print(f"\n切向位移 (前5帧): {result.d_flapwise_mm[:5]}")
        print(f"轴向位移 (前5帧): {result.d_edgewise_mm[:5]}")
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()


def example_3_verify_npz_format():
    """
    示例3: 验证npz文件格式是否正确
    """
    print("\n" + "=" * 60)
    print("示例3: 验证npz文件格式")
    print("=" * 60)
    
    # 替换为你的npz文件路径
    npz_file = "path/to/your/video_frames_20240101_120000.npz"
    
    if not os.path.exists(npz_file):
        print(f"❌ 文件不存在: {npz_file}")
        return
    
    try:
        # 加载npz文件
        data = np.load(npz_file, allow_pickle=True)
        
        print("NPZ文件内容:")
        print(f"  包含的键: {list(data.keys())}")
        
        # 检查frames
        if 'frames' in data:
            frames = data['frames']
            print(f"\n  frames:")
            print(f"    类型: {type(frames)}")
            if isinstance(frames, np.ndarray):
                print(f"    形状: {frames.shape}")
                print(f"    数据类型: {frames.dtype}")
                if frames.dtype == object and len(frames) > 0:
                    print(f"    第一帧形状: {frames[0].shape if hasattr(frames[0], 'shape') else 'N/A'}")
        else:
            print("  ❌ 缺少'frames'键")
        
        # 检查fps
        if 'fps' in data:
            fps = data['fps']
            print(f"\n  fps:")
            print(f"    类型: {type(fps)}")
            if isinstance(fps, np.ndarray):
                print(f"    值: {fps}")
                print(f"    形状: {fps.shape}")
            else:
                print(f"    值: {fps}")
        else:
            print("  ❌ 缺少'fps'键")
        
        print("\n✅ NPZ文件格式验证完成")
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Backend使用npz文件示例")
    print("\n请先修改脚本中的npz_file路径为实际的npz文件路径")
    print("\n选择要运行的示例:")
    print("1. 直接从npz文件分析（推荐）")
    print("2. 先加载再分析（可检查数据）")
    print("3. 验证npz文件格式")
    
    # 取消注释下面的行来运行示例
    # example_1_direct_from_npz()
    # example_2_load_then_analyze()
    # example_3_verify_npz_format()

