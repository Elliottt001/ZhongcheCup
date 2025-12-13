"""
signal_analysis.py

从位移时间序列中提取振动特征（工程增强版）：
- 输入检查（fs、频带、NaN、长度、时间戳等）
- 可选重采样（当 time_stamps 非等间隔时）
- 去均值/去趋势
- 带通滤波（Butterworth + 零相位 sosfiltfilt）
- 时域指标（峰-峰值、RMS）
- 频域分析（加窗 + 幅值校正 + 主频峰值搜索 + 峰值显著性）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple, Optional, Dict, Any

import numpy as np
from scipy import signal


# =========================
# 数据结构定义
# =========================

@dataclass
class DisplacementSeries:
    """
    位移时间序列（上游图像模块的输出，进入本模块的输入）。
    """
    time_stamps: np.ndarray  # (N,), seconds
    d_t_mm: np.ndarray       # (N,), millimeter
    fs: int                  # Hz
    fan_id: str              # identifier


@dataclass
class AnalysisResult:
    """
    振动分析结果（本模块输出，下游存储与可视化模块使用）。
    """
    A_pp_mm: float
    A_rms_mm: float
    f_dominant_hz: float
    f_spectrum: np.ndarray
    X_spectrum: np.ndarray
    is_abnormal: bool

    # 工程扩展字段（不破坏下游兼容：可忽略）
    fan_id: Optional[str] = None
    quality: Dict[str, Any] = field(default_factory=dict)        # e.g. {"peak_ratio":..., "snr_db":...}
    preprocess_meta: Dict[str, Any] = field(default_factory=dict) # e.g. {"resampled":..., "band":...}


# =========================
# 工具函数
# =========================

#将输入变为1D浮点数组，避免上有传入list、二维数组等导致报错
def _as_1d_float(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float).reshape(-1)
    return x

#确保采样率为正数
def _validate_fs(fs: int) -> int:
    if not isinstance(fs, (int, np.integer)):
        raise TypeError(f"fs must be int, got {type(fs)}")
    if fs <= 0:
        raise ValueError(f"fs must be > 0, got {fs}")
    return int(fs)


def _sanitize_signal(x: np.ndarray) -> np.ndarray:
    """
    去除 NaN/Inf：用线性插值填补；若全是无效值则抛错。
    """
    x = _as_1d_float(x)
    if x.size == 0:
        return x

    mask = np.isfinite(x)
    if mask.all():
        return x

    if not mask.any():
        raise ValueError("Signal contains no finite values (all NaN/Inf).")

    idx = np.arange(x.size)
    x_filled = x.copy()
    x_filled[~mask] = np.interp(idx[~mask], idx[mask], x[mask])
    return x_filled

#检查time_stamps是否严格递增
def _check_and_resample_if_needed(
    time_stamps: np.ndarray,
    x: np.ndarray,
    fs: int,
    jitter_ratio_tol: float = 0.02,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    检查 time_stamps 是否近似等间隔；若不等间隔，插值重采样到均匀时间网格。
    """
    t = _as_1d_float(time_stamps)
    x = _as_1d_float(x)
    fs = _validate_fs(fs)

    meta: Dict[str, Any] = {
        "resampled": False,
        "jitter_ratio": None,
        "t_start": None,
        "t_end": None,
        "fs_used": fs,
    }

    if t.size == 0 or x.size == 0:
        return t, x, meta
    if t.size != x.size:
        raise ValueError(f"time_stamps and signal must have same length, got {t.size} vs {x.size}")

    # 保证时间单调递增
    if np.any(np.diff(t) <= 0):
        # 尝试按时间排序；若重复时间点仍存在，则会导致插值问题
        order = np.argsort(t)
        t = t[order]
        x = x[order]
        if np.any(np.diff(t) <= 0):
            raise ValueError("time_stamps must be strictly increasing (after sorting still not).")

    dt = np.diff(t)
    dt_median = float(np.median(dt))
    if dt_median <= 0:
        raise ValueError("Invalid time_stamps (median dt <= 0).")

    # 估计抖动程度：相对中位数的偏差
    jitter_ratio = float(np.std(dt) / dt_median) if dt.size > 1 else 0.0
    meta["jitter_ratio"] = jitter_ratio
    meta["t_start"] = float(t[0])
    meta["t_end"] = float(t[-1])

    # 如果抖动很小，认为等间隔，不重采样
    if jitter_ratio <= jitter_ratio_tol:
        return t, x, meta

    # 重采样到均匀网格
    t0, t1 = float(t[0]), float(t[-1])
    # 目标采样点数：按 fs 覆盖原时长
    N_target = int(np.floor((t1 - t0) * fs)) + 1
    if N_target < 8:
        # 数据太短，重采样意义不大
        return t, x, meta

    t_uniform = t0 + np.arange(N_target) / fs
    x_uniform = np.interp(t_uniform, t, x)

    meta["resampled"] = True
    meta["fs_used"] = fs
    return t_uniform, x_uniform, meta


