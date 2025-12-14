import numpy as np
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_structs.analysis_data import CalibrationData, DisplacementSeries

def pixel_to_physical(dx_pix: np.ndarray, dy_pix: np.ndarray, calib: CalibrationData) -> np.ndarray:
    """
    利用比例尺将像素位移转换为物理位移 (mm)
    返回: (dx_mm, dy_mm)
    """
    # 简单的线性缩放
    # 在更复杂的场景下，可能需要利用深度信息(Z)和内参(K)进行透视变换恢复
    # 这里根据题目描述，使用 pixel_to_mm_ratio
    
    ratio = calib.pixel_to_mm_ratio
    
    dx_mm = dx_pix * ratio
    dy_mm = dy_pix * ratio
    
    return dx_mm, dy_mm

def decompose_vibration(dx_mm: np.ndarray, dy_mm: np.ndarray, angle_deg: float) -> np.ndarray:
    """
    应用旋转矩阵将物理位移投影分解到切向 (Flapwise) 和轴向 (Edgewise)
    返回: (d_flapwise, d_edgewise)
    """
    # 将角度转换为弧度
    theta = np.radians(angle_deg)
    
    # 构造旋转矩阵
    # 假设 angle_deg 是叶片主轴相对于图像垂直方向的夹角
    # 我们需要将图像坐标系 (x, y) 旋转到叶片坐标系 (flap, edge)
    # 这里采用标准的 2D 旋转矩阵
    # [ x' ]   [ cos(theta)   sin(theta) ] [ x ]
    # [ y' ] = [ -sin(theta)  cos(theta) ] [ y ]
    
    c = np.cos(theta)
    s = np.sin(theta)
    
    # 批量旋转
    # d_flapwise 对应 x' (假设切向对应旋转后的 X 轴，或者根据具体定义调整)
    # d_edgewise 对应 y'
    
    d_flapwise = dx_mm * c + dy_mm * s
    d_edgewise = -dx_mm * s + dy_mm * c
    
    return d_flapwise, d_edgewise
