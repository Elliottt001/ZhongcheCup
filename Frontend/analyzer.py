"""
风机叶片振动分析可视化界面
集成Frontend和Backend，提供完整的分析流程和可视化展示
"""

import streamlit as st
import numpy as np
import tempfile
import os
import sys
import time
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
from matplotlib import font_manager
import io

# 添加Backend路径
backend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# 尝试导入Backend模块
BACKEND_AVAILABLE = False
SIGNAL_AVAILABLE = False
SignalDisplacementSeries = None
analyze_displacement_series = None

try:
    from WindVibAnalysis.main_workflow import run_image_analysis_from_npz
    BACKEND_AVAILABLE = True
except ImportError as e:
    st.warning(f"⚠️ Backend图像分析模块导入失败: {e}")

# 使用importlib避免与Python内置signal模块冲突
# 方法：使用runpy模块或直接执行文件
try:
    # 确保backend_path在sys.path中
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    signal_module_path = os.path.join(backend_path, 'signal.py')
    
    if not os.path.exists(signal_module_path):
        st.warning(f"⚠️ Backend信号分析模块文件不存在: {signal_module_path}")
    else:
        # 使用绝对路径
        signal_module_path = os.path.abspath(signal_module_path)
        
        try:
            # 方法：使用importlib.machinery直接加载
            from importlib import machinery
            
            # 创建SourceFileLoader
            loader = machinery.SourceFileLoader('backend_signal', signal_module_path)
            
            # 创建模块
            backend_signal = loader.load_module('backend_signal')
            
            # 检查模块是否有需要的类/函数
            if hasattr(backend_signal, 'DisplacementSeries') and hasattr(backend_signal, 'analyze_displacement_series'):
                SignalDisplacementSeries = backend_signal.DisplacementSeries
                analyze_displacement_series = backend_signal.analyze_displacement_series
                SIGNAL_AVAILABLE = True
            else:
                missing = []
                if not hasattr(backend_signal, 'DisplacementSeries'):
                    missing.append('DisplacementSeries')
                if not hasattr(backend_signal, 'analyze_displacement_series'):
                    missing.append('analyze_displacement_series')
                st.warning(f"⚠️ Backend信号分析模块缺少: {', '.join(missing)}")
                    
        except Exception as load_error:
            # 如果SourceFileLoader失败，尝试使用exec
            try:
                with open(signal_module_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # 创建命名空间
                namespace = {'__name__': 'backend_signal', '__file__': signal_module_path}
                namespace['__path__'] = [os.path.dirname(signal_module_path)]
                
                # 执行代码
                exec(code, namespace)
                
                # 检查是否有需要的类/函数
                if 'DisplacementSeries' in namespace and 'analyze_displacement_series' in namespace:
                    SignalDisplacementSeries = namespace['DisplacementSeries']
                    analyze_displacement_series = namespace['analyze_displacement_series']
                    SIGNAL_AVAILABLE = True
                else:
                    missing = []
                    if 'DisplacementSeries' not in namespace:
                        missing.append('DisplacementSeries')
                    if 'analyze_displacement_series' not in namespace:
                        missing.append('analyze_displacement_series')
                    st.warning(f"⚠️ Backend信号分析模块缺少: {', '.join(missing)}")
            except Exception as exec_error:
                import traceback
                error_details = traceback.format_exc()
                st.warning(f"⚠️ 加载模块时出错: {exec_error}")
                with st.expander("查看详细错误信息"):
                    st.code(error_details)
                
except Exception as e:
    import traceback
    error_details = traceback.format_exc()
    st.warning(f"⚠️ Backend信号分析模块导入失败: {e}")
    with st.expander("查看详细错误信息"):
        st.code(error_details)

# --- 页面配置 ---
st.set_page_config(
    page_title="WTG Blade Vibration Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 自定义 CSS 样式 ---
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    h1, h2, h3 {
        color: #ffffff;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .status-success {
        color: #4ade80;
        font-weight: bold;
    }
    .status-error {
        color: #f87171;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- 主标题 ---
st.title("📊 风机叶片振动分析系统")
st.markdown("---")

# --- 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ 分析配置")
    
    # Backend状态检查
    if BACKEND_AVAILABLE and SIGNAL_AVAILABLE:
        st.success("✅ Backend已连接")
    else:
        st.error("❌ Backend未完全连接")
        if not BACKEND_AVAILABLE:
            st.error("图像分析模块不可用")
        if not SIGNAL_AVAILABLE:
            st.error("信号分析模块不可用")
    
    st.markdown("---")
    
    # 信号分析参数
    st.subheader("📈 信号分析参数")
    
    low_cut = st.number_input(
        "低截止频率 (Hz)",
        min_value=0.0,
        max_value=10.0,
        value=0.2,
        step=0.1,
        help="带通滤波器的低截止频率"
    )
    
    high_cut = st.number_input(
        "高截止频率 (Hz)",
        min_value=0.1,
        max_value=20.0,
        value=5.0,
        step=0.1,
        help="带通滤波器的高截止频率"
    )
    
    f_search_min = st.number_input(
        "主频搜索最小值 (Hz)",
        min_value=0.0,
        max_value=10.0,
        value=0.3,
        step=0.1,
        help="主频搜索范围的最小值"
    )
    
    f_search_max = st.number_input(
        "主频搜索最大值 (Hz)",
        min_value=0.1,
        max_value=20.0,
        value=4.5,
        step=0.1,
        help="主频搜索范围的最大值"
    )
    
    # 异常阈值
    st.markdown("---")
    st.subheader("⚠️ 异常检测阈值")
    
    enable_threshold = st.checkbox("启用异常检测", value=False)
    
    if enable_threshold:
        A_pp_limit = st.number_input(
            "峰峰值阈值 (mm)",
            min_value=0.0,
            value=10.0,
            step=0.1,
            help="超过此值将标记为异常"
        )
        
        A_rms_limit = st.number_input(
            "RMS阈值 (mm)",
            min_value=0.0,
            value=5.0,
            step=0.1,
            help="超过此值将标记为异常"
        )
    else:
        A_pp_limit = None
        A_rms_limit = None

# --- 主界面 ---

# 文件上传区域
st.header("📁 上传NPZ文件")
st.markdown("请上传Frontend生成的npz文件（包含frames和fps）")

uploaded_file = st.file_uploader(
    "选择NPZ文件",
    type=['npz'],
    help="上传Frontend生成的npz格式文件"
)

if uploaded_file is not None:
    # 显示文件信息
    file_size_mb = uploaded_file.size / (1024 * 1024)
    st.info(f"📄 文件: {uploaded_file.name} | 大小: {file_size_mb:.2f} MB")
    
    # 保存上传的文件
    if st.button("🚀 开始分析", type="primary", use_container_width=True):
        if not BACKEND_AVAILABLE or not SIGNAL_AVAILABLE:
            st.error("❌ Backend未完全连接，无法进行分析。请检查Backend配置。")
        else:
            # 创建进度容器
            progress_container = st.container()
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
                log_container = st.empty()
                
                logs = []
                
                def add_log(message):
                    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
                    log_container.text("\n".join(logs[-10:]))  # 只显示最后10条
                
                def update_progress(progress, message):
                    progress_bar.progress(progress)
                    status_text.text(message)
                
                try:
                    # 步骤1: 保存上传的文件
                    add_log("正在保存上传的文件...")
                    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.npz')
                    tfile.write(uploaded_file.read())
                    npz_path = tfile.name
                    tfile.close()
                    add_log(f"文件已保存: {npz_path}")
                    
                    # 步骤2: 图像分析
                    add_log("开始图像分析...")
                    update_progress(0.2, "图像分析中...")
                    start_time = time.time()
                    
                    image_result = run_image_analysis_from_npz(npz_path)
                    
                    image_time = time.time() - start_time
                    add_log(f"✅ 图像分析完成！耗时: {image_time:.1f}秒")
                    add_log(f"   采样率: {image_result.fs} Hz")
                    add_log(f"   数据长度: {len(image_result.time_stamps)} 帧")
                    
                    # 步骤3: 信号分析（切向方向）
                    add_log("开始信号分析（切向方向）...")
                    update_progress(0.6, "信号分析中...")
                    
                    signal_disp_flap = SignalDisplacementSeries(
                        time_stamps=image_result.time_stamps,
                        d_t_mm=image_result.d_flapwise_mm,
                        fs=int(image_result.fs),
                        fan_id="fan_001"
                    )
                    
                    signal_result_flap = analyze_displacement_series(
                        disp_series=signal_disp_flap,
                        low_cut=low_cut,
                        high_cut=high_cut,
                        f_search_min=f_search_min,
                        f_search_max=f_search_max,
                        A_pp_limit=A_pp_limit,
                        A_rms_limit=A_rms_limit
                    )
                    
                    # 信号分析（轴向方向）
                    add_log("开始信号分析（轴向方向）...")
                    
                    signal_disp_edge = SignalDisplacementSeries(
                        time_stamps=image_result.time_stamps,
                        d_t_mm=image_result.d_edgewise_mm,
                        fs=int(image_result.fs),
                        fan_id="fan_001"
                    )
                    
                    signal_result_edge = analyze_displacement_series(
                        disp_series=signal_disp_edge,
                        low_cut=low_cut,
                        high_cut=high_cut,
                        f_search_min=f_search_min,
                        f_search_max=f_search_max,
                        A_pp_limit=A_pp_limit,
                        A_rms_limit=A_rms_limit
                    )
                    
                    signal_time = time.time() - start_time - image_time
                    add_log(f"✅ 信号分析完成！耗时: {signal_time:.1f}秒")
                    
                    # 保存结果到session state
                    st.session_state.image_result = image_result
                    st.session_state.signal_result_flap = signal_result_flap
                    st.session_state.signal_result_edge = signal_result_edge
                    st.session_state.analysis_complete = True
                    
                    update_progress(1.0, "分析完成！")
                    add_log("🎉 所有分析完成！")
                    
                    total_time = time.time() - start_time
                    add_log(f"总耗时: {total_time:.1f}秒")
                    
                    st.success("✅ 分析完成！")
                    st.balloons()
                    
                except Exception as e:
                    add_log(f"❌ 分析失败: {str(e)}")
                    st.error(f"❌ 分析过程中发生错误: {str(e)}")
                    with st.expander("🔍 查看详细错误信息"):
                        st.exception(e)
                finally:
                    # 清理临时文件
                    try:
                        os.unlink(npz_path)
                    except (PermissionError, FileNotFoundError):
                        pass

# --- 结果显示 ---
if st.session_state.get('analysis_complete', False):
    st.markdown("---")
    st.header("📊 分析结果")
    
    image_result = st.session_state.image_result
    signal_result_flap = st.session_state.signal_result_flap
    signal_result_edge = st.session_state.signal_result_edge
    
    # 关键指标展示
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "切向主频",
            f"{signal_result_flap.f_dominant_hz:.3f} Hz",
            delta=None
        )
    
    with col2:
        st.metric(
            "切向峰峰值",
            f"{signal_result_flap.A_pp_mm:.3f} mm",
            delta=None
        )
    
    with col3:
        st.metric(
            "轴向主频",
            f"{signal_result_edge.f_dominant_hz:.3f} Hz",
            delta=None
        )
    
    with col4:
        st.metric(
            "轴向峰峰值",
            f"{signal_result_edge.A_pp_mm:.3f} mm",
            delta=None
        )
    
    # 异常状态
    if signal_result_flap.is_abnormal or signal_result_edge.is_abnormal:
        st.warning("⚠️ 检测到异常振动！")
    
    # 时域图
    st.subheader("📈 时域分析")
    
    fig_time, axes = plt.subplots(2, 1, figsize=(12, 8))
    fig_time.patch.set_facecolor('white')
    
    # 切向位移
    axes[0].plot(image_result.time_stamps, image_result.d_flapwise_mm, 'b-', linewidth=1.5, label='切向位移')
    axes[0].set_xlabel('时间 (s)', fontsize=12)
    axes[0].set_ylabel('位移 (mm)', fontsize=12)
    axes[0].set_title('切向位移时间序列', fontsize=14, fontweight='bold')
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()
    
    # 轴向位移
    axes[1].plot(image_result.time_stamps, image_result.d_edgewise_mm, 'r-', linewidth=1.5, label='轴向位移')
    axes[1].set_xlabel('时间 (s)', fontsize=12)
    axes[1].set_ylabel('位移 (mm)', fontsize=12)
    axes[1].set_title('轴向位移时间序列', fontsize=14, fontweight='bold')
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()
    
    plt.tight_layout()
    st.pyplot(fig_time)
    plt.close(fig_time)
    
    # 频域图
    st.subheader("🔊 频域分析")
    
    fig_freq, axes = plt.subplots(2, 1, figsize=(12, 8))
    fig_freq.patch.set_facecolor('white')
    
    # 切向频谱
    axes[0].plot(signal_result_flap.f_spectrum, signal_result_flap.X_spectrum, 'b-', linewidth=1.5, label='频谱')
    axes[0].axvline(signal_result_flap.f_dominant_hz, color='red', linestyle='--', linewidth=2, label=f'主频: {signal_result_flap.f_dominant_hz:.3f} Hz')
    axes[0].set_xlabel('频率 (Hz)', fontsize=12)
    axes[0].set_ylabel('幅值 (mm)', fontsize=12)
    axes[0].set_title('切向位移频谱', fontsize=14, fontweight='bold')
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()
    axes[0].set_xlim([0, min(high_cut * 1.5, signal_result_flap.f_spectrum.max())])
    
    # 轴向频谱
    axes[1].plot(signal_result_edge.f_spectrum, signal_result_edge.X_spectrum, 'r-', linewidth=1.5, label='频谱')
    axes[1].axvline(signal_result_edge.f_dominant_hz, color='blue', linestyle='--', linewidth=2, label=f'主频: {signal_result_edge.f_dominant_hz:.3f} Hz')
    axes[1].set_xlabel('频率 (Hz)', fontsize=12)
    axes[1].set_ylabel('幅值 (mm)', fontsize=12)
    axes[1].set_title('轴向位移频谱', fontsize=14, fontweight='bold')
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()
    axes[1].set_xlim([0, min(high_cut * 1.5, signal_result_edge.f_spectrum.max())])
    
    plt.tight_layout()
    st.pyplot(fig_freq)
    plt.close(fig_freq)
    
    # 详细统计信息
    st.subheader("📋 详细统计信息")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 切向方向")
        st.markdown(f"""
        - **主频**: {signal_result_flap.f_dominant_hz:.4f} Hz
        - **峰峰值**: {signal_result_flap.A_pp_mm:.4f} mm
        - **RMS**: {signal_result_flap.A_rms_mm:.4f} mm
        - **异常状态**: {'⚠️ 异常' if signal_result_flap.is_abnormal else '✅ 正常'}
        """)
    
    with col2:
        st.markdown("### 轴向方向")
        st.markdown(f"""
        - **主频**: {signal_result_edge.f_dominant_hz:.4f} Hz
        - **峰峰值**: {signal_result_edge.A_pp_mm:.4f} mm
        - **RMS**: {signal_result_edge.A_rms_mm:.4f} mm
        - **异常状态**: {'⚠️ 异常' if signal_result_edge.is_abnormal else '✅ 正常'}
        """)
    
    # 数据下载
    st.markdown("---")
    st.subheader("💾 导出结果")
    
    # 导出为CSV
    if st.button("📥 导出统计数据为CSV"):
        import pandas as pd
        
        data = {
            '方向': ['切向', '轴向'],
            '主频_Hz': [signal_result_flap.f_dominant_hz, signal_result_edge.f_dominant_hz],
            '峰峰值_mm': [signal_result_flap.A_pp_mm, signal_result_edge.A_pp_mm],
            'RMS_mm': [signal_result_flap.A_rms_mm, signal_result_edge.A_rms_mm],
            '异常状态': [signal_result_flap.is_abnormal, signal_result_edge.is_abnormal]
        }
        
        df = pd.DataFrame(data)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        
        st.download_button(
            label="⬇️ 下载CSV文件",
            data=csv,
            file_name=f"vibration_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

else:
    st.info("👆 请上传NPZ文件并开始分析")

