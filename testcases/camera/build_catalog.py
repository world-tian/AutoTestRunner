"""维护相机第一版目录清单和带说明的薄用例脚本。执行后需审阅 diff。"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
GROUPS = {
    'output': ('基础图像 / Output', '正常照明、有纹理的实际输出图片，支持8-bit JPEG/PNG'),
    'ae': ('曝光 / AE', '固定光源、构图的标准曝光场景，等待曝光稳定'),
    'sharpness': ('清晰度 / Sharpness', '固定光源、距离、分辨率；中心和四角包含相同重复纹理图卡'),
    'awb': ('白平衡 / AWB & Color', '均匀照明的中性灰卡，等待AWB稳定；不能使用任意彩色场景'),
    'shading': ('亮度均匀性 / LSC & Shading', '均匀平场或积分球，锁定曝光；避免照明不均干扰'),
    'defect': ('异常检测 / Defect', '中性均匀场，仅针对大面积局部色度异常；非通用花屏或坏点检测'),
    'noise': ('噪声与信噪比 / Noise & SNR', '固定照明、灰场或暗场；噪声结果依赖曝光、增益和温度'),
    'geometry': ('几何 / Geometry', '综合图网格或直线；基础代理不替代标定级畸变模型'),
    'underwater': ('水下画质 / Underwater IQ', '同一综合卡的空气/水下配对输入；缺少配对输入时不判通过'),
    'regression': ('版本回归 / Regression', '固定输入和版本基线；缺少基线时明确返回 N/A'),
}
ROWS = [
    ('output', 'IMG', 1, 'image_parse', '图片可解析', '判断图像输出链路是否正常', '图片完整解码成功，无损坏/截断'),
    ('output', 'IMG', 2, 'output_resolution', '分辨率检查', '验证输出规格是否符合要求', '按EXIF方向解码后宽高等于 expected_size'),
    ('output', 'IMG', 3, 'abnormal_frame', '全黑/全白/严重异常图像', '筛查全黑、全白或亮度近乎恒定的异常输出；不覆盖花屏和坏点', 'Y≤10 与 Y≥245 的像素占比各 < 0.98，亮度标准差 ≥ 1'),
    ('output', 'IMG', 4, 'exif_orientation', 'EXIF方向', '检查原始图片方向元数据是否存在且有效', 'EXIF Orientation 为 1～8，缺失时按默认方向 1处理'),
    ('output', 'IMG', 5, 'bit_depth_channel', '位深与通道', '检查输出是否为支持的8-bit RGB/RGBA图像', '位深为8，通道为3或4'),
    ('ae', 'AE', 1, 'average_brightness', '平均亮度', '验证整体曝光水平', 'mean_min ≤ 平均亮度 ≤ mean_max'),
    ('ae', 'AE', 2, 'underexposure_ratio', '欠曝比例', '判断暗部是否存在明显欠曝', 'Y≤10 像素占比 ≤ under_max'),
    ('ae', 'AE', 3, 'overexposure_ratio', '过曝比例', '判断高光区域是否存在明显截断', 'Y≥245 像素占比 ≤ over_max'),
    ('ae', 'AE', 5, 'histogram_percentile', '亮度直方图分位数', '识别平均亮度正常但暗部或高光分布异常的图像', 'P1≥5、P5≥15、P50≥60、P95≤240、P99≤250'),
    ('ae', 'AE', 6, 'median_brightness', '亮度中位数', '减少少量极端像素对整体曝光判断的影响', 'median_min ≤ 亮度中位数 ≤ median_max'),
    ('ae', 'AE', 7, 'effective_dynamic_range', '有效动态范围', '检查P5到P95的有效亮度范围', 'dynamic_range_min ≤ P95-P5 ≤ dynamic_range_max'),
    ('ae', 'AE', 8, 'image_contrast', '图像对比度', '检查全图亮度RMS对比度', 'contrast_min ≤ RMS contrast ≤ contrast_max'),
    ('ae', 'AE', 9, 'histogram_entropy', '直方图熵', '检查亮度分布的信息量和异常塌缩', 'entropy_min ≤ 亮度直方图熵 ≤ entropy_max'),
    ('sharpness', 'SHP', 1, 'global_sharpness', '全局清晰度', '快速判断失焦、抖动、整体模糊', '全局 Laplacian 方差 ≥ sharpness_min；不是MTF'),
    ('sharpness', 'SHP', 2, 'center_sharpness', '中心区域清晰度', '验证镜头中心成像质量', '中心25%宽高ROI清晰度 ≥ sharpness_min'),
    ('sharpness', 'SHP', 3, 'corner_sharpness', '四角区域清晰度', '判断边缘成像和局部异常', '四角25%宽高ROI的清晰度分别 ≥ sharpness_min'),
    ('sharpness', 'SHP', 4, 'center_corner_consistency', '中心/四角清晰度一致性', '辅助发现镜头倾斜、AA、组装问题', '五区清晰度最小/最大 ≥ sharpness_ratio_min，且各区清晰度达标'),
    ('sharpness', 'SHP', 5, 'roi_3x3_heatmap', '3×3清晰度热力图', '发现局部清晰度下降和空间一致性异常', '3×3各ROI清晰度 ≥ sharpness_min，且最小/最大 ≥ sharpness_ratio_min'),
    ('sharpness', 'SHP', 6, 'tenengrad', '梯度清晰度', '使用Sobel梯度能量补充Laplacian清晰度', 'tenengrad ≥ tenengrad_min'),
    ('awb', 'COLOR', 1, 'rgb_channel_statistics', 'RGB 通道统计', '验证 RGB 通道及颜色输出基础状态', 'RGB均值各在 channel_min..channel_max，另记录通道标准差'),
    ('awb', 'COLOR', 2, 'color_cast', '明显偏色检测', '初步判断 AWB 或 ISP 色彩异常', 'RGB均值极差/三通道均值 ≤ color_cast_max，且各通道非暗场；不是ΔE'),
    ('awb', 'COLOR', 3, 'red_green_ratio', '灰卡R/G比例', '检查中性灰场的红绿通道比例', 'rg_min ≤ R/G ≤ rg_max'),
    ('awb', 'COLOR', 4, 'blue_green_ratio', '灰卡B/G比例', '检查中性灰场的蓝绿通道比例', 'bg_min ≤ B/G ≤ bg_max'),
    ('awb', 'COLOR', 5, 'neutral_error', '中性误差', '检查中性灰场三通道离散程度', 'neutral_error ≤ neutral_error_max'),
    ('shading', 'SHD', 1, 'center_edge_brightness', '中心/边缘亮度差', '判断暗角及 LSC 效果', '中心与各角均值差/中心均值 ≤ center_edge_max，且各区亮度 ≥ mean_min'),
    ('shading', 'SHD', 2, 'corner_brightness_consistency', '四角亮度一致性', '判断局部 Shading 或装配异常', '四角亮度极差/四角均值 ≤ corner_delta_max，且各区亮度 ≥ mean_min'),
    ('defect', 'DEFECT', 4, 'large_color_block', '大面积异常色块/花屏检测', '发现 ISP、Sensor 或数据传输异常', '8×8分块相对于全图中位色度的最大块均值 ≤ chroma_tile_max'),
    ('output', 'IMG', 6, 'duplicate_frame', '重复帧/冻结', '检测连续输出是否冻结或重复', '需要至少两帧目录；重复相似度 ≤ duplicate_similarity_max，否则 N/A/失败'),
    ('output', 'IMG', 7, 'jpeg_compression', 'JPEG异常压缩', '检测JPEG 8×8块效应代理', 'JPEG块效应 ≤ jpeg_blockiness_max；非JPEG输入返回 N/A/失败'),
    ('sharpness', 'SHP', 7, 'mtf50', 'MTF50基础代理', '用边缘梯度频率代理评估MTF50', '纹理/边缘输入的 MTF50 代理 ≥ mtf50_min；不替代ISO12233标定'),
    ('sharpness', 'SHP', 8, 'mtf20', 'MTF20基础代理', '用边缘梯度频率代理评估MTF20', '纹理/边缘输入的 MTF20 代理 ≥ mtf20_min；不替代ISO12233标定'),
    ('sharpness', 'SHP', 9, 'corner_center_mtf_ratio', '角落/中心MTF比', '比较中心与四角清晰度代理', '角落/中心代理最小比 ≥ corner_center_mtf_ratio_min'),
    ('sharpness', 'SHP', 10, 'siemens_star_mtf', '西门子星MTF50/MTF20试验', '先定位图卡平面并透视矫正，再从6颗西门子星（中间2颗、四角4颗）估计MTF50主值并输出MTF20辅助值', '6颗配置的西门子星全部成功输出 MTF50；单位为 cycles/pixel，MTF20作为辅助值，产品阈值待标定'),
    ('sharpness', 'SHP', 11, 'slanted_edge_sfr', '斜边SFR整体清晰度', '先定位图卡并矫正，再锁定3x3图卡的9个黑白斜边方块，在原图像素上用斜边法计算整体SFR、MTF50/MTF20', '9个斜边方块必须全部锁定（否则立即失败且不计算），至少7条斜边得到有效MTF50，整体MTF50中位数≥0.3 cycles/pixel'),
    ('awb', 'COLOR', 6, 'colorchecker_delta_e', 'ColorChecker色差基础代理', '以RGB通道离散度代理中性色差', '中性色差代理 ≤ delta_e_max；未定位标准ColorChecker时为基础代理'),
    ('shading', 'SHD', 3, 'luma_9x9_heatmap', '9×9亮度均匀性', '输出9×9亮度热力图和范围', '9×9亮度范围 ≤ luma_range_max'),
    ('shading', 'SHD', 4, 'color_9x9_heatmap', '9×9颜色均匀性', '输出9×9 R/G、B/G热力图和范围', 'R/G、B/G范围分别 ≤ rg_range_max、bg_range_max'),
    ('noise', 'NOISE', 1, 'luma_noise', '亮度噪声', '测量灰场亮度标准差', '亮度噪声 ≤ luma_noise_max'),
    ('noise', 'NOISE', 2, 'chroma_noise', '色度噪声', '测量Cb/Cr色度标准差', '色度噪声 ≤ chroma_noise_max'),
    ('noise', 'NOISE', 3, 'signal_to_noise_ratio', '信噪比', '计算Mean/Std及dB', 'SNR ≥ snr_min 或 snr_db ≥ snr_db_min'),
    ('noise', 'NOISE', 4, 'dark_frame_noise', '暗场噪声', '在暗场中测量黑电平噪声', '暗场平均亮度 ≤ dark_mean_max 且噪声 ≤ dark_noise_max'),
    ('noise', 'NOISE', 5, 'temporal_noise', '时域噪声', '比较连续帧的像素波动', '需要至少两帧目录；时域噪声 ≤ temporal_noise_max'),
    ('geometry', 'GEO', 1, 'lens_distortion', '镜头畸变', '以边缘半径离散度作基础代理', '畸变代理 ≤ distortion_max'),
    ('geometry', 'GEO', 2, 'lateral_chromatic_aberration', '横向色差LCA', '测量通道色差梯度代理', 'LCA代理 ≤ lca_max'),
    ('geometry', 'GEO', 3, 'optical_center_offset', '光轴中心偏移', '从边缘分布估计几何中心偏移', '中心偏移 ≤ center_offset_max'),
    ('geometry', 'GEO', 4, 'perspective_error', '透视误差', '比较左右边缘线的垂直偏差', '透视误差 ≤ perspective_max'),
    ('defect', 'DEFECT', 5, 'hot_pixel', '热点', '检测均匀场孤立亮点', '热点数量 ≤ hot_pixel_max'),
    ('defect', 'DEFECT', 6, 'dead_pixel', '坏点', '检测均匀场孤立暗点', '坏点数量 ≤ dead_pixel_max'),
    ('defect', 'DEFECT', 7, 'horizontal_banding', '水平条纹', '比较逐行亮度周期波动', '水平条纹代理 ≤ horizontal_banding_max'),
    ('defect', 'DEFECT', 8, 'vertical_banding', '垂直条纹', '比较逐列亮度周期波动', '垂直条纹代理 ≤ vertical_banding_max'),
    ('defect', 'DEFECT', 9, 'frame_corruption', '帧损坏', '检查当前帧尺寸、有限值和可解码性', '图像全部有限且尺寸符合 expected_size'),
    ('defect', 'DEFECT', 10, 'duplicate_frame', '冻结/重复帧', '检测连续帧是否重复', '需要至少两帧目录；重复相似度 ≤ duplicate_similarity_max，否则 N/A/失败'),
    ('underwater', 'UW', 1, 'sharpness_change', '水下清晰度变化', '比较空气与水下清晰度代理', '需要空气基线；水下/空气清晰度比 ≥ underwater_ratio_min'),
    ('underwater', 'UW', 2, 'fov_distortion', '水下视场角/畸变', '比较输入几何代理变化', '需要空气基线且畸变变化 ≤ fov_change_max'),
    ('underwater', 'UW', 3, 'awb', '水下白平衡', '比较水下RGB通道平衡', '水下R/G、B/G均在配置范围'),
    ('underwater', 'UW', 4, 'contrast_loss', '水下对比度损失', '比较水下与空气RMS对比度', '需要空气基线且对比度损失 ≤ contrast_loss_max'),
    ('underwater', 'UW', 5, 'backscatter', '水下散射颗粒', '检测亮度局部离群颗粒代理', '散射亮点数量 ≤ backscatter_max'),
    ('regression', 'REG', 1, 'firmware_metrics', '固件版本指标对比', '与配置基线比较综合指标', '必须提供基线文件；变化率不超过 regression_delta_max'),
    ('regression', 'REG', 2, 'isp_metrics', 'ISP版本指标对比', '与配置基线比较图像指标', '必须提供基线文件；变化率不超过 regression_delta_max'),
    ('regression', 'REG', 3, 'golden_sample', '模组Golden Sample对比', '与Golden Sample图像比较', '必须提供基线文件；相似度 ≥ golden_similarity_min'),
]
PRIORITY_BY_SLUG = {'histogram_percentile': 'P1', 'roi_3x3_heatmap': 'P1', 'exif_orientation': 'P1', 'bit_depth_channel': 'P1', 'median_brightness': 'P1', 'effective_dynamic_range': 'P1', 'image_contrast': 'P1', 'histogram_entropy': 'P1', 'tenengrad': 'P1', 'red_green_ratio': 'P1', 'blue_green_ratio': 'P1', 'neutral_error': 'P1', 'duplicate_frame': 'P1', 'jpeg_compression': 'P1', 'mtf50': 'P1', 'mtf20': 'P1', 'corner_center_mtf_ratio': 'P1', 'siemens_star_mtf': 'P1', 'slanted_edge_sfr': 'P1', 'colorchecker_delta_e': 'P1', 'luma_9x9_heatmap': 'P1', 'color_9x9_heatmap': 'P1', 'luma_noise': 'P1', 'chroma_noise': 'P1', 'signal_to_noise_ratio': 'P1', 'dark_frame_noise': 'P1', 'temporal_noise': 'P1', 'lens_distortion': 'P1', 'lateral_chromatic_aberration': 'P1', 'optical_center_offset': 'P1', 'perspective_error': 'P1', 'hot_pixel': 'P1', 'dead_pixel': 'P1', 'horizontal_banding': 'P1', 'vertical_banding': 'P1', 'frame_corruption': 'P1', 'sharpness_change': 'P1', 'fov_distortion': 'P1', 'awb': 'P1', 'contrast_loss': 'P1', 'backscatter': 'P1', 'firmware_metrics': 'P1', 'isp_metrics': 'P1', 'golden_sample': 'P1'}


def build():
    catalog = []
    for category, prefix, num, slug, title, desc, expected in ROWS:
        cid = f'CAM-{prefix}-{num:03d}'
        label, pre = GROUPS[category]
        priority = PRIORITY_BY_SLUG.get(slug, 'P0')
        # 目录名表达模块、优先级和功能：<module>/<priority>/test-<module>-<feature>。
        folder = ROOT / category / priority / f'test-{category}-{slug}'
        fn = f'test_{category}_{slug}'
        script = folder / f'{fn}.py'
        if not script.is_file():
            raise FileNotFoundError(f'用例脚本不存在: {script}')
        relative = script.relative_to(ROOT).as_posix()
        catalog.append(dict(local_case_id=cid, title=f'{cid} {title}', priority=priority,
                            feature=f'camera/{category}', test_class=label, description=desc,
                            preconditions=pre, steps=[f'准备场景：{pre}',
                            '配置 CAMERA_CONFIG 中该类别图片和产品验收阈值',
                            f'在 Runner 根目录运行 python -m autotest_runner run testcases/camera/{relative}',
                            '查看 HTML 报告和 reports/camera 的指标证据，按配置阈值判定'],
                            expected_result=expected, script_path=relative, function=fn))
    (ROOT / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')
    # 脚本判定和阈值由用例自身维护；生成目录清单时绝不覆盖脚本或公共配置。


if __name__ == '__main__':
    build()
