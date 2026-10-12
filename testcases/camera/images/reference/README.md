# 厂商采集靶图示意

这里的 PNG 是拍摄任务的布局说明，不是相机测试输入，不具有可追溯反射率、斜边、格距或均匀度。运行厂商专项 plan 时必须使用设备拍摄的实物靶图，通过 `--picture` 传入。

- `vendor_flat_field_reference.png`：Shading。实物是积分球或已验证均匀度的漫射背光板。图中 9×9 格线只是软件统计位置，真实靶面不能有格线。
- `vendor_neutral_gray_reference.png`：AWB。实物是中性灰卡，尽量充满画面；现有算法对全图 RGB 求均值，不应混入彩色块。
- `vendor_slanted_edge_reference.png`：清晰度。3×3 九区均有重复斜边，兼顾中心/四角与九宫格 ROI；真实 MTF50/20 算法尚未实现。
- `vendor_geometry_grid_reference.png`：几何。实物为格距已测量的平整棋盘格；当前算法只输出几何代理，未求内参/畸变系数。
- `vendor_combined_screening_reference.png`：常用综合布局，九处斜边加背景网格，可在同一张实拍图上执行 `camera_vendor_lens_optics.yaml` 的清晰度和几何代理筛查。斜边块遮挡了网格，正式棋盘格角点标定及 ISO12233 MTF 必须另拍完整标准靶卡。
- 用户提供的黑白图卡（顶部写有 `VALUES IN 100X LINES PER PICTURE HEIGHT`、含西门子星和分辨率楔形）属于旧式 ISO/CIPA 视觉分辨率图，不是 2014/2017/2023 eSFR 低对比度斜边标准靶。它可用于 `CAM-SHP-010` 的西门子星实验性 MTF 测量，但不能直接作为正式 eSFR MTF50/MTF20 验收图。
- `CAM-SHP-010` 使用 `SFR_STAR_REGIONS` JSON 标注每颗星的归一化 `x`、`y`、`radius` 和整圈 `cycles`；专项 plan 已为当前完整图卡预置左中/右下两颗 36 周期星，也可用 `--sfr-stars` 覆盖。MTF50、MTF20、频率曲线和判定阈值统一使用 cycles/pixel。手机拍摄后若有透视、裁剪或数字变焦，应重新标定图卡定位参数，不能盲目沿用屏幕示例坐标。
- `vendor_air_water_pair_reference.png`：水下。空气和水下对同一实物靶卡成对采集；AWB 需另拍全幅灰卡，对比度需灰阶靶卡，散射需连续帧。当前 UW-001/002/004 仍未实现配对判定。

统一采集记录：工站、模组/镜头/光学窗口状态、图卡型号及物理尺寸、距离、光源色温与照度、曝光、增益、白平衡锁定状态、介质、FW/ISP 版本。工站截图中的 55 cm、6500±500 K、350±100 lux 需以经确认的厂商规格为准。

使用 `python make_vendor_targets.py` 可重新生成示意图。

厂商交付包清单见 `vendor_target_package.md`。其中 `vendor_flat_field_reference.png`、`vendor_neutral_gray_reference.png`、`vendor_slanted_edge_reference.png`、`vendor_geometry_grid_reference.png`、`vendor_combined_screening_reference.png` 和 `vendor_air_water_pair_reference.png` 是布局示意；厂商需要按示意制作/准备实物靶卡，使用待测相机拍摄后回传原始照片和采集参数。
