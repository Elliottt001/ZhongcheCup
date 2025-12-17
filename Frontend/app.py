import streamlit as st
import numpy as np
import tempfile
import os
import time
from datetime import datetime
from processor import VideoProcessor
import io

# --- 页面配置 ---
st.set_page_config(
    page_title="WTG Blade Video Preprocessor",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 自定义 CSS 样式 ---
st.markdown("""
<style>
    /* 全局样式 */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: #ffffff;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* 标题样式 */
    h1 {
        color: #ffffff;
        text-align: center;
        font-weight: 700;
        font-size: 2.5em;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        margin-bottom: 1rem;
    }
    h2, h3 {
        color: #ffffff;
    }

    /* 卡片样式 */
    .card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }

    /* 按钮样式 */
    .stButton>button {
        width: 100%;
        background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
        color: white;
        height: 3.5em;
        border-radius: 25px;
        font-weight: bold;
        font-size: 1.1em;
        border: none;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
        background: linear-gradient(45deg, #4ECDC4, #FF6B6B);
    }

    /* 高亮框样式 */
    .highlight-box {
        background: rgba(76, 175, 80, 0.2);
        border-left: 4px solid #4CAF50;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
    }

    /* 信息框样式 */
    .info-box {
        background: rgba(33, 150, 243, 0.2);
        border-left: 4px solid #2196F3;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
    }

    /* 结果卡片样式 */
    .result-card {
        background: rgba(255, 255, 255, 0.15);
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- 重置函数 ---
def reset_processing_state():
    """重置处理状态"""
    if 'processing_complete' in st.session_state:
        del st.session_state.processing_complete
    if 'processed_file_name' in st.session_state:
        del st.session_state.processed_file_name
    if 'frames' in st.session_state:
        del st.session_state.frames
    if 'fps' in st.session_state:
        del st.session_state.fps
    if 'npz_file_path' in st.session_state:
        del st.session_state.npz_file_path
    st.rerun()

# --- 保存帧序列为numpy文件 ---
def save_frames_to_numpy(frames, fps, output_path):
    """将帧序列保存为numpy压缩文件格式（Backend兼容格式）"""
    try:
        # 保存为Backend可以直接使用的格式
        np.savez_compressed(
            output_path,
            frames=np.array(frames, dtype=object),  # 保存为对象数组
            fps=np.array([fps], dtype=np.int32)     # fps保存为整数
        )
        return True, None
    except Exception as e:
        return False, str(e)

# --- 侧边栏：说明信息 ---
with st.sidebar:
    st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
    st.header("📖 使用说明")
    
    st.markdown("""
    ### 🎯 功能说明
    
    本系统用于处理视频文件，提取帧序列并保存为Backend所需的格式。
    
    **处理流程：**
    1. 📤 上传视频文件
    2. 🎬 提取所有视频帧
    3. 💾 保存为.npz格式文件
    4. ⬇️ 下载到本地
    
    **输出格式：**
    - 文件格式：`.npz` (NumPy压缩格式)
    - 包含内容：
      - `frames`: `list[np.ndarray]` - 视频帧序列
      - `fps`: `int` - 视频帧率
    
    **Backend兼容性：**
    ✅ 输出格式完全符合Backend的`run_image_analysis()`接口要求
    """)
    
    st.markdown("---")
    
    with st.expander("⚡ 性能说明"):
        st.markdown("""
        **处理特点：**
        - ✅ 直接读取视频帧，无额外处理
        - ✅ 极速处理，仅受视频读取速度限制
        
        **预计处理时间：**
        - 100MB视频: ~10-20秒
        - 500MB视频: ~30-50秒
        - 1GB视频: ~60-90秒
        """)
    
    st.markdown("---")
    st.markdown("Developed for Wind Turbine Health Monitoring Project")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 主界面 ---
with st.container():
    st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
    
    # 标题区域
    st.title("🚁 风机叶片视频预处理系统")
    st.markdown("### Video Preprocessing for Backend Analysis")
    
    st.markdown("---")
    
    # 功能说明
    st.markdown("""
    <div class="highlight-box">
    <h4>🎯 系统功能</h4>
    <p>本系统将视频文件处理为Backend所需的格式，输出包含视频帧序列和帧率的.npz文件。</p>
    <p><strong>输出格式：</strong></p>
    <ul>
        <li>📦 <strong>文件格式</strong>: .npz (NumPy压缩格式)</li>
        <li>🎬 <strong>帧序列</strong>: list[np.ndarray] - 所有视频帧</li>
        <li>⏱️ <strong>帧率</strong>: int - 视频采样率 (FPS)</li>
    </ul>
    <p><strong>✅ 完全兼容Backend接口：</strong></p>
    <code>run_image_analysis(stabilized_frames: List[np.ndarray], fs: int)</code>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# 视频上传区
with st.container():
    st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
    st.subheader("🎥 视频上传")
    uploaded_file = st.file_uploader(
        "拖入或选择视频文件 (.m4v, .mp4, .mov)", 
        type=["m4v", "mp4", "mov"],
        help="支持M4V、MP4、MOV格式，最大2GB"
    )
    st.markdown('</div>', unsafe_allow_html=True)

# 开始处理逻辑
if uploaded_file is not None:
    with st.container():
        st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
        st.subheader("📊 视频信息")
        
        # 显示视频预览和信息
        col1, col2 = st.columns([2, 1])
        with col1:
            st.video(uploaded_file)
        with col2:
            file_size_mb = uploaded_file.size / 1024 / 1024
            st.metric("文件大小", f"{file_size_mb:.2f} MB")
            st.metric("文件类型", uploaded_file.type or "未知")
            
            # 估算处理时间
            estimated_time = max(10, file_size_mb * 0.2)  # 粗略估算
            st.info(f"⏱ 预计处理时间: {int(estimated_time)}秒")
        
        file_details = {
            "文件名": uploaded_file.name,
            "文件类型": uploaded_file.type or "未知",
            "文件大小": f"{file_size_mb:.2f} MB"
        }
        
        with st.expander("📋 详细信息"):
            st.json(file_details)

        if st.button("🚀 开始处理", type="primary", use_container_width=True):
            # 创建处理区域
            processing_container = st.container()
            with processing_container:
                st.markdown("---")
                st.subheader("⚙️ 处理状态")
                
                # 进度条和状态
                progress_bar = st.progress(0)
                status_display = st.empty()
                log_container = st.empty()
                
                # 处理日志
                logs = []
                
                def add_log(message):
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    logs.append(f"[{timestamp}] {message}")
                    log_text = "\n".join(logs[-10:])
                    log_container.markdown(f"**📝 处理日志**\n\n```\n{log_text}\n```")
                
                def update_progress(progress, status_text):
                    progress_bar.progress(progress)
                    status_display.info(status_text)
                
                # 保存上传的视频到临时文件
                tfile = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1])
                tfile.write(uploaded_file.read())
                video_path = tfile.name
                tfile.close()

                start_time = time.time()
                try:
                    add_log("正在初始化处理引擎...")
                    
                    # 实例化处理器
                    processor = VideoProcessor()
                    add_log("处理器初始化完成")

                    # 执行处理
                    add_log("开始读取视频帧...")
                    frames, fps = processor.process_video(video_path, update_progress)
                    
                    elapsed_time = time.time() - start_time
                    add_log(f"处理完成！耗时: {elapsed_time:.1f}秒")
                    add_log(f"共提取 {len(frames)} 帧，帧率: {fps} FPS")
                    
                    # 存储到session_state
                    st.session_state.frames = frames
                    st.session_state.fps = fps
                    st.session_state.processing_complete = True
                    st.session_state.processed_file_name = uploaded_file.name
                    
                    # 显示结果
                    st.success(f"✅ 处理完成！共提取 {len(frames)} 帧，帧率: {fps} FPS")
                    st.balloons()
                    
                    # 结果展示
                    st.markdown("---")
                    st.subheader("📦 处理结果")
                    
                    result_col1, result_col2, result_col3 = st.columns(3)
                    with result_col1:
                        st.metric("总帧数", f"{len(frames):,}")
                    with result_col2:
                        st.metric("帧率", f"{fps} FPS")
                    with result_col3:
                        st.metric("处理时间", f"{elapsed_time:.1f}秒")
                    
                    # 显示帧信息
                    if len(frames) > 0:
                        st.info(f"📐 分辨率: {frames[0].shape[1]}×{frames[0].shape[0]} 像素 | 数据类型: {frames[0].dtype}")
                    
                    # 生成并下载.npz文件
                    st.markdown("---")
                    st.subheader("💾 下载Backend格式文件")
                    
                    # 生成文件名
                    video_name = os.path.splitext(uploaded_file.name)[0]
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    npz_filename = f"{video_name}_frames_{timestamp}.npz"
                    
                    # 创建临时文件
                    temp_npz = tempfile.NamedTemporaryFile(delete=False, suffix='.npz')
                    temp_npz_path = temp_npz.name
                    temp_npz.close()
                    
                    # 保存为npz文件
                    with st.spinner("正在生成.npz文件..."):
                        success, error = save_frames_to_numpy(frames, fps, temp_npz_path)
                        
                        if success:
                            file_size = os.path.getsize(temp_npz_path) / (1024 * 1024)
                            
                            # 读取文件内容用于下载
                            with open(temp_npz_path, 'rb') as f:
                                npz_data = f.read()
                            
                            st.success(f"✅ .npz文件生成成功！文件大小: {file_size:.2f} MB")
                            
                            # 显示文件信息
                            st.markdown("""
                            <div class="result-card">
                            <h4>📄 文件信息</h4>
                            <ul>
                                <li><strong>文件名</strong>: {}</li>
                                <li><strong>文件大小</strong>: {:.2f} MB</li>
                                <li><strong>格式</strong>: NumPy压缩格式 (.npz)</li>
                                <li><strong>内容</strong>: frames (list[np.ndarray]), fps (int)</li>
                                <li><strong>Backend兼容</strong>: ✅ 完全兼容</li>
                            </ul>
                            </div>
                            """.format(npz_filename, file_size), unsafe_allow_html=True)
                            
                            # 下载按钮
                            st.download_button(
                                label="⬇️ 下载Backend格式文件 (.npz)",
                                data=npz_data,
                                file_name=npz_filename,
                                mime="application/octet-stream",
                                type="primary",
                                use_container_width=True,
                                help="下载包含视频帧序列和帧率的.npz文件，可直接用于Backend分析"
                            )
                            
                            # 使用说明
                            st.markdown("---")
                            st.markdown("### 📖 使用说明")
                            st.markdown("""
                            **在Backend中使用此文件：**
                            
                            ```python
                            import numpy as np
                            from Backend.WindVibAnalysis.main_workflow import run_image_analysis
                            
                            # 加载文件
                            data = np.load('{}', allow_pickle=True)
                            frames = data['frames']
                            fps = int(data['fps'][0])
                            
                            # 转换为列表格式
                            frames_list = [frame for frame in frames]
                            
                            # 调用Backend分析
                            result = run_image_analysis(frames_list, fps)
                            ```
                            """.format(npz_filename))
                            
                            # 存储文件路径（可选，用于后续操作）
                            st.session_state.npz_file_path = temp_npz_path
                        else:
                            st.error(f"❌ 生成.npz文件失败: {error}")
                    
                    # 处理统计
                    st.markdown("---")
                    st.subheader("📈 处理统计")
                    stat_col1, stat_col2, stat_col3 = st.columns(3)
                    with stat_col1:
                        st.metric("处理时间", f"{elapsed_time:.1f}秒")
                    with stat_col2:
                        speed = file_size_mb / elapsed_time if elapsed_time > 0 else 0
                        st.metric("处理速度", f"{speed:.2f} MB/s")
                    with stat_col3:
                        frames_per_sec = len(frames) / elapsed_time if elapsed_time > 0 else 0
                        st.metric("帧提取速度", f"{frames_per_sec:.1f} 帧/秒")
                    
                    # 清空并重新开始按钮
                    st.markdown("---")
                    st.markdown("### 🔄 继续处理")
                    st.info("💡 处理完成！您可以下载文件，或点击下方按钮清空当前状态，继续处理下一个文件。")
                    col_reset1, col_reset2, col_reset3 = st.columns([1, 2, 1])
                    with col_reset2:
                        if st.button("🔄 清空并重新开始", type="secondary", use_container_width=True, 
                                   help="清空当前处理结果，准备处理下一个文件"):
                            # 清理临时文件
                            try:
                                if 'npz_file_path' in st.session_state:
                                    os.unlink(st.session_state.npz_file_path)
                            except:
                                pass
                            reset_processing_state()

                except Exception as e:
                    elapsed_time = time.time() - start_time
                    error_msg = str(e)
                    add_log(f"❌ 处理失败: {error_msg}")
                    
                    # 根据错误类型提供不同的建议
                    error_suggestions = []
                    
                    if "无法打开视频文件" in error_msg:
                        error_suggestions.append("• 检查视频文件是否损坏")
                        error_suggestions.append("• 尝试使用其他视频文件")
                        error_suggestions.append("• 确认视频格式是否支持（.mp4, .m4v, .mov）")
                    elif "无法获取" in error_msg or "损坏" in error_msg:
                        error_suggestions.append("• 视频文件可能已损坏")
                        error_suggestions.append("• 尝试使用视频修复工具修复文件")
                        error_suggestions.append("• 或使用其他视频文件")
                    elif "read" in error_msg.lower() or "exception" in error_msg.lower():
                        error_suggestions.append("• 视频文件可能在处理过程中损坏")
                        error_suggestions.append("• 尝试重新上传视频文件")
                        error_suggestions.append("• 如果视频很大，可能是内存不足，尝试处理较短的视频")
                        error_suggestions.append("• 检查视频编码格式，某些编码可能不兼容")
                    else:
                        error_suggestions.append("• 检查视频文件是否完整")
                        error_suggestions.append("• 尝试使用其他视频文件")
                        error_suggestions.append("• 检查系统内存是否充足")
                    
                    st.error(f"❌ 处理过程中发生错误: {error_msg}")
                    
                    if error_suggestions:
                        st.warning("**💡 建议解决方案：**\n" + "\n".join(error_suggestions))
                    
                    with st.expander("🔍 查看详细错误信息"):
                        st.exception(e)
                    
                    # 错误时也提供重置按钮
                    st.markdown("---")
                    st.info("💡 处理过程中出现错误。您可以检查错误信息，或点击下方按钮清空当前状态，重新开始处理。")
                    col_reset1, col_reset2, col_reset3 = st.columns([1, 2, 1])
                    with col_reset2:
                        if st.button("🔄 清空并重新开始", type="secondary", use_container_width=True, 
                                   help="清空当前处理结果，准备处理下一个文件", key="reset_error"):
                            reset_processing_state()
                finally:
                    try:
                        os.unlink(video_path)  # 删除临时视频文件
                    except (PermissionError, FileNotFoundError):
                        pass
        st.markdown('</div>', unsafe_allow_html=True)
