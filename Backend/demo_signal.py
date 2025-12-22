from signal_analysis import DisplacementSeries, analyze_displacement_series

import numpy as np

if __name__ == "__main__":
    rng = np.random.default_rng(0)

    # 生成测试信号：1.2 Hz 正弦（峰值 2mm） + 低频漂移 + 噪声
    fs_demo = 50
    t = np.arange(0, 20.0, 1.0 / fs_demo)
    f0 = 1.2
    amp_peak = 2.0  # mm (peak)
    x = amp_peak * np.sin(2 * np.pi * f0 * t)

    drift = 1.0 * np.sin(2 * np.pi * 0.05 * t)  # 0.05Hz 漂移
    noise = 0.2 * rng.standard_normal(t.size)
    x = x + drift + noise

    # 模拟少量缺失点（NaN）
    x[100] = np.nan
    x[333] = np.inf

    disp = DisplacementSeries(
        time_stamps=t,
        d_t_mm=x,
        fs=fs_demo,
        fan_id="demo_fan",
    )

    result = analyze_displacement_series(
        disp_series=disp,
        low_cut=0.2,
        high_cut=5.0,
        A_pp_limit=10.0,
        A_rms_limit=5.0,
        window="hann",
        zero_pad_to=4096,       # 零填充提升频率轴分辨率（不提升真实信息）
        f_search_min=0.3,       # 主频搜索频段建议略收紧
        f_search_max=4.5,
    )

    print("fan_id:", result.fan_id)
    # print("A_pp_mm:", result.A_pp_mm)
    # print("A_rms_mm:", result.A_rms_mm)
    # print("f_dominant_hz:", result.f_dominant_hz)
    # print("is_abnormal:", result.is_abnormal)
    # print("quality:", result.quality)
    # print("preprocess_meta (keys):", list(result.preprocess_meta.keys()))
    # 可视化频频谱
    import matplotlib.pyplot as plt
    plt.plot(result.f_spectrum, result.X_spectrum)
    plt.show()