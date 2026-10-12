# 厂商镜头标定拍摄靶图交付包

本目录中的 PNG 是布局和采集示意，供厂商制作或准备对应实物靶卡。不得把示意 PNG 直接作为相机实拍输入，也不得把它当作已校准的 ColorChecker、ISO12233 或几何标定板。

| 编号 | 文件 | 对应工站/场景 | 实际要验证的参数 | 厂商必须回传 |
|---|---|---|---|---|
| TARGET-SHD | `vendor_flat_field_reference.png` | OTP/LSC 均匀场 | 中心/边缘差、四角差、9x9 Y、R/G、B/G | 均匀灰/白场实拍图、照度、色温、曝光、Gain、WB状态 |
| TARGET-AWB | `vendor_neutral_gray_reference.png` | OTP/AWB 中性灰 | RGB均值、R/G、B/G、中性误差 | 中性灰卡实拍图、光源型号、色温、照度、WB收敛状态 |
| TARGET-SFR | `vendor_slanted_edge_reference.png` | AA组装/SFR | 中心/四角清晰度、3x3、Tenengrad、MTF代理 | 完整SFR/ISO12233实拍图、距离、倾角、对焦、曝光、MTF报告 |
| TARGET-GEO | `vendor_geometry_grid_reference.png` | 模组标定/几何 | 畸变、LCA、光轴中心、透视误差 | 已知格距棋盘格/网格实拍图、角点、内参/畸变模型和残差 |
| TARGET-OPTICS | `vendor_combined_screening_reference.png` | 光学联合筛查 | 同一装配状态下的清晰度和几何代理 | 综合靶实拍图；正式MTF和几何标定仍需分别回传标准靶图 |
| TARGET-UW | `vendor_air_water_pair_reference.png` | 全检/水下 | 空气-水下清晰度、FOV、畸变、AWB、对比度、散射 | 同一靶卡空气图+水下图、连续帧、水深、窗口和光源记录 |

## 回传命名

```text
<vendor>_<module>_<target>_<air|water>_<lux>_<kelvin>_<fw>_<isp>_<yyyymmdd>_<seq>.jpg
```

示例：

```text
vendorA_lens_TARGET-SFR_air_350lux_6500K_fw120_isp08_20260914_001.jpg
vendorA_lens_TARGET-UW_water_200lux_6500K_fw120_isp08_20260914_001.jpg
```

## 共同采集要求

- 使用待测模组、镜头、AA/光学窗口和最终固件/ISP版本。
- 记录工站、设备序列号、图卡型号、图卡物理尺寸、距离、角度、光源色温、照度、曝光、模拟/数字Gain和WB状态。
- 原始文件不得裁剪、缩放、二次压缩或套用美化算法。
- 同一空气/水下配对必须保持同一设备、同一图卡、同一距离和构图。
- 图片回传同时附带采集参数 CSV/JSON 和厂商正式标定结果。
