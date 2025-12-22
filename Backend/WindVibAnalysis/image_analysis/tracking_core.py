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
        
        # 红色在 HSV 空间中的两个范围（红色跨越了 0 度/180 度）
        self.red_lower1 = np.array([0, 100, 100])
        self.red_upper1 = np.array([10, 255, 255])
        self.red_lower2 = np.array([160, 100, 100])
        self.red_upper2 = np.array([180, 255, 255])
        
        # 记录上一帧的位置，用于局部搜索（可选优化）
        self.last_pos = None

    def track_marker_subpix(self, frame: np.ndarray) -> Tuple[float, float]:
        """
        通过颜色分割定位红色条形标记，并返回亚像素质心坐标 (x, y)。
        """
        if frame is None:
            return np.nan, np.nan

        # 1. 转换到 HSV 空间
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # 2. 创建红色掩膜（处理红色跨越 0/180 的情况）
        mask1 = cv2.inRange(hsv, self.red_lower1, self.red_upper1)
        mask2 = cv2.inRange(hsv, self.red_lower2, self.red_upper2)
        mask = cv2.addWeighted(mask1, 1.0, mask2, 1.0, 0.0)

        # 3. 形态学处理：去除噪声并填充空洞
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # 4. 寻找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return np.nan, np.nan

        # 5. 找到面积最大的轮廓（假设它是我们的红色条形标记）
        max_cnt = max(contours, key=cv2.contourArea)
        
        # 过滤掉太小的噪声
        if cv2.contourArea(max_cnt) < 50:
            return np.nan, np.nan

        # 6. 计算质心（利用矩 Moments 获得亚像素精度）
        M = cv2.moments(max_cnt)
        if M["m00"] == 0:
            return np.nan, np.nan
            
        center_x = M["m10"] / M["m00"]
        center_y = M["m01"] / M["m00"]

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
            f"红色标记物检测失败：在 {total_frames} 帧中未检测到任何红色区域。\n"
            f"可能原因：\n"
            f"1. 视频中没有明显的红色标记物\n"
            f"2. 红色颜色范围（HSV）不匹配当前光照条件\n"
            f"3. 标记物太小被过滤掉了（当前阈值：50像素面积）\n"
            f"4. 视频质量问题或光照不足导致颜色失真\n"
            f"建议：检查 tracking_core.py 中的 red_lower/upper 阈值设置。"
        )
    elif detection_rate < 0.1:  # 检测率低于10%
        print(f"警告：AruCo标记物检测率较低 ({detection_rate*100:.1f}%)，仅 {detection_count}/{total_frames} 帧成功检测。")
    
    return np.array(x_list), np.array(y_list)