def _clamp_band(low_cut: float, high_cut: float, fs: int, margin: float = 0.95) -> Tuple[float, float, Dict[str, Any]]:
    """
    将频带裁剪到 (0, Nyquist) 内，并保证 low < high。
    """
    fs = _validate_fs(fs)
    nyq = 0.5 * fs

    if low_cut is None or high_cut is None:
        raise ValueError("low_cut and high_cut must not be None")

    low = float(low_cut)
    high = float(high_cut)

    meta = {"band_input": (low, high), "band_used": None, "nyquist": nyq}

    # 基本合法性
    if not np.isfinite(low) or not np.isfinite(high):
        raise ValueError(f"Band edges must be finite, got low_cut={low}, high_cut={high}")

    # clamp
    eps = 1e-6
    low = max(low, eps)
    high = min(high, nyq * margin)

    if low >= high:
        raise ValueError(f"Invalid band after clamp: low_cut={low} >= high_cut={high}. "
                         f"Check fs={fs}, nyquist={nyq}, and input band={low_cut, high_cut}")

    meta["band_used"] = (low, high)
    return low, high, meta


# =========================
# 核心函数
# =========================

def filter_signal(
    d_t_mm: np.ndarray,
    fs: int,
    low_cut: float,
    high_cut: float,
    order: int = 4,
    detrend: bool = True,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    对位移信号进行带通滤波（工程增强版）。
    返回滤波结果 + meta（便于记录参数）。
    """
    fs = _validate_fs(fs)
    x = _sanitize_signal(d_t_mm)

    if x.size == 0:
        return x, {"note": "empty_signal"}

    # 去趋势/去均值：先做 detrend 再去均值更稳
    if detrend and x.size >= 3:
        x = signal.detrend(x, type="linear")
    x = x - float(np.mean(x))

    low, high, band_meta = _clamp_band(low_cut, high_cut, fs)
    sos = signal.butter(
        N=order,
        Wn=[low, high],
        btype="bandpass",
        fs=fs,
        output="sos",
    )

    # 零相位滤波，避免相位畸变
    x_filt = signal.sosfiltfilt(sos, x)

    meta = {
        "filter": "butterworth_bandpass_sosfiltfilt",
        "order": order,
        "detrend": detrend,
        **band_meta,
    }
    return x_filt, meta


def calculate_time_domain_amp(d_t_mm_filtered: np.ndarray) -> Tuple[float, float]:
    """
    计算时域振动指标：峰-峰值幅度与 RMS 幅度。
    """
    x = _as_1d_float(d_t_mm_filtered)
    if x.size == 0:
        return 0.0, 0.0

    A_pp_mm = float(np.max(x) - np.min(x))
    A_rms_mm = float(np.sqrt(np.mean(x ** 2)))
    return A_pp_mm, A_rms_mm


def calculate_fft_spectrum(
    d_t_mm_filtered: np.ndarray,
    fs: int,
    window: str = "hann",
    zero_pad_to: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    """
    计算单边幅度谱（带窗函数与幅值校正），返回 (freqs, X_amp, meta)。
    """
    fs = _validate_fs(fs)
    x = _sanitize_signal(d_t_mm_filtered)
    N = x.size

    if N == 0:
        return np.array([]), np.array([]), {"note": "empty_signal"}

    # 窗函数
    if window is None or window == "none":
        w = np.ones(N, dtype=float)
        window_name = "none"
    else:
        try:
            w = signal.get_window(window, N, fftbins=True).astype(float)
            window_name = str(window)
        except Exception as e:
            raise ValueError(f"Invalid window '{window}': {e}")

    # coherent gain：平均值，用于幅值校正（让正弦峰值更接近真实幅值）
    cg = float(np.mean(w))
    if cg <= 0:
        cg = 1.0

    xw = x * w

    # FFT 长度（零填充可提升频率轴分辨率，不提升真实信息量）
    nfft = int(zero_pad_to) if (zero_pad_to is not None) else N
    if nfft < N:
        nfft = N
    # 取为 2 的幂常更快（可选）
    # nfft = int(2 ** np.ceil(np.log2(nfft)))

    X_complex = np.fft.rfft(xw, n=nfft)
    freqs = np.fft.rfftfreq(nfft, d=1.0 / fs)

    # 单边幅度谱校正：2/(N*cg) * |X|
    # 注意：DC(0Hz) 和 Nyquist(若存在) 不应该乘 2，这里做标准处理
    X_amp = (2.0 / (N * cg)) * np.abs(X_complex)
    if X_amp.size > 0:
        X_amp[0] = X_amp[0] / 2.0
    if (nfft % 2 == 0) and (X_amp.size > 1):  # Nyquist 存在于 rfft 末端
        X_amp[-1] = X_amp[-1] / 2.0

    meta = {
        "window": window_name,
        "coherent_gain": cg,
        "n": N,
        "nfft": nfft,
        "fs": fs,
    }
    return freqs, X_amp, meta


def find_dominant_frequency(
    freqs: np.ndarray,
    X_amp: np.ndarray,
    fmin: float,
    fmax: float,
) -> Tuple[float, Dict[str, Any]]:
    """
    在指定频段内寻找幅值谱最大峰，返回主频 + quality 指标。
    """
    freqs = _as_1d_float(freqs)
    X_amp = _as_1d_float(X_amp)

    if freqs.size == 0 or X_amp.size == 0:
        return 0.0, {"note": "empty_spectrum"}

    if freqs.size != X_amp.size:
        raise ValueError("freqs and X_amp must have same length")

    # 限定搜索范围
    fmin = float(fmin)
    fmax = float(fmax)
    if not np.isfinite(fmin) or not np.isfinite(fmax) or fmin <= 0:
        raise ValueError(f"Invalid fmin/fmax: {fmin}/{fmax}")
    if fmin >= fmax:
        raise ValueError(f"Invalid search band: fmin >= fmax ({fmin} >= {fmax})")

    band_mask = (freqs >= fmin) & (freqs <= fmax)
    if not np.any(band_mask):
        return 0.0, {"note": "no_bins_in_search_band", "fmin": fmin, "fmax": fmax}

    f_band = freqs[band_mask]
    X_band = X_amp[band_mask]

    # 找最大峰
    idx_local = int(np.argmax(X_band))
    f_peak = float(f_band[idx_local])
    peak_amp = float(X_band[idx_local])

    # 质量指标：peak_ratio（主峰/次峰）、snr_db（主峰相对中位数噪声）
    X_sorted = np.sort(X_band)
    second = float(X_sorted[-2]) if X_sorted.size >= 2 else 0.0
    peak_ratio = float(peak_amp / (second + 1e-12))

    noise_floor = float(np.median(X_band))
    snr_db = float(20.0 * np.log10((peak_amp + 1e-12) / (noise_floor + 1e-12)))

    quality = {
        "peak_amp": peak_amp,
        "second_peak_amp": second,
        "peak_ratio": peak_ratio,
        "snr_db": snr_db,
        "search_band": (fmin, fmax),
    }
    return f_peak, quality


def analyze_displacement_series(
    disp_series: DisplacementSeries,
    low_cut: float,
    high_cut: float,
    A_pp_limit: Optional[float] = None,
    A_rms_limit: Optional[float] = None,
    # 频谱/主频参数
    window: str = "hann",
    zero_pad_to: Optional[int] = None,
    # 主频搜索频段（默认与滤波频段一致，但建议略收紧）
    f_search_min: Optional[float] = None,
    f_search_max: Optional[float] = None,
    # 时间戳抖动阈值，超过则重采样
    jitter_ratio_tol: float = 0.02,
) -> AnalysisResult:
    """
    高层封装：直接从 DisplacementSeries 得到 AnalysisResult（工程增强版）。
    """
    fs = _validate_fs(disp_series.fs)

    t_raw = _as_1d_float(disp_series.time_stamps)
    x_raw = _sanitize_signal(disp_series.d_t_mm)

    # 0) 检查/重采样
    t, x, resample_meta = _check_and_resample_if_needed(
        time_stamps=t_raw,
        x=x_raw,
        fs=fs,
        jitter_ratio_tol=jitter_ratio_tol,
    )

    # 1) 带通滤波
    x_filt, filter_meta = filter_signal(
        d_t_mm=x,
        fs=fs,
        low_cut=low_cut,
        high_cut=high_cut,
        order=4,
        detrend=True,
    )

    # 2) 时域幅值
    A_pp_mm, A_rms_mm = calculate_time_domain_amp(x_filt)

    # 3) 频谱（加窗 + 幅值校正）
    freqs, X_amp, spec_meta = calculate_fft_spectrum(
        d_t_mm_filtered=x_filt,
        fs=fs,
        window=window,
        zero_pad_to=zero_pad_to,
    )

    # 4) 主频搜索频段
    # 默认：在滤波带内找峰，稍微避开边界更稳
    band_low, band_high, _ = _clamp_band(low_cut, high_cut, fs)
    fmin = float(f_search_min) if f_search_min is not None else max(band_low, 1e-3)
    fmax = float(f_search_max) if f_search_max is not None else band_high
    # 若用户给的搜索频段不合理，退回到 band
    if (not np.isfinite(fmin)) or (not np.isfinite(fmax)) or (fmin <= 0) or (fmin >= fmax):
        fmin, fmax = max(band_low, 1e-3), band_high

    f_dom, quality = find_dominant_frequency(freqs, X_amp, fmin=fmin, fmax=fmax)

    # 5) 异常判定（可扩展）
    abnormal_flags = []
    if A_pp_limit is not None:
        abnormal_flags.append(A_pp_mm > float(A_pp_limit))
    if A_rms_limit is not None:
        abnormal_flags.append(A_rms_mm > float(A_rms_limit))

    # 可选：若主峰显著性太低，标记“结果不可信”，这里不直接算异常，只写进 quality
    # 你也可以把它纳入异常逻辑（取决于项目需求）
    is_abnormal = any(abnormal_flags) if abnormal_flags else False

    preprocess_meta: Dict[str, Any] = {
        **resample_meta,
        **filter_meta,
        **spec_meta,
        "n_raw": int(t_raw.size),
        "n_used": int(t.size),
    }

    return AnalysisResult(
        A_pp_mm=A_pp_mm,
        A_rms_mm=A_rms_mm,
        f_dominant_hz=f_dom,
        f_spectrum=freqs,
        X_spectrum=X_amp,
        is_abnormal=is_abnormal,
        fan_id=disp_series.fan_id,
        quality=quality,
        preprocess_meta=preprocess_meta,
    )


# =========================
# 本地简单测试（示例）
# =========================

# =========================
# 本地测试（多模态 + 验证 high_cut 是否有效）
# =========================

if __name__ == "__main__":
    rng = np.random.default_rng(0)

    # 为了容纳“可被 high_cut 滤掉”的高频模态，fs 要足够高
    fs_demo = 100  # Hz
    T = 30.0
    t = np.arange(0, T, 1.0 / fs_demo)

    # -------- 多模态振动（单位：mm）--------
    # 模态1：低频主模态（例如叶片一阶）
    f1, A1 = 1.2, 2.0      # 1.2 Hz，peak=2.0mm
    mode1 = A1 * np.sin(2 * np.pi * f1 * t)

    # 模态2：中频模态（例如二阶或耦合模态）
    f2, A2 = 3.6, 0.8      # 3.6 Hz，peak=0.8mm
    mode2 = A2 * np.sin(2 * np.pi * f2 * t + 0.3)

    # 模态3：高频模态（专门用于验证 high_cut 是否有效）
    # 选 12 Hz：当 high_cut=5Hz 时应被明显压掉；当 high_cut=20Hz 时应保留
    f3, A3 = 12.0, 0.6     # 12 Hz，peak=0.6mm
    mode3 = A3 * np.sin(2 * np.pi * f3 * t + 1.1)

    # 给高频模态一个慢包络，更接近真实（幅值随时间起伏）
    envelope = 0.5 * (1.0 + np.sin(2 * np.pi * 0.15 * t))  # 0.15 Hz 调制
    mode3 = envelope * mode3

    # -------- 漂移 + 噪声 + 脉冲扰动--------
    drift = 1.0 * np.sin(2 * np.pi * 0.05 * t)          # 0.05 Hz 漂移（应被 low_cut 抑制）
    noise = 0.15 * rng.standard_normal(t.size)          # 白噪声

    impulses = np.zeros_like(t)
    idx = rng.choice(t.size, size=6, replace=False)     # 少量尖峰（模拟瞬时测量异常）
    impulses[idx] = rng.normal(loc=0.0, scale=1.5, size=idx.size)

    x = mode1 + mode2 + mode3 + drift + noise + impulses

    # 模拟少量缺失点（NaN/Inf）
    x[200] = np.nan
    x[777] = np.inf

    disp = DisplacementSeries(
        time_stamps=t,
        d_t_mm=x,
        fs=fs_demo,
        fan_id="demo_multi_mode",
    )

    # -------- 对比实验：只改 high_cut --------
    # Case A：high_cut 较低（应滤掉 12Hz 高模态）
    res_low = analyze_displacement_series(
        disp_series=disp,
        low_cut=0.2,
        high_cut=5.0,          # 12 Hz 应被强烈衰减
        window="hann",
        zero_pad_to=8192,
        f_search_min=0.3,
        f_search_max=4.5,      # 主频只在低频模态范围找（避免 12Hz 干扰主频判定）
    )

    # Case B：high_cut 较高（允许 12Hz 通过）
    res_high = analyze_displacement_series(
        disp_series=disp,
        low_cut=0.2,
        high_cut=20.0,         # 12 Hz 应保留
        window="hann",
        zero_pad_to=8192,
        f_search_min=0.3,
        f_search_max=18.0,
    )

    # -------- 频谱峰值提取：对比 1.2/3.6/12 Hz 三个模态的峰是否存在 --------
    def _peak_at(freqs: np.ndarray, amps: np.ndarray, f0: float, tol: float = 0.25) -> float:
        freqs = np.asarray(freqs, dtype=float).reshape(-1)
        amps = np.asarray(amps, dtype=float).reshape(-1)
        m = (freqs >= f0 - tol) & (freqs <= f0 + tol)
        return float(np.max(amps[m])) if np.any(m) else float("nan")

    print("\n=== Case A: high_cut=5Hz (12Hz应被滤掉) ===")
    print("fan_id:", res_low.fan_id)
    print("A_pp_mm:", res_low.A_pp_mm)
    print("A_rms_mm:", res_low.A_rms_mm)
    print("f_dominant_hz:", res_low.f_dominant_hz)
    print("quality:", res_low.quality)
    print("Peak@1.2Hz:", _peak_at(res_low.f_spectrum, res_low.X_spectrum, 1.2))
    print("Peak@3.6Hz:", _peak_at(res_low.f_spectrum, res_low.X_spectrum, 3.6))
    print("Peak@12Hz :", _peak_at(res_low.f_spectrum, res_low.X_spectrum, 12.0), " <-- 应显著更小/接近消失")

    print("\n=== Case B: high_cut=20Hz (12Hz应保留) ===")
    print("fan_id:", res_high.fan_id)
    print("A_pp_mm:", res_high.A_pp_mm)
    print("A_rms_mm:", res_high.A_rms_mm)
    print("f_dominant_hz:", res_high.f_dominant_hz)
    print("quality:", res_high.quality)
    print("Peak@1.2Hz:", _peak_at(res_high.f_spectrum, res_high.X_spectrum, 1.2))
    print("Peak@3.6Hz:", _peak_at(res_high.f_spectrum, res_high.X_spectrum, 3.6))
    print("Peak@12Hz :", _peak_at(res_high.f_spectrum, res_high.X_spectrum, 12.0), " <-- 应明显更大")

    # 额外：定量比较 12Hz 峰值衰减倍数（越大说明 high_cut 作用越明显）
    p12_low = _peak_at(res_low.f_spectrum, res_low.X_spectrum, 12.0)
    p12_high = _peak_at(res_high.f_spectrum, res_high.X_spectrum, 12.0)
    if np.isfinite(p12_low) and np.isfinite(p12_high):
        print("\n12Hz attenuation ratio (high_cut=20 / high_cut=5):", (p12_high + 1e-12) / (p12_low + 1e-12))
