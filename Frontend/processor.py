import cv2
import numpy as np
import os
import tempfile
import zipfile
from datetime import datetime


class VideoProcessor:
    def __init__(self, camera_matrix, dist_coeffs, enable_stabilization=True):
        """
        初始化处理器
        :param camera_matrix: 相机内参矩阵 (3x3 numpy array)
        :param dist_coeffs: 畸变系数 (numpy array)
        :param enable_stabilization: 是否启用视频稳像
        """
        self.K = camera_matrix
        self.D = dist_coeffs
        self.enable_stabilization = enable_stabilization
        # 预计算畸变校正映射表（性能优化）
        self.mapx = None
        self.mapy = None
        self.stabilization_interval = 5  # 每5帧计算一次稳像变换（性能优化）
        self.feature_scale = 0.5  # 特征检测时缩小图像到50%以提高速度

    def _init_undistort_maps(self, width, height):
        """预计算畸变校正映射表，避免每帧重复计算"""
        if self.mapx is None or self.mapx.shape != (height, width):
            self.mapx, self.mapy = cv2.initUndistortRectifyMap(
                self.K, self.D, None, self.K, (width, height), cv2.CV_32FC1
            )

    def process_video(self, video_path, output_folder, time_interval, status_callback, 
                     enable_stabilization=None, create_zip=True, return_frames=False):
        """
        执行视频处理流程：畸变校正 -> 稳像 -> 切割或返回帧序列
        :param video_path: 视频路径
        :param output_folder: 输出文件夹路径
        :param time_interval: 切割时间间隔 (秒)
        :param status_callback: 用于更新UI进度的回调函数 (progress, status_text)
        :param enable_stabilization: 是否启用稳像，如果None则使用实例变量
        :param create_zip: 是否创建zip压缩包
        :param return_frames: 如果为True，返回稳定帧列表而不是保存图像
        """
        if enable_stabilization is None:
            enable_stabilization = self.enable_stabilization
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return "无法打开视频文件", None

        # 获取视频基本信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # 预计算畸变校正映射表（性能优化关键点1）
        self._init_undistort_maps(width, height)

        # 准备输出目录
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_subfolder = os.path.join(output_folder, f"{video_name}_{timestamp}")
        if not os.path.exists(output_subfolder):
            os.makedirs(output_subfolder)

        # 初始化稳像所需的变量
        prev_gray_small = None  # 使用缩小图像进行特征检测
        saved_count = 0
        frames_to_skip = max(1, int(fps * time_interval))
        current_transform = np.eye(2, 3, dtype=np.float32)  # 当前变换矩阵
        transform_cache = []  # 缓存变换矩阵用于插值

        # 缩小尺寸用于特征检测
        small_width = int(width * self.feature_scale)
        small_height = int(height * self.feature_scale)

        # 如果返回帧序列，初始化帧列表
        stabilized_frames = [] if return_frames else None

        for i in range(total_frames):
            ret, frame = cap.read()
            if not ret:
                break

            # --- 步骤 1: 畸变校正 (使用预计算的映射表，性能提升10倍+) ---
            frame_undistorted = cv2.remap(frame, self.mapx, self.mapy, cv2.INTER_LINEAR)

            # --- 步骤 2: 视频稳像 (优化：降低计算频率) ---
            if enable_stabilization:
                # 每隔N帧重新计算变换矩阵（性能优化关键点2）
                if i % self.stabilization_interval == 0 or i == 0:
                    # 缩小图像用于特征检测和光流计算（性能优化关键点3）
                    frame_small = cv2.resize(frame_undistorted, (small_width, small_height))
                    curr_gray_small = cv2.cvtColor(frame_small, cv2.COLOR_BGR2GRAY)

                    if prev_gray_small is not None:
                        # 使用更少的特征点（性能优化关键点4）
                        p0 = cv2.goodFeaturesToTrack(
                            prev_gray_small, 
                            maxCorners=100,  # 从200减少到100
                            qualityLevel=0.01, 
                            minDistance=30,
                            blockSize=3
                        )

                        if p0 is not None and len(p0) > 10:
                            # 光流法跟踪（使用更快的参数）
                            p1, status, err = cv2.calcOpticalFlowPyrLK(
                                prev_gray_small, curr_gray_small, p0, None,
                                winSize=(15, 15),  # 减小窗口大小
                                maxLevel=2,  # 减少金字塔层数
                                criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
                            )

                            # 选取跟踪成功的点
                            good_prev = p0[status == 1]
                            good_curr = p1[status == 1]

                            if len(good_curr) > 10:
                                # 将坐标放大回原图尺寸
                                good_prev_full = good_prev / self.feature_scale
                                good_curr_full = good_curr / self.feature_scale
                                
                                # 计算变换矩阵
                                m, inliers = cv2.estimateAffine2D(
                                    good_curr_full, good_prev_full,
                                    method=cv2.RANSAC,
                                    ransacReprojThreshold=3.0,
                                    maxIters=100  # 减少迭代次数
                                )

                                if m is not None:
                                    current_transform = m
                                    transform_cache.append(current_transform.copy())
                                    # 只保留最近10个变换矩阵
                                    if len(transform_cache) > 10:
                                        transform_cache.pop(0)

                    # 更新前一帧（仅在重新计算时）
                    prev_gray_small = curr_gray_small

                # 应用变换矩阵
                frame_stabilized = cv2.warpAffine(frame_undistorted, current_transform, (width, height))
            else:
                frame_stabilized = frame_undistorted

            # --- 步骤 3: 等时切割或帧序列收集 ---
            if return_frames:
                # 收集所有稳定帧用于后续分析
                stabilized_frames.append(frame_stabilized.copy())
            elif i % frames_to_skip == 0:
                # 保存图像文件
                current_timestamp = i / fps
                filename = f"frame_{i:06d}_t{current_timestamp:.2f}s.jpg"
                save_path = os.path.join(output_subfolder, filename)
                # 使用高质量JPEG压缩（95质量，平衡文件大小和质量）
                cv2.imwrite(save_path, frame_stabilized, [cv2.IMWRITE_JPEG_QUALITY, 95])
                saved_count += 1

            # 更新UI进度（每5帧更新一次，减少UI更新开销）
            if i % 5 == 0 or i == total_frames - 1:
                progress = (i + 1) / total_frames
                status_text = f"处理中: {i+1}/{total_frames} 帧 | 已保存: {saved_count} 张图像"
                status_callback(progress, status_text)

        cap.release()

        if return_frames:
            # 返回稳定帧序列和fps，格式符合Backend要求
            # stabilized_frames: list[np.ndarray] - 稳定处理后的图像帧列表
            # fps: float -> int - 视频采样率（转换为整数以符合Backend接口）
            status_callback(1.0, f"处理完成！共提取 {len(stabilized_frames)} 帧稳定序列。")
            return stabilized_frames, int(fps)  # 确保fps是整数类型
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