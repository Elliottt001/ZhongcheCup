import cv2
import numpy as np
from typing import Tuple, List, Optional
import sys
import os

# Add project root to path to ensure imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_structs.analysis_data import TrackingConfig

class MarkerTracker:
    def __init__(self, config: TrackingConfig):
        self.config = config
        
        # 检测OpenCV版本并选择合适的AruCo API
        self.opencv_version = cv2.__version__
        self.use_new_api = False
        
        try:
            # 尝试使用新API (OpenCV 4.7+)
            if hasattr(cv2.aruco, 'ArucoDetector'):
                self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
                self.aruco_params = cv2.aruco.DetectorParameters()
                self.aruco_detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
                self.use_new_api = True
            else:
                # 使用旧API (OpenCV 4.6及以下)
                self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
                self.aruco_params = cv2.aruco.DetectorParameters()
                self.use_new_api = False
        except Exception:
            # 如果都失败，尝试直接使用旧API
            self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
            self.aruco_params = cv2.aruco.DetectorParameters()
            self.use_new_api = False
        
        # Subpixel criteria
        self.criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 
                         self.config.subpix_criteria_max_iter, 
                         self.config.subpix_criteria_eps)

    def track_marker_subpix(self, frame: np.ndarray) -> Tuple[float, float]:
        """
        在单个帧中定位并返回标记物的亚像素中心坐标 (x, y)。
        如果未找到标记，返回 (np.nan, np.nan)。
        """
        if frame is None:
            return np.nan, np.nan

        gray = frame
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 1. AruCo 粗略检测 - 兼容新旧API
        try:
            if self.use_new_api:
                # 新API (OpenCV 4.7+)
                corners, ids, rejected = self.aruco_detector.detectMarkers(gray)
            else:
                # 旧API (OpenCV 4.6及以下)
                corners, ids, rejected = cv2.aruco.detectMarkers(
                    gray, self.aruco_dict, parameters=self.aruco_params
                )
        except AttributeError:
            # 如果新API不可用，回退到旧API
            try:
                corners, ids, rejected = cv2.aruco.detectMarkers(
                    gray, self.aruco_dict, parameters=self.aruco_params
                )
            except Exception as e:
                # 如果都失败，返回NaN
                return np.nan, np.nan

        if ids is None or len(ids) == 0:
            return np.nan, np.nan

        # 找到指定 ID 的标记
        target_idx = -1
        for i, marker_id in enumerate(ids):
            if marker_id[0] == self.config.marker_id:
                target_idx = i
                break
        
        if target_idx == -1:
            return np.nan, np.nan

        # 获取四个角点 (1, 4, 2) -> (4, 2)
        marker_corners = corners[target_idx][0]

        # 2. 亚像素优化
        # cornerSubPix 需要 float32 输入
        marker_corners_sub = marker_corners.astype(np.float32)
        
        win_size = (self.config.subpix_win_size, self.config.subpix_win_size)
        zero_zone = (self.config.subpix_zero_zone, self.config.subpix_zero_zone)
        
        cv2.cornerSubPix(gray, marker_corners_sub, win_size, zero_zone, self.criteria)

        # 3. 计算中心点 (取四个角点的重心)
        center_x = np.mean(marker_corners_sub[:, 0])
        center_y = np.mean(marker_corners_sub[:, 1])

        return float(center_x), float(center_y)

def generate_pixel_series(frame_list: List[np.ndarray], config: TrackingConfig) -> Tuple[np.ndarray, np.ndarray]:
    """
    接收预处理后的帧列表，逐帧调用 track_marker_subpix，返回像素位移序列。
    """
    tracker = MarkerTracker(config)
    
    x_list = []
    y_list = []
    
    # 初始位置 (用于计算相对位移，或者直接返回绝对坐标由后续处理)
    # 题目要求：记录标记物中心点相对于初始位置的**原始像素位移序列**
    # 所以我们需要记录第一帧成功检测的位置作为基准
    
    x0, y0 = None, None
    detection_count = 0  # 成功检测的帧数
    total_frames = len(frame_list)
    
    for i, frame in enumerate(frame_list):
        x, y = tracker.track_marker_subpix(frame)
        
        if np.isnan(x):
            # 如果丢失跟踪，可以使用上一帧的位置，或者保持 NaN 后续插值
            # 这里为了简单，如果丢失则填 NaN
            x_list.append(np.nan)
            y_list.append(np.nan)
            continue
        else:
            detection_count += 1
            
        if x0 is None:
            x0, y0 = x, y
            
        # 计算相对位移
        dx = x - x0
        dy = y - y0
        
        x_list.append(dx)
        y_list.append(dy)
    
    # 检查检测率
    detection_rate = detection_count / total_frames if total_frames > 0 else 0.0
    
    if detection_count == 0:
        raise ValueError(
            f"AruCo标记物检测失败：在 {total_frames} 帧中未检测到任何标记物。\n"
            f"可能原因：\n"
            f"1. 视频中没有AruCo标记物（ID={config.marker_id}）\n"
            f"2. 标记物ID配置不正确（当前配置：{config.marker_id}）\n"
            f"3. 标记物字典类型不匹配（当前使用：DICT_4X4_50）\n"
            f"4. 标记物太小、太模糊或被遮挡\n"
            f"5. 视频质量问题或光照不足\n"
            f"建议：检查配置文件中的marker_id设置，确认视频中确实存在对应的AruCo标记物。"
        )
    elif detection_rate < 0.1:  # 检测率低于10%
        print(f"警告：AruCo标记物检测率较低 ({detection_rate*100:.1f}%)，仅 {detection_count}/{total_frames} 帧成功检测。")
    
    return np.array(x_list), np.array(y_list)
