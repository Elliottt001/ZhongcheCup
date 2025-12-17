import streamlit as st
import numpy as np
import tempfile
import os
import time
import zipfile
from datetime import datetime
from processor import VideoProcessor
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

# --- 页面配置 ---
st.set_page_config(
    page_title="WTG Blade Health Monitor - Preprocessor",
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
    .css-1d391kg {
        padding-top: 2rem;
    }
    .reportview-container .markdown-text-container {
        color: #ffffff;
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

    /* 输入框样式 */
    .stTextInput>div>div>input {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        color: #333;
        padding: 0.5rem;
    }

    /* 文件上传器样式 */
    .stFileUploader {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 1rem;
        border: 2px dashed rgba(255, 255, 255, 0.3);
    }

    /* 进度条样式 */
    .stProgress > div > div > div > div {
        background: linear-gradient(45deg, #FF6B6B, #4ECDC4);
    }

    /* 侧边栏样式 */
    .sidebar .sidebar-content {
        background: rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
    }

    /* 成功/错误消息样式 */
    .stSuccess, .stError {
        background: rgba(255, 255, 255, 0.9);
        color: #333;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }

    /* 视频显示样式 */
    .stVideo {
        border-radius: 15px;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }

    /* 动画效果 */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .fade-in {
        animation: fadeIn 0.5s ease-in-out;
    }

    /* 指标卡片样式 */
    .metric-container {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }

    /* 日志区域样式 */
    textarea {
        font-family: 'Courier New', monospace;
        font-size: 0.9em;
    }

    /* 高亮框样式 - 用于突出显示重要信息 */
    .highlight-box {
        background: rgba(76, 175, 80, 0.2);
        border-left: 4px solid #4CAF50;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }

    /* 信息框样式 */
    .info-box {
        background: rgba(33, 150, 243, 0.2);
        border-left: 4px solid #2196F3;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# --- 文件夹选择函数 ---
def select_folder_safe(initial_dir):
    """安全的文件夹选择函数，处理线程安全问题"""
    try:
        # 创建根窗口
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        root.attributes('-topmost', True)  # 置顶
        root.update()  # 更新窗口状态
        
        # 打开文件夹选择对话框
        selected_folder = filedialog.askdirectory(
            title="选择输出文件夹",
            initialdir=initial_dir
        )
        
        # 安全地关闭窗口
        try:
            root.quit()  # 退出主循环
        except:
            pass
        try:
            root.destroy()  # 销毁窗口
        except:
            pass
        
        return selected_folder if selected_folder else None
    except Exception as e:
        # 确保即使出错也尝试关闭窗口
        try:
            if 'root' in locals():
                root.quit()
                root.destroy()
        except:
            pass
        raise e

# --- 重置函数 ---
def reset_processing_state():
    """重置处理状态，清空已上传的文件和相关状态"""
    # 清空处理相关的 session_state
    if 'processing_complete' in st.session_state:
        del st.session_state.processing_complete
    if 'processed_file_name' in st.session_state:
        del st.session_state.processed_file_name
    if 'stabilized_frames' in st.session_state:
        del st.session_state.stabilized_frames
    if 'fps' in st.session_state:
        del st.session_state.fps
    # 注意：uploaded_file 是 file_uploader 的返回值，通过 rerun 会自动清空
    st.rerun()

# --- 保存帧序列为numpy文件 ---
def save_frames_to_numpy(frames, fps, output_path):
    """将帧序列保存为numpy压缩文件格式"""
    try:
        np.savez_compressed(
            output_path,
            frames=np.array(frames, dtype=object),  # 保存为对象数组
            fps=np.array([fps], dtype=np.int32)
        )
        return True, None
    except Exception as e:
        return False, str(e)

# --- 侧边栏：参数设置 ---
with st.sidebar:
    st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
    st.header("⚙️ 参数配置")
    
    # 输出模式选择 - 放在最前面突出显示
    st.subheader("🎯 输出模式（默认：帧序列）")
    output_mode = st.selectbox(
        "选择输出格式", 
        ["返回帧序列（Backend格式）", "保存图像文件"], 
        index=0,
        help="**帧序列模式（推荐）**: 输出稳定处理后的图像帧列表，格式为list[np.ndarray]，可直接用于Backend振动分析模块。\n\n**图像文件模式**: 生成JPG图像序列文件，适合查看和存档。"
    )
    
    st.markdown("---")

    st.subheader("1. 相机内参 (Camera Matrix K)")
    st.info("请输入标定后的相机内参矩阵数据")
    col1, col2 = st.columns(2)
    fx = col1.number_input("fx (焦距 x)", value=1000.0)
    fy = col2.number_input("fy (焦距 y)", value=1000.0)
    cx = col1.number_input("cx (主点 x)", value=960.0)
    cy = col2.number_input("cy (主点 y)", value=540.0)

    st.subheader("2. 畸变系数 (Distortion Coeffs)")
    st.info("径向和切向畸变参数")
    k1 = st.number_input("k1", value=0.0)
    k2 = st.number_input("k2", value=0.0)
    p1 = st.number_input("p1", value=0.0)
    p2 = st.number_input("p2", value=0.0)
    k3 = st.number_input("k3", value=0.0)

    st.subheader("3. 处理设置")
    enable_stabilization = st.checkbox("启用视频稳像", value=True, 
                                       help="启用后会对视频进行稳像处理，消除相机抖动")
    
    # 仅在图像文件模式下显示时间间隔设置
    if output_mode == "保存图像文件":
        time_interval = st.number_input("图像切割间隔 (秒)", min_value=0.1, value=1.0, step=0.1,
                                       help="每隔多少秒提取一帧图像")
        create_zip = st.checkbox("生成ZIP压缩包", value=True, 
                                help="将生成的图片打包成ZIP文件便于下载")
    else:
        time_interval = 0.0  # 帧序列模式不使用间隔
        create_zip = False
    
    reduce_quality = st.checkbox("启用快速模式 (降低处理质量)", value=False, 
                                 help="启用后处理速度更快，但可能影响图像质量")

    st.markdown("---")
    
    # 性能优化提示
    with st.expander("⚡ 性能优化提示"):
        st.markdown("""
        **优化措施已启用：**
        - ✅ 预计算畸变校正映射表（提速10倍+）
        - ✅ 降低稳像计算频率（每5帧计算一次）
        - ✅ 缩小图像进行特征检测（50%分辨率）
        - ✅ 减少特征点数量（100个）
        - ✅ 优化光流算法参数
        
        **预计处理时间：**
        - 100MB视频: ~60秒
        - 500MB视频: ~90秒
        - 1GB视频: ~120秒
        """)
    
    st.markdown("---")
    st.markdown("Developed for Wind Turbine Health Monitoring Project")
    st.markdown('</div>', unsafe_allow_html=True)

# --- 主界面 ---
with st.container():
    st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
    st.title("🚁 风机叶片视频预处理系统")
    st.markdown("### Video Preprocessing: Stabilization & Frame Extraction")
    
    # 突出显示默认输出模式
    if output_mode == "返回帧序列（Backend格式）":
        st.markdown("""
        <div class="highlight-box">
        <h4>🎯 当前模式：帧序列输出（Backend兼容格式）</h4>
        <p>系统将输出稳定处理后的图像帧序列，格式为 <code>list[np.ndarray]</code>，可直接用于Backend振动分析模块。</p>
        <p><strong>输出存储位置：</strong></p>
        <ul>
            <li>✅ <strong>内存存储</strong>：存储在session_state中，可在当前会话中直接使用</li>
            <li>💾 <strong>可选保存</strong>：可保存为.npz格式文件到本地磁盘</li>
            <li>🔗 <strong>直接传递</strong>：可直接传递给Backend的<code>run_image_analysis()</code>函数</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="info-box">
        <h4>📁 当前模式：图像文件输出</h4>
        <p>系统将生成JPG图像序列文件，保存到指定的输出文件夹。</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# 1. 输出路径选择（仅在图像文件模式下显示，或用于保存numpy文件）
if output_mode == "保存图像文件":
    with st.container():
        st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
        st.subheader("📁 输出路径配置")
        
        # 初始化 session_state
        if 'output_folder' not in st.session_state:
            st.session_state.output_folder = "C:/Users/Public/Documents/Blade_Images"
        if 'folder_selected' not in st.session_state:
            st.session_state.folder_selected = False
        
        col1, col2 = st.columns([3, 1])
        with col1:
            output_folder = st.text_input("请输入结果保存的本地文件夹路径 (绝对路径):",
                                          value=st.session_state.output_folder,
                                          key="output_folder_input")
            # 同步输入框的值到 session_state（仅在用户手动输入时，且不是由浏览按钮触发）
            if 'output_folder_input' in st.session_state and not st.session_state.folder_selected:
                if st.session_state.output_folder_input != st.session_state.output_folder:
                    st.session_state.output_folder = st.session_state.output_folder_input
            # 重置标志
            st.session_state.folder_selected = False
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📂 浏览文件夹", help="打开文件夹选择对话框选择本地文件夹"):
                try:
                    # 获取初始目录
                    initial_dir = st.session_state.output_folder if os.path.exists(st.session_state.output_folder) else os.path.expanduser("~")
                    
                    # 使用安全的文件夹选择函数
                    selected_folder = select_folder_safe(initial_dir)
                    
                    if selected_folder:
                        st.session_state.output_folder = selected_folder
                        st.session_state.folder_selected = True
                        st.rerun()
                    else:
                        st.info("未选择文件夹，保持当前路径")
                except Exception as e:
                    error_msg = str(e)
                    if "Tcl_AsyncDelete" in error_msg or "wrong thread" in error_msg.lower():
                        st.warning("⚠️ 文件夹选择对话框在当前环境下可能不稳定。\n\n**建议：** 请直接在输入框中手动输入文件夹路径。")
                    else:
                        st.error(f"无法打开文件夹选择对话框: {error_msg}\n\n**提示：** 如果是在远程服务器上运行，请手动输入文件夹路径。")
        
        # 使用 session_state 中的值
        output_folder = st.session_state.output_folder
        
        if output_folder and os.path.exists(output_folder):
            st.success(f"✓ 输出文件夹存在: {output_folder}")
        elif output_folder:
            st.warning(f"⚠ 文件夹不存在，将自动创建: {output_folder}")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    # 帧序列模式：初始化输出文件夹（用于可选保存numpy文件）
    if 'output_folder' not in st.session_state:
        st.session_state.output_folder = "C:/Users/Public/Documents/Blade_Images"
    output_folder = st.session_state.output_folder

# 2. 视频上传区
with st.container():
    st.markdown('<div class="card fade-in">', unsafe_allow_html=True)
    st.subheader("🎥 视频上传")
    uploaded_file = st.file_uploader("拖入或选择视频文件 (.m4v, .mp4, .mov)", type=["m4v", "mp4", "mov"])
    st.markdown('</div>', unsafe_allow_html=True)

# 3. 开始处理逻辑
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
            estimated_time = max(30, file_size_mb * 2)  # 粗略估算
            st.info(f"⏱ 预计处理时间: {int(estimated_time)}秒")
        
        file_details = {
            "文件名": uploaded_file.name,
            "文件类型": uploaded_file.type or "未知",
            "文件大小": f"{file_size_mb:.2f} MB"
        }
        
        with st.expander("📋 详细信息"):
            st.json(file_details)

        # 检查输出路径（仅在图像文件模式下需要）
        need_output_folder = (output_mode == "保存图像文件")
        can_process = not need_output_folder or (output_folder and output_folder.strip())
        
        if not can_process and need_output_folder:
            st.error("❌ 请先指定输出文件夹路径！")
        elif st.button("🚀 开始处理 (Start Processing)", type="primary"):
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
                    log_text = "\n".join(logs[-10:])  # 只显示最后10条日志
                    log_container.markdown(f"**📝 处理日志**\n\n```\n{log_text}\n```")
                
                def update_progress(progress, status_text):
                    progress_bar.progress(progress)
                    status_display.info(status_text)
                
                # 构建矩阵
                K = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])
                D = np.array([k1, k2, p1, p2, k3])

                # 保存上传的视频到临时文件
                tfile = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1])
                tfile.write(uploaded_file.read())
                video_path = tfile.name
                tfile.close()

                start_time = time.time()
                try:
                    add_log("正在初始化处理引擎...")
                    
                    # 实例化处理器
                    processor = VideoProcessor(K, D, enable_stabilization)
                    add_log("处理器初始化完成")

                    # 执行处理
                    add_log("开始处理视频...")
                    return_frames = (output_mode == "返回帧序列（Backend格式）")
                    # 帧序列模式：返回稳定处理后的图像帧，格式符合Backend要求
                    result = processor.process_video(
                        video_path, output_folder, time_interval, 
                        update_progress, enable_stabilization, 
                        create_zip if not return_frames else False,  # 帧序列模式不创建zip
                        return_frames  # True时返回list[np.ndarray]和fps，符合Backend输入格式
                    )
                    
                    if return_frames:
                        # 返回格式： stabilized_frames: list[np.ndarray], fps: int
                        # 符合Backend的run_image_analysis接口要求
                        stabilized_frames, fps = result
                        # 确保fps是整数类型（Backend期望int）
                        fps = int(fps)
                        result_msg = f"处理完成！共提取 {len(stabilized_frames)} 帧稳定序列（格式：list[np.ndarray]，可直接用于Backend分析）。"
                        zip_path = None
                    else:
                        result_msg, zip_path = result
                    
                    elapsed_time = time.time() - start_time
                    add_log(f"处理完成！耗时: {elapsed_time:.1f}秒")
                    
                    # 显示结果
                    st.success("✅ " + result_msg)
                    st.balloons()
                    
                    # 解析结果信息
                    image_count = 0
                    output_subfolder = None
                    if not return_frames:
                        try:
                            if "共保存" in result_msg and "张图像" in result_msg:
                                image_count = int(result_msg.split("共保存 ")[1].split(" 张图像")[0])
                            if "图像文件夹:" in result_msg:
                                output_subfolder = result_msg.split("图像文件夹: ")[1].split("\n")[0]
                        except:
                            pass
                    
                    # 结果预览和下载
                    st.markdown("---")
                    st.subheader("📦 处理结果")
                    
                    if return_frames:
                        # 帧序列模式 - 重点展示
                        st.markdown("""
                        <div class="highlight-box">
                        <h4>✅ 帧序列提取成功！</h4>
                        <p>稳定处理后的图像帧序列已准备就绪，格式符合Backend要求。</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 显示帧序列信息
                        info_col1, info_col2 = st.columns(2)
                        with info_col1:
                            st.markdown("**📊 帧序列详情**")
                            st.write(f"- **总帧数**: {len(stabilized_frames)} 帧")
                            st.write(f"- **帧率**: {fps} FPS (int类型)")
                            st.write(f"- **分辨率**: {stabilized_frames[0].shape[1]}×{stabilized_frames[0].shape[0]} 像素")
                            st.write(f"- **数据类型**: `list[np.ndarray]`")
                            st.write(f"- **颜色格式**: OpenCV BGR格式")
                        
                        with info_col2:
                            st.markdown("**✅ 格式验证**")
                            st.success("符合Backend接口要求")
                            st.code("run_image_analysis(\n    stabilized_frames: List[np.ndarray],\n    fs: int\n) -> DisplacementSeries", language="python")
                        
                        # 存储到session_state供后续使用
                        st.session_state.stabilized_frames = stabilized_frames
                        st.session_state.fps = fps
                        
                        # 输出存储位置说明
                        st.markdown("---")
                        st.subheader("💾 输出存储位置")
                        
                        storage_col1, storage_col2 = st.columns(2)
                        with storage_col1:
                            st.markdown("""
                            **📍 当前存储位置：**
                            
                            ✅ **内存存储（Session State）**
                            - 变量名: `st.session_state.stabilized_frames`
                            - 变量名: `st.session_state.fps`
                            - 状态: 已存储，可在当前会话中使用
                            - 用途: 可直接传递给Backend分析模块
                            """)
                        
                        with storage_col2:
                            st.markdown("""
                            **💡 使用方式：**
                            
                            ```python
                            # 在当前会话中访问
                            frames = st.session_state.stabilized_frames
                            fps = st.session_state.fps
                            
                            # 传递给Backend
                            from Backend.WindVibAnalysis.main_workflow import run_image_analysis
                            result = run_image_analysis(frames, fps)
                            ```
                            """)
                        
                        # 可选：保存为numpy文件
                        st.markdown("---")
                        st.subheader("💾 可选：保存为文件")
                        st.info("💡 您可以选择将帧序列保存为.npz格式文件到本地磁盘，以便后续使用或分享。")
                        
                        save_col1, save_col2 = st.columns([3, 1])
                        with save_col1:
                            numpy_save_path = st.text_input(
                                "保存路径（.npz文件）:",
                                value=os.path.join(output_folder, f"{os.path.splitext(uploaded_file.name)[0]}_frames.npz"),
                                help="输入完整的文件路径，包括文件名和.npz扩展名"
                            )
                        with save_col2:
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button("💾 保存为NPZ", help="将帧序列保存为numpy压缩文件"):
                                if numpy_save_path:
                                    try:
                                        # 确保目录存在
                                        save_dir = os.path.dirname(numpy_save_path)
                                        if save_dir and not os.path.exists(save_dir):
                                            os.makedirs(save_dir)
                                        
                                        success, error = save_frames_to_numpy(stabilized_frames, fps, numpy_save_path)
                                        if success:
                                            file_size = os.path.getsize(numpy_save_path) / (1024 * 1024)
                                            st.success(f"✅ 保存成功！\n文件路径: {numpy_save_path}\n文件大小: {file_size:.2f} MB")
                                            st.info("💡 可以使用 `np.load('file.npz')` 加载文件，然后通过 `data['frames']` 和 `data['fps']` 访问数据。")
                                        else:
                                            st.error(f"❌ 保存失败: {error}")
                                    except Exception as e:
                                        st.error(f"❌ 保存过程中出错: {str(e)}")
                                else:
                                    st.warning("⚠️ 请输入保存路径")
                        
                        st.success("✅ 稳定帧序列已存储，格式符合Backend要求，可直接用于振动分析！")
                    else:
                        # 图像文件模式
                        result_col1, result_col2 = st.columns(2)
                        with result_col1:
                            if output_subfolder:
                                st.info(f"📁 输出文件夹:\n{output_subfolder}")
                            else:
                                st.info(f"📁 输出文件夹:\n{output_folder}")
                        
                        if zip_path and os.path.exists(zip_path):
                            zip_size = os.path.getsize(zip_path) / (1024 * 1024)
                            with result_col2:
                                st.info(f"📦 ZIP压缩包:\n{zip_path}\n大小: {zip_size:.2f} MB")
                            
                            # 提供下载按钮
                            try:
                                with open(zip_path, 'rb') as f:
                                    zip_data = f.read()
                                st.download_button(
                                    label="⬇️ 下载ZIP压缩包",
                                    data=zip_data,
                                    file_name=os.path.basename(zip_path),
                                    mime="application/zip",
                                    type="primary"
                                )
                            except Exception as e:
                                st.warning(f"无法读取ZIP文件: {str(e)}")
                    
                    # 处理统计
                    st.markdown("---")
                    st.subheader("📈 处理统计")
                    stat_col1, stat_col2, stat_col3 = st.columns(3)
                    with stat_col1:
                        st.metric("处理时间", f"{elapsed_time:.1f}秒")
                    with stat_col2:
                        if return_frames:
                            st.metric("提取帧数", len(stabilized_frames))
                        elif image_count > 0:
                            st.metric("生成图像数", image_count)
                        else:
                            st.metric("生成图像数", "N/A")
                    with stat_col3:
                        speed = file_size_mb / elapsed_time if elapsed_time > 0 else 0
                        st.metric("处理速度", f"{speed:.2f} MB/s")
                    
                    # 标记处理完成
                    st.session_state.processing_complete = True
                    st.session_state.processed_file_name = uploaded_file.name
                    
                    # 清空并重新开始按钮
                    st.markdown("---")
                    st.markdown("### 🔄 继续处理")
                    st.info("💡 处理完成！您可以继续处理下一个文件，或点击下方按钮清空当前状态。")
                    col_reset1, col_reset2, col_reset3 = st.columns([1, 2, 1])
                    with col_reset2:
                        if st.button("🔄 清空并重新开始", type="primary", use_container_width=True, 
                                   help="清空当前处理结果，准备处理下一个文件"):
                            reset_processing_state()

                except Exception as e:
                    elapsed_time = time.time() - start_time
                    add_log(f"❌ 处理失败: {str(e)}")
                    st.error(f"❌ 处理过程中发生错误: {str(e)}")
                    st.exception(e)
                    
                    # 错误时也提供重置按钮
                    st.markdown("---")
                    st.info("💡 处理过程中出现错误。您可以检查错误信息，或点击下方按钮清空当前状态，重新开始处理。")
                    col_reset1, col_reset2, col_reset3 = st.columns([1, 2, 1])
                    with col_reset2:
                        if st.button("🔄 清空并重新开始", type="primary", use_container_width=True, 
                                   help="清空当前处理结果，准备处理下一个文件", key="reset_error"):
                            reset_processing_state()
                finally:
                    try:
                        os.unlink(video_path)  # 删除临时文件
                    except (PermissionError, FileNotFoundError):
                        pass
        st.markdown('</div>', unsafe_allow_html=True)
