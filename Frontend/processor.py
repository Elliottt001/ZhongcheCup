import cv2
import numpy as np
import os
import zipfile
from datetime import datetime


class VideoProcessor:
    def __init__(self):
        """
        简化的视频处理器 - 直接读取视频帧，不进行畸变校正和稳像处理
        """
        pass

    def process_video(self, video_path, output_folder, time_interval, status_callback, 
                     enable_stabilization=None, create_zip=True, return_frames=False):
        """
        执行视频处理流程：直接读取视频帧
        :param video_path: 视频路径
        :param output_folder: 输出文件夹路径（仅在图像文件模式下使用）
        :param time_interval: 切割时间间隔 (秒)（仅在图像文件模式下使用）
        :param status_callback: 用于更新UI进度的回调函数 (progress, status_text)
        :param enable_stabilization: 已废弃，保留以兼容接口
        :param create_zip: 是否创建zip压缩包（仅在图像文件模式下使用）
        :param return_frames: 如果为True，返回帧列表而不是保存图像
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return "无法打开视频文件", None

        # 获取视频基本信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 准备输出目录（仅在图像文件模式下）
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_subfolder = None
        if not return_frames:
            output_subfolder = os.path.join(output_folder, f"{video_name}_{timestamp}")
            if not os.path.exists(output_subfolder):
                os.makedirs(output_subfolder)

        saved_count = 0
        frames_to_skip = max(1, int(fps * time_interval)) if not return_frames else 1

        # 如果返回帧序列，初始化帧列表
        frames = [] if return_frames else None

        # 直接读取所有帧，不进行任何处理
        for i in range(total_frames):
            ret, frame = cap.read()
            if not ret:
                break

            # 直接使用原始帧，不进行畸变校正和稳像处理
            if return_frames:
                # 收集所有帧用于后续分析
                frames.append(frame.copy())
            elif i % frames_to_skip == 0:
                # 保存图像文件
                current_timestamp = i / fps
                filename = f"frame_{i:06d}_t{current_timestamp:.2f}s.jpg"
                save_path = os.path.join(output_subfolder, filename)
                # 使用高质量JPEG压缩（95质量，平衡文件大小和质量）
                cv2.imwrite(save_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                saved_count += 1

            # 更新UI进度（每10帧更新一次，减少UI更新开销）
            if i % 10 == 0 or i == total_frames - 1:
                progress = (i + 1) / total_frames
                if return_frames:
                    status_text = f"读取中: {i+1}/{total_frames} 帧 | 已提取: {len(frames)} 帧"
                else:
                    status_text = f"处理中: {i+1}/{total_frames} 帧 | 已保存: {saved_count} 张图像"
                status_callback(progress, status_text)

        cap.release()

        if return_frames:
            # 返回帧序列和fps，格式符合Backend要求
            # frames: list[np.ndarray] - 原始视频帧列表
            # fps: float -> int - 视频采样率（转换为整数以符合Backend接口）
            status_callback(1.0, f"处理完成！共提取 {len(frames)} 帧。")
            return frames, int(fps)  # 确保fps是整数类型
        else:
            # 创建ZIP压缩包
            zip_path = None
            if create_zip and saved_count > 0:
                zip_filename = f"{video_name}_{timestamp}.zip"
                zip_path = os.path.join(output_folder, zip_filename)
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(output_subfolder):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, output_subfolder)
                            zipf.write(file_path, arcname)

            status_callback(1.0, f"处理完成！共保存 {saved_count} 张图像。")
            
            result_msg = f"处理完成！共保存 {saved_count} 张图像。\n"
            result_msg += f"图像文件夹: {output_subfolder}"
            if zip_path:
                zip_size = os.path.getsize(zip_path) / (1024 * 1024)
                result_msg += f"\n压缩包: {zip_path} ({zip_size:.2f} MB)"
            
            return result_msg, zip_path
