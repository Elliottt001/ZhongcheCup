import json
import numpy as np
import os
import sys
from typing import List

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_structs.analysis_data import CalibrationData, TrackingConfig, DisplacementSeries
from image_analysis.tracking_core import generate_pixel_series
from image_analysis.displacement_calc import pixel_to_physical, decompose_vibration

def load_config(config_path: str):
    with open(config_path, 'r') as f:
        data = json.load(f)
    return data

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
