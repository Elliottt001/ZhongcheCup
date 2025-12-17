import cv2
import numpy as np
from datetime import datetime
import warnings

# 忽略OpenCV的警告
warnings.filterwarnings('ignore')


class VideoProcessor:
    def __init__(self):
        """
        视频处理器 - 直接读取视频帧，输出Backend所需格式
        """
        pass

    def process_video(self, video_path, status_callback):
        """
        执行视频处理流程：直接读取所有视频帧（增强错误处理）
        :param video_path: 视频路径
        :param status_callback: 用于更新UI进度的回调函数 (progress, status_text)
        :return: (frames, fps) - 帧序列列表和帧率
        """
        cap = None
        try:
            # 尝试打开视频文件
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"无法打开视频文件: {video_path}")

            # 获取视频基本信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # 验证基本信息
            if fps <= 0:
                raise ValueError("无法获取视频帧率，视频文件可能损坏")
            if total_frames <= 0:
                raise ValueError("无法获取视频总帧数，视频文件可能损坏")
            
            status_callback(0.0, f"视频信息: {width}x{height}, {fps:.2f} FPS, 总帧数: {total_frames}")

            # 初始化帧列表
            frames = []
            failed_frames = 0
            max_failed_frames = 10  # 允许连续失败的帧数
            consecutive_failures = 0

            # 直接读取所有帧，增强错误处理
            for i in range(total_frames):
                try:
                    # 尝试读取帧
                    ret, frame = cap.read()
                    
                    # 检查读取结果
                    if not ret or frame is None:
                        consecutive_failures += 1
                        failed_frames += 1
                        
                        if consecutive_failures >= max_failed_frames:
                            status_callback(
                                (i + 1) / total_frames,
                                f"警告: 连续 {max_failed_frames} 帧读取失败，停止读取。已提取: {len(frames)} 帧"
                            )
                            break
                        
                        # 尝试跳转到下一帧
                        cap.set(cv2.CAP_PROP_POS_FRAMES, i + 1)
                        continue
                    
                    # 验证帧数据
                    if frame.size == 0:
                        consecutive_failures += 1
                        failed_frames += 1
                        continue
                    
                    # 重置连续失败计数
                    consecutive_failures = 0
                    
                    # 收集有效帧
                    frames.append(frame.copy())

                    # 更新UI进度（每10帧更新一次，减少UI更新开销）
                    if i % 10 == 0 or i == total_frames - 1:
                        progress = (i + 1) / total_frames
                        status_text = f"读取中: {i+1}/{total_frames} 帧 | 已提取: {len(frames)} 帧"
                        if failed_frames > 0:
                            status_text += f" | 跳过: {failed_frames} 帧"
                        status_callback(progress, status_text)
                
                except Exception as e:
                    # 捕获单个帧读取的错误，继续处理
                    failed_frames += 1
                    consecutive_failures += 1
                    
                    if consecutive_failures >= max_failed_frames:
                        status_callback(
                            (i + 1) / total_frames,
                            f"错误: 连续 {max_failed_frames} 帧读取失败 ({str(e)})，停止读取。已提取: {len(frames)} 帧"
                        )
                        break
                    
                    # 尝试跳转到下一帧
                    try:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, i + 1)
                    except:
                        pass
                    continue

            # 检查是否提取到足够的帧
            if len(frames) == 0:
                raise ValueError("未能提取任何有效帧，视频文件可能损坏或格式不支持")
            
            if len(frames) < total_frames * 0.5:
                status_callback(
                    1.0,
                    f"警告: 仅提取了 {len(frames)}/{total_frames} 帧 ({len(frames)/total_frames*100:.1f}%)，可能有部分帧损坏"
                )
            else:
                status_callback(1.0, f"处理完成！共提取 {len(frames)} 帧。")
            
            if failed_frames > 0:
                status_callback(1.0, f"处理完成！共提取 {len(frames)} 帧，跳过了 {failed_frames} 个损坏帧。")

            return frames, int(fps)
            
        except Exception as e:
            # 重新抛出异常，让上层处理
            raise Exception(f"视频处理失败: {str(e)}")
        finally:
            # 确保释放资源
            if cap is not None:
                try:
                    cap.release()
                except:
                    pass
