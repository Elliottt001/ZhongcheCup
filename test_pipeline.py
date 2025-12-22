import os
import sys
import numpy as np
import cv2

# 将 Backend 目录添加到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(current_dir, 'Backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# 导入模块
try:
    from WindVibAnalysis.main_workflow import run_image_analysis
    import signal_analysis
    print("✅ 成功导入 Backend 模块")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)

def test_with_video(video_path, max_frames=300):
    if not os.path.exists(video_path):
        print(f"❌ 视频文件不存在: {video_path}")
        return

    print(f"🎬 正在处理视频: {video_path} (限制最多 {max_frames} 帧)")
    
    # 1. 读取视频帧
    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frames = []
    count = 0
    while count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
        count += 1
    cap.release()
    
    print(f"📊 视频读取完成: {len(frames)} 帧, FPS: {fps}")
    
    if len(frames) == 0:
        print("❌ 未读取到任何帧")
        return

    # 2. 运行图像分析 (WindVibAnalysis)
    print("🔍 正在运行图像跟踪与位移计算...")
    try:
        disp_series = run_image_analysis(frames, fps)
        print("✅ 图像分析完成")
    except Exception as e:
        print(f"❌ 图像分析出错: {e}")
        return

    # 3. 运行信号分析 (signal_analysis)
    # 注意：WindVibAnalysis 输出包含两个方向，我们分别分析
    print("📈 正在运行振动信号分析...")
    
    # 适配数据结构：将 WindVibAnalysis 的输出转换为 signal_analysis 期望的格式
    # 分析切向位移 (Flapwise)
    disp_flap = signal_analysis.DisplacementSeries(
        time_stamps=disp_series.time_stamps,
        d_t_mm=disp_series.d_flapwise_mm,
        fs=int(disp_series.fs),
        fan_id="test_fan_flap"
    )
    
    # 分析轴向位移 (Edgewise)
    disp_edge = signal_analysis.DisplacementSeries(
        time_stamps=disp_series.time_stamps,
        d_t_mm=disp_series.d_edgewise_mm,
        fs=int(disp_series.fs),
        fan_id="test_fan_edge"
    )

    try:
        result_flap = signal_analysis.analyze_displacement_series(disp_flap, low_cut=0.1, high_cut=10.0)
        result_edge = signal_analysis.analyze_displacement_series(disp_edge, low_cut=0.1, high_cut=10.0)
        
        print("\n--- 分析结果 ---")
        print(f"切向 (Flapwise) - 主频: {result_flap.f_dominant_hz:.2f} Hz, 峰峰值: {result_flap.A_pp_mm:.2f} mm")
        print(f"轴向 (Edgewise) - 主频: {result_edge.f_dominant_hz:.2f} Hz, 峰峰值: {result_edge.A_pp_mm:.2f} mm")
        print("---------------")
        print("✅ 所有流程运行成功！")
        
    except Exception as e:
        print(f"❌ 信号分析出错: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_with_video(sys.argv[1])
    else:
        print("💡 请提供视频文件路径进行测试: python test_pipeline.py <video_path>")
        # 也可以在这里放一个默认的测试逻辑
