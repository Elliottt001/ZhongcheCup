import json
import numpy as np
import os
import sys
from typing import List, Tuple

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_structs.analysis_data import CalibrationData, TrackingConfig, DisplacementSeries
from image_analysis.tracking_core import generate_pixel_series
from image_analysis.displacement_calc import pixel_to_physical, decompose_vibration

def load_config(config_path: str):
    with open(config_path, 'r') as f:
        data = json.load(f)
    return data

def load_frames_from_npz(npz_path: str) -> Tuple[List[np.ndarray], int]:
    """
    从npz文件加载视频帧序列和帧率（Frontend生成的格式）
    
    :param npz_path: npz文件路径
    :return: (frames, fps) - 帧序列列表和帧率
    """
    if not os.path.exists(npz_path):
        raise FileNotFoundError(f"NPZ文件不存在: {npz_path}")
    
    try:
        # 加载npz文件
        data = np.load(npz_path, allow_pickle=True)
        
        # 检查必要的键是否存在
        if 'frames' not in data:
            raise ValueError("NPZ文件中缺少'frames'键")
        if 'fps' not in data:
            raise ValueError("NPZ文件中缺少'fps'键")
        
        # 提取frames和fps
        frames_array = data['frames']
        fps_value = data['fps']
        
        # 将frames数组转换为列表
        if isinstance(frames_array, np.ndarray):
            # 如果是对象数组，需要逐个提取
            if frames_array.dtype == object:
                frames = [frame for frame in frames_array]
            else:
                # 如果是普通数组，直接转换
                frames = [frames_array[i] for i in range(len(frames_array))]
        else:
            frames = list(frames_array)
        
        # 提取fps值
        if isinstance(fps_value, np.ndarray):
            fps = int(fps_value[0]) if fps_value.size > 0 else int(fps_value)
        else:
            fps = int(fps_value)
        
        print(f"成功加载NPZ文件: {npz_path}")
        print(f"  帧数: {len(frames)}")
        print(f"  帧率: {fps} FPS")
        if len(frames) > 0:
            print(f"  分辨率: {frames[0].shape[1]}x{frames[0].shape[0]}")
        
        return frames, fps
        
    except Exception as e:
        raise ValueError(f"加载NPZ文件失败: {str(e)}")

def run_image_analysis(stabilized_frames: List[np.ndarray], fs: int) -> DisplacementSeries:
    """
    对外接口：接收 B 的稳定帧列表和帧率 fs，执行完整的图像分析流程。
    """
    # 1. 加载配置
    # 假设 config 目录在当前文件同级目录下
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, 'config', 'camera_params.json')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
        
    config_dict = load_config(config_path)
    
    # 解析配置到数据结构
    cam_conf = config_dict['camera']
    fan_conf = config_dict['fan_geometry']
    track_conf = config_dict['tracking']
    
    calib_data = CalibrationData(
        K=np.array(cam_conf['K']),
        D=np.array(cam_conf['D']),
        drone_height_m=fan_conf['drone_height_m'],
        leaf_angle_deg=fan_conf['leaf_angle_deg'],
        pixel_to_mm_ratio=fan_conf['pixel_to_mm_ratio']
    )
    
    tracking_config = TrackingConfig(
        marker_id=track_conf['marker_id'],
        subpix_win_size=track_conf['subpix_win_size']
    )
    
    # 2. 亚像素级特征点跟踪
    print("Starting sub-pixel tracking...")
    dx_pix, dy_pix = generate_pixel_series(stabilized_frames, tracking_config)
    
    # 3. 像素转物理位移
    print("Converting to physical units...")
    dx_mm, dy_mm = pixel_to_physical(dx_pix, dy_pix, calib_data)
    
    # 4. 坐标系分解
    print("Decomposing vibration components...")
    d_flap, d_edge = decompose_vibration(dx_mm, dy_mm, calib_data.leaf_angle_deg)
    
    # 5. 构造时间戳
    n_frames = len(stabilized_frames)
    if fs > 0:
        time_stamps = np.arange(n_frames) / fs
    else:
        time_stamps = np.zeros(n_frames)
        
    # 6. 封装结果
    result = DisplacementSeries(
        time_stamps=time_stamps,
        d_flapwise_mm=d_flap,
        d_edgewise_mm=d_edge,
        fs=float(fs),
        raw_x_pix=dx_pix,
        raw_y_pix=dy_pix
    )
    
    print("Image analysis completed.")
    return result

def run_image_analysis_from_npz(npz_path: str) -> DisplacementSeries:
    """
    从npz文件加载数据并执行图像分析
    
    :param npz_path: npz文件路径（由Frontend生成）
    :return: DisplacementSeries对象，包含切向和轴向的物理位移序列
    """
    # 1. 从npz文件加载帧序列和帧率
    frames, fps = load_frames_from_npz(npz_path)
    
    # 2. 调用现有的分析函数
    return run_image_analysis(frames, fps)


if __name__ == "__main__":
    # 简单的测试桩
    print("This module is intended to be imported by the main pipeline.")
    print("Running a dummy test...")
    
    # 创建一些伪造的帧 (纯黑图像)
    dummy_frames = [np.zeros((1080, 1920, 3), dtype=np.uint8) for _ in range(5)]
    
    try:
        res = run_image_analysis(dummy_frames, fs=30)
        print("Test run successful (output will be NaNs due to empty images).")
    except Exception as e:
        print(f"Test run failed: {e}")
