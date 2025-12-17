import cv2
import numpy as np
from datetime import datetime


class VideoProcessor:
    def __init__(self):
        """
        视频处理器 - 直接读取视频帧，输出Backend所需格式
        """
        pass

    def process_video(self, video_path, status_callback):
        """
        执行视频处理流程：直接读取所有视频帧
        :param video_path: 视频路径
        :param status_callback: 用于更新UI进度的回调函数 (progress, status_text)
        :return: (frames, fps) - 帧序列列表和帧率
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError("无法打开视频文件")

        # 获取视频基本信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 初始化帧列表
        frames = []

        # 直接读取所有帧
        for i in range(total_frames):
            ret, frame = cap.read()
            if not ret:
                break

            # 收集所有帧
            frames.append(frame.copy())

            # 更新UI进度（每10帧更新一次，减少UI更新开销）
            if i % 10 == 0 or i == total_frames - 1:
                progress = (i + 1) / total_frames
                status_text = f"读取中: {i+1}/{total_frames} 帧 | 已提取: {len(frames)} 帧"
                status_callback(progress, status_text)

        cap.release()

        # 返回帧序列和fps，格式符合Backend要求
        # frames: list[np.ndarray] - 视频帧列表
        # fps: int - 视频采样率（整数类型）
        status_callback(1.0, f"处理完成！共提取 {len(frames)} 帧。")
        return frames, int(fps)
