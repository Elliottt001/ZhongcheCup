from dataclasses import dataclass, field
import numpy as np
from typing import List, Optional

@dataclass
class CalibrationData:
    """
    存储相机内参和拍摄几何信息
    """
    K: np.ndarray  # 相机内参矩阵 (3x3)
    D: np.ndarray  # 畸变系数 (1x5 or 1xN)
    drone_height_m: float  # 无人机拍摄距离/高度
    leaf_angle_deg: float  # 叶片在画面中的倾斜角度
    pixel_to_mm_ratio: float  # 像素-毫米比例尺 (mm/pixel)

@dataclass
class TrackingConfig:
    """
    跟踪算法的运行时参数
    """
    marker_id: int = 42
    marker_dict: int = 0 # cv2.aruco.DICT_4X4_50 (example mapping)
    subpix_win_size: int = 11
    subpix_zero_zone: int = -1
    subpix_criteria_max_iter: int = 30
    subpix_criteria_eps: float = 0.001

@dataclass
class DisplacementSeries:
    """
    A 的核心输出：物理位移时间序列
    """
    time_stamps: np.ndarray  # 时间戳序列 (N,)
    d_flapwise_mm: np.ndarray  # 切向位移 (N,)
    d_edgewise_mm: np.ndarray  # 轴向位移 (N,)
    fs: float  # 采样率 (Hz)
    
    # 原始像素数据用于调试
    raw_x_pix: Optional[np.ndarray] = None
    raw_y_pix: Optional[np.ndarray] = None
