# 相机方案：10 大类、59 条用例（P0/P1）

<!-- CAMERA_CASE_COUNTS_START -->
- `testcases`（60条）
- `testcases/camera`（60条）
- `testcases/camera/ae`（8条）
- `testcases/camera/awb`（6条）
- `testcases/camera/defect`（7条）
- `testcases/camera/geometry`（4条）
- `testcases/camera/noise`（5条）
- `testcases/camera/output`（7条）
- `testcases/camera/regression`（3条）
- `testcases/camera/shading`（4条）
- `testcases/camera/sharpness`（11条）
- `testcases/camera/underwater`（5条）
- `testcases/camera/ae/P0`（3条）
- `testcases/camera/ae/P1`（5条）
- `testcases/camera/awb/P0`（2条）
- `testcases/camera/awb/P1`（4条）
- `testcases/camera/defect/P0`（1条）
- `testcases/camera/defect/P1`（6条）
- `testcases/camera/geometry/P1`（4条）
- `testcases/camera/noise/P1`（5条）
- `testcases/camera/output/P0`（3条）
- `testcases/camera/output/P1`（4条）
- `testcases/camera/regression/P1`（3条）
- `testcases/camera/shading/P0`（2条）
- `testcases/camera/shading/P1`（2条）
- `testcases/camera/sharpness/P0`（4条）
- `testcases/camera/sharpness/P1`（7条）
- `testcases/camera/underwater/P1`（5条）
- `testcases/camera/ae/P0/test-ae-average_brightness`（1条）
- `testcases/camera/ae/P0/test-ae-overexposure_ratio`（1条）
- `testcases/camera/ae/P0/test-ae-underexposure_ratio`（1条）
- `testcases/camera/ae/P1/test-ae-effective_dynamic_range`（1条）
- `testcases/camera/ae/P1/test-ae-histogram_entropy`（1条）
- `testcases/camera/ae/P1/test-ae-histogram_percentile`（1条）
- `testcases/camera/ae/P1/test-ae-image_contrast`（1条）
- `testcases/camera/ae/P1/test-ae-median_brightness`（1条）
- `testcases/camera/awb/P0/test-awb-color_cast`（1条）
- `testcases/camera/awb/P0/test-awb-rgb_channel_statistics`（1条）
- `testcases/camera/awb/P1/test-awb-blue_green_ratio`（1条）
- `testcases/camera/awb/P1/test-awb-colorchecker_delta_e`（1条）
- `testcases/camera/awb/P1/test-awb-neutral_error`（1条）
- `testcases/camera/awb/P1/test-awb-red_green_ratio`（1条）
- `testcases/camera/defect/P0/test-defect-large_color_block`（1条）
- `testcases/camera/defect/P1/test-defect-dead_pixel`（1条）
- `testcases/camera/defect/P1/test-defect-duplicate_frame`（1条）
- `testcases/camera/defect/P1/test-defect-frame_corruption`（1条）
- `testcases/camera/defect/P1/test-defect-horizontal_banding`（1条）
- `testcases/camera/defect/P1/test-defect-hot_pixel`（1条）
- `testcases/camera/defect/P1/test-defect-vertical_banding`（1条）
- `testcases/camera/geometry/P1/test-geometry-lateral_chromatic_aberration`（1条）
- `testcases/camera/geometry/P1/test-geometry-lens_distortion`（1条）
- `testcases/camera/geometry/P1/test-geometry-optical_center_offset`（1条）
- `testcases/camera/geometry/P1/test-geometry-perspective_error`（1条）
- `testcases/camera/noise/P1/test-noise-chroma_noise`（1条）
- `testcases/camera/noise/P1/test-noise-dark_frame_noise`（1条）
- `testcases/camera/noise/P1/test-noise-luma_noise`（1条）
- `testcases/camera/noise/P1/test-noise-signal_to_noise_ratio`（1条）
- `testcases/camera/noise/P1/test-noise-temporal_noise`（1条）
- `testcases/camera/output/P0/test-output-abnormal_frame`（1条）
- `testcases/camera/output/P0/test-output-image_parse`（1条）
- `testcases/camera/output/P0/test-output-output_resolution`（1条）
- `testcases/camera/output/P1/test-output-bit_depth_channel`（1条）
- `testcases/camera/output/P1/test-output-duplicate_frame`（1条）
- `testcases/camera/output/P1/test-output-exif_orientation`（1条）
- `testcases/camera/output/P1/test-output-jpeg_compression`（1条）
- `testcases/camera/regression/P1/test-regression-firmware_metrics`（1条）
- `testcases/camera/regression/P1/test-regression-golden_sample`（1条）
- `testcases/camera/regression/P1/test-regression-isp_metrics`（1条）
- `testcases/camera/shading/P0/test-shading-center_edge_brightness`（1条）
- `testcases/camera/shading/P0/test-shading-corner_brightness_consistency`（1条）
- `testcases/camera/shading/P1/test-shading-color_9x9_heatmap`（1条）
- `testcases/camera/shading/P1/test-shading-luma_9x9_heatmap`（1条）
- `testcases/camera/sharpness/P0/test-sharpness-center_corner_consistency`（1条）
- `testcases/camera/sharpness/P0/test-sharpness-center_sharpness`（1条）
- `testcases/camera/sharpness/P0/test-sharpness-corner_sharpness`（1条）
- `testcases/camera/sharpness/P0/test-sharpness-global_sharpness`（1条）
- `testcases/camera/sharpness/P1/test-sharpness-corner_center_mtf_ratio`（1条）
- `testcases/camera/sharpness/P1/test-sharpness-mtf20`（1条）
- `testcases/camera/sharpness/P1/test-sharpness-mtf50`（1条）
- `testcases/camera/sharpness/P1/test-sharpness-roi_3x3_heatmap`（1条）
- `testcases/camera/sharpness/P1/test-sharpness-siemens_star_mtf`（1条）
- `testcases/camera/sharpness/P1/test-sharpness-slanted_edge_sfr`（1条）
- `testcases/camera/sharpness/P1/test-sharpness-tenengrad`（1条）
- `testcases/camera/underwater/P1/test-underwater-awb`（1条）
- `testcases/camera/underwater/P1/test-underwater-backscatter`（1条）
- `testcases/camera/underwater/P1/test-underwater-contrast_loss`（1条）
- `testcases/camera/underwater/P1/test-underwater-fov_distortion`（1条）
- `testcases/camera/underwater/P1/test-underwater-sharpness_change`（1条）
<!-- CAMERA_CASE_COUNTS_END -->

## 命名规范

用例目录和脚本统一使用 `test-模块-测试功能项`；目录层级统一为 `testcases/camera/<模块>/<优先级>/test-<模块>-<功能>`，例如 `testcases/camera/ae/P0/test-ae-average_brightness` 和 `testcases/camera/sharpness/P1/test-sharpness-roi_3x3_heatmap`。同一功能的重复场景追加 `-001`、`-002`。
编号 `CAM-AE-001` 等是平台统计用例编号，文件名负责表达功能；两者都必须保持稳定，不再使用 `case1`、`case2`。
`__pycache__` 是 Python 运行时字节码缓存，不属于用例资产；Runner 已通过 `PYTHONDONTWRITEBYTECODE=1` 禁止生成，相机目录的 `conftest.py` 也会在直接 pytest 时关闭写入。若 IDE 已显示旧缓存，可删除一次；Runner 不依赖它。

## 用例文案规范

用例生成时必须一次性写入脚本 `@autotest` 元数据和 `catalog.json`：`test_class` 是测试大类，`description` 是面向报告的中文描述并包含实际阈值，`expected_result` 是判定规则原文，`parameters` 保存结构化参数。报告只读取这些静态元数据，执行阶段只输出实测值和判定结果，不调用 AI 补写描述。其他模块沿用同一字段规范。

图片由设备/采集程序提前拍摄。本套件分析本地图片，不控制相机拍摄，也不假定一个场景适用于所有指标。
原始检测图片放在 `testcases/camera/images/`。当前已放入一张公开测试图片 `camera_test.jpg` 作为流程验证样本，配置只需填写 `images.default`；真实设备图片可替换它。图片需要由实际设备或测试数据源采集，不由框架伪造。

| 测试大类 | 目录 | 用例编号 | 数量 |
|---|---|---|---|
| 基础图像 / Output | output/P0、output/P1/test-output-* | CAM-IMG-001..005 | 5 |
| 曝光 / AE | ae/P0、ae/P1/test-ae-* | CAM-AE-001..003、CAM-AE-005..009 | 8 |
| 清晰度 / Sharpness | sharpness/P0、sharpness/P1/test-sharpness-* | CAM-SHP-001..010 | 10 |
| 白平衡 / AWB & Color | awb/P0、awb/P1/test-awb-* | CAM-COLOR-001..006 | 6 |
| 亮度均匀性 / LSC & Shading | shading/P0、shading/P1/test-shading-* | CAM-SHD-001..004 | 4 |
| 异常检测 / Defect | defect/P0、defect/P1/test-defect-* | CAM-DEFECT-004..010 | 7 |
| 噪声与信噪比 / Noise & SNR | noise/P1/test-noise-* | CAM-NOISE-001..005 | 5 |
| 几何 / Geometry | geometry/P1/test-geometry-* | CAM-GEO-001..004 | 4 |
| 水下画质 / Underwater IQ | underwater/P1/test-underwater-* | CAM-UW-001..005 | 5 |
| 版本回归 / Regression | regression/P1/test-regression-* | CAM-REG-001..003 | 3 |

## 本地运行（在 autotestrunner 根目录）

如果当前终端位于工作区根目录 `D:\dev\testcode`，也可以直接使用带 `autotestrunner/` 前缀的路径：

```powershell
python -m autotest_runner run --plan autotestrunner/plans/camera_smoke.yaml --picture autotestrunner/testcases/camera/images/valid_texture.png
```

Runner 会自动定位 `autotestrunner/testcases` 下的 catalog；如果环境变量中配置了 `AUTOTEST_PROJECT_ID`，命令会先同步用例到 AutoTestHub。

```powershell
python -m pip install -e .
Copy-Item testcases/camera/config.example.json testcases/camera/config.local.json
# 编辑 config.local.json：填写产品实际 expected_size 和图片路径；不要在这里配置阈值。
python -m autotest_runner run --plan plans/camera.yaml
# 也可以单独运行大类或单条：
$env:CAMERA_CONFIG = (Resolve-Path testcases/camera/config.local.json).Path
python -m autotest_runner run testcases/camera/awb/P0
python -m autotest_runner run testcases/camera/awb/P0/test-awb-rgb_channel_statistics

# 单次覆盖配置中的图片；可传具体文件或目录。
python -m autotest_runner run testcases/camera/awb/P0 -pic D:/data/camera/awb.jpg
python -m autotest_runner run --plan plans/camera.yaml -pic D:/data/camera
```

如果当前终端位于工作区根目录 `D:\dev\testcode`，先执行 `Set-Location autotestrunner`；否则相对的 `plans/`、`testcases/` 和 `reports/` 路径会指向错误位置。若环境变量设置了 `AUTOTEST_PROJECT_ID`，Runner 会先同步 catalog；本地只执行不需要同步时可执行 `Remove-Item Env:AUTOTEST_PROJECT_ID,Env:AUTOTEST_HUB_URL,Env:AUTOTEST_HUB_TOKEN -ErrorAction SilentlyContinue`。

### 可直接执行的计划

以下计划均从 `autotestrunner` 根目录执行；`--picture` 会临时覆盖 `config.json` 中的默认图片。相对路径优先按 Runner 当前目录解析，也支持绝对路径。

| 计划 | 覆盖范围 | 用途 |
|---|---|---|
| `plans/camera_smoke.yaml` | 5 条代表用例 | 快速冒烟，确认输出、曝光、清晰度、颜色和缺陷链路 |
| `plans/camera_p0.yaml` | 全部 15 条 P0 | 基础质量门禁 |
| `plans/camera_sharpness.yaml` | SHP-001..005 | 清晰度专项，包含 P1 的 3×3 热力图 |
| `plans/camera_shading.yaml` | SHD-001..004 | LSC/Shading专项，默认使用均匀灰场 |
| `plans/camera.yaml` | 当前全部 59 条 | 完整相机回归 |

### 厂商镜头标定验证计划

针对镜头标定厂商效果，建议按质量域单独执行，避免把不适用的输入混在同一门禁中：

| 厂商验证计划 | 用例范围 | 默认/要求输入 | 主要验证内容 |
|---|---|---|---|
| `plans/camera_vendor_shading.yaml` | SHD-001..004 | 默认使用 `valid_uniform_gray.png` 流程图；正式验收用 `--picture` 覆盖为设备实拍均匀灰/白场 | LSC中心/边缘、四角、9×9亮度和颜色均匀性代理 |
| `plans/camera_vendor_awb_color.yaml` | COLOR-001..005 | 必须提供设备实拍中性灰卡；006 色差代理不纳入 | AWB通道、R/G、B/G、中性误差；无真实 ΔE2000 |
| `plans/camera_vendor_mtf.yaml` | SHP-010 | 必须提供设备实拍旧式 ISO/CIPA 图卡；计划默认标注两颗 36 周期西门子星，可用 `--sfr-stars` 覆盖 | 西门子星径向调制度 MTF50 主值、MTF20 辅助值；输出 cycles/pixel，不冒充 ISO 12233 eSFR 正式值 |
| `plans/camera_vendor_geometry.yaml` | GEO-001..004 | 必须提供设备实拍且尺寸已知的网格/棋盘格 | 几何代理；尚未计算内参、畸变系数或拟合残差 |
| `plans/camera_vendor_lens_optics.yaml` | SHP-001..009 + GEO-001..004 | 必须提供同时包含斜边和标定网格的设备实拍靶图 | 联合执行清晰度和几何代理；两类指标独立判定 |
| `plans/camera_vendor_underwater.yaml` | UW-001..005 | 必须准备同一测试卡的空气/水下配对图和连续帧 | 水下清晰度、FOV/畸变、AWB、对比度、散射 |

执行示例：

```powershell
python -m autotest_runner run --plan plans/camera_vendor_shading.yaml --picture <实拍均匀场图>
python -m autotest_runner run --plan plans/camera_vendor_awb_color.yaml --picture <实拍中性灰卡图>
python -m autotest_runner run --plan plans/camera_vendor_mtf.yaml --picture <实拍图卡照片>
# 手机裁剪/透视明显时，用实际标注覆盖默认 ROI；x/y/radius 均为归一化坐标。
python -m autotest_runner run --plan plans/camera_vendor_mtf.yaml --picture <实拍图卡照片> --sfr-stars '[{"name":"left_mid","x":0.35,"y":0.39,"radius":0.05,"cycles":36}]'
python -m autotest_runner run --plan plans/camera_vendor_geometry.yaml --picture <实拍已知尺寸网格图>
python -m autotest_runner run --plan plans/camera_vendor_lens_optics.yaml --picture <实拍斜边加网格综合图>
python -m autotest_runner run --plan plans/camera_vendor_underwater.yaml --allow-failures
```

SHP-001..009 仍是原有清晰度/MTF 代理；SHP-010 使用手工标注的西门子星做频域试验，结果用于比较手机实拍的失焦、抖动和区域差异。它不包含透视校正、标准 eSFR 九区自动定位、OECF 或物理图卡反射率标定，因此不能作为 ISO 12233 正式验收报告。正式 eSFR 仍应使用低对比度标准斜边卡，并在固定距离、光照、曝光、增益、白平衡和锐化策略下，用 Golden/Bad 样本建立产品阈值。

图片资产：`valid_uniform_gray.png` 是纯灰算法流程图；`vendor_composite_test_chart.png` 和 `vendor_sfr_geometry_chart.png` 是程序生成的灰度棋盘格，既不是实拍图，也不具备 ColorChecker 标准色块或合格斜边。厂商专项 plan 不再默认使用这些图。正式验收还必须记录光源色温、照度、距离、镜头状态、空气/水下介质、固件/ISP版本和基线文件。

联合光学的拍摄布局参考图位于 `testcases/camera/images/reference/`，分别给出均匀场、中性灰卡、中心/四角斜边、已知格距棋盘格和空气/水下配对构图。它们是示意图，不是 Runner 输入；拍摄条件和实物靶卡要求见该目录的 README 及飞书方案 8.1。

示例命令：

```powershell
python -m autotest_runner run --plan plans/camera_smoke.yaml --picture testcases/camera/images/valid_texture.png
python -m autotest_runner run --plan plans/camera_p0.yaml --picture testcases/camera/images/invalid_all_black.png
python -m autotest_runner run --plan plans/camera_shading.yaml
python -m autotest_runner run --plan plans/camera.yaml --picture testcases/camera/images/invalid_color_cast.png
```

完整计划使用单张验证图时，部分多帧、暗场、水下或版本基线用例可能因输入不适用而失败；严格门禁应保留默认退出码1。仅做探索性检查、希望 PowerShell 不因这些报告失败弹出退出代码1时，可显式增加 `--allow-failures`：

```powershell
python -m autotest_runner run --plan plans/camera.yaml --picture testcases/camera/images/valid_texture.png --allow-failures
```

该选项只改变命令退出码，不隐藏失败用例；HTML、JUnit 和 `reports/camera` 证据仍保留真实失败结果。

### 58条实现验收状态

当前4.1规划的58条用例均已生成脚本、元数据、catalog、plan和算法回归入口。使用单张 `valid_texture.png` 执行完整计划的结果为 `44 passed / 14 failed`：失败项集中在多帧冻结/时域噪声、JPEG专用输入、暗场/均匀场、几何标定、水下空气配对和版本/Golden基线缺失，脚本会保存证据并明确说明前置条件，不将不适用输入伪报为产品通过。MTF、DeltaE、几何和水下项目当前是可执行基础代理，正式验收仍需标准测试卡、标定模型和真实采集条件。

### 本地验证图片

这些图片是算法链路验证样本，不是相机实拍，也不能用于产品验收。`valid_texture.png` 用于大多数基础用例通过验证；`invalid_all_black.png`、`invalid_all_white.png`、`invalid_color_cast.png`、`invalid_shading_gradient.png` 和 `invalid_blur.png` 分别用于验证全黑、全白、偏色、均匀性异常和失焦场景。完整相机质量验证仍应替换为真实设备输出，并按场景配置阈值。

图片位置：`testcases/camera/images/valid_texture.png`、`invalid_all_black.png`、`invalid_all_white.png`、`invalid_color_cast.png`、`invalid_shading_gradient.png`、`invalid_blur.png`。

厂商标定靶图交付包位于 `testcases/camera/images/reference/`，详细清单见 `vendor_target_package.md`。其中的 PNG 是布局示意，不是可直接作为相机输入的校准靶卡；厂商应按示意准备实物靶卡，完成标定后用待测相机拍摄并回传原始照片、采集参数和正式标定报告。

LSC/Shading 专项默认图片为 `testcases/camera/images/valid_uniform_gray.png`。这是一张均匀灰场流程验证图，适合验证中心/边缘、四角和9×9代理指标；正式产品验收仍需积分球或均匀背光板采集的真实平场图片。

### VS Code 中的 `camera_case` 波浪线

`camera_case` 来自 `src/autotest_runner/camera/execution.py`，这是 `src` 布局下的包导入，不是相机用例目录中的本地文件。Runner 已通过可编辑安装和 `python.analysis.extraPaths` 配置解析该包；可用 `python -c "from autotest_runner.camera.execution import camera_case; print(camera_case.__module__)"` 验证导入。若编辑器仍显示旧波浪线，选择 Runner 使用的 Python 解释器后执行 `Python: Restart Language Server`。Pylance 对 `check()` 中未使用的 `expected_size` 参数可能给出提示，该参数是统一用例接口保留参数，不代表 `camera_case` 引用失败。

图片路径相对于配置 JSON 所在目录；expected_size 是 EXIF 方向修正后的 `[宽, 高]`。未设置 `CAMERA_CONFIG` 时，Runner 会自动查找当前目录或安装目录下的 `testcases/camera/config.json`；需要切换多套配置时，再复制为 `config.local.json` 并通过 `CAMERA_CONFIG` 指定。
缺配置、缺图片、损坏图片均报错/失败，不会跳过或自动生成“通过”图片。
HTML 报告位于 `reports/local`；每条指标 JSON 位于 `reports/camera`，可用 `CAMERA_RESULTS_DIR` 指定保存目录。
JSON 包含输入路径、配置、通用/专用阈值、实测结果和判定；失败同样保存证据。

## 场景与阈值

### 自动统计用例数量

新增或移动用例后，在 `autotestrunner` 根目录执行下面命令，自动统计 `testcases`、`camera`、模块和 P0/P1/P2/P3 数量，并更新本 README 的统计区间：

```powershell
python testcases/camera/count_cases.py --update-readme
```

阈值现在分两层：`common.json` 只放被多个用例复用的 `mean_min`、`sharpness_min`、`channel_min`；各用例脚本中的 `CASE_LIMITS` 只放该用例特有参数，紧邻 `check()` 判定函数。`config.json` 只管理图片、输出规格和报告信息。要调整某条判定时直接打开对应脚本，例如 `output/P0/test-output-abnormal_frame/test_output_abnormal_frame.py`；它的 `CASE_LIMITS` 包含 `extreme_max` 和 `std_min`，并有逐项中文备注。配置的优先顺序是 `common.json` 中的共享值和该脚本中的专用值，二者不能重名。

每条用例的正文按固定顺序执行：`camera_case(...)` 准备真实图片和生效阈值；显式调用 `camera.metrics` 中对应的小指标函数；显式调用本脚本的 `check(metrics, limits, expected_size)`；`run.record(...)` 写入实测值和结果；失败时由脚本自己的 `raise AssertionError(...)` 抛出。`camera_case` 从 `@autotest` 元数据读取用例编号并保证失败证据落盘，不负责业务判定。`metrics.py` 的 `measure()` 仅供算法回归和离线分析聚合使用，实际用例只计算对应领域的指标。
现有脚本的 `@autotest` 中文说明保留开发默认数值，作为静态目录描述；如果修改共享或专用阈值，也要同步修改对应脚本中的 `description` / `parameters`。执行时以 `common.json` 和 `CASE_LIMITS` 的实际值判定，证据 JSON 会保存最终生效阈值。

- Output：正常曝光的纹理场景，纯灰图可能被低方差检查判为异常。
- AE：固定照明和构图的标准曝光场景。
- Sharpness：全幅重复纹理图卡，中心/四角须有相同纹理；固定距离、分辨率、锐化设置。
- AWB：均匀照明中性灰卡，等待白平衡稳定。
- Shading：均匀平场或积分球，锁定曝光。
- Defect：中性均匀场；当前检测大块局部色度异常，不覆盖所有花屏、条纹或坏点。

默认值仅为开发起点，不是产品验收规格。应使用合格/不合格样本按场景标定，并将配置纳入版本管理。
亮度为8-bit RGB加权值（0.299R+0.587G+0.114B），不是线性光强；暗像素 Y≤10、亮像素 Y≥245。

| 参数 | 所在位置 | 默认值 | 含义 |
|---|---|---|---|
| mean_min / sharpness_min / channel_min | `common.json` | 60 / 80 / 10 | 多条用例共享的亮度、清晰度和通道下限 |
| mean_max / under_max / over_max | 各 AE 用例的 `CASE_LIMITS` | 200 / 0.15 / 0.15 | 平均亮度上限、欠曝/过曝比例上限 |
| extreme_max / std_min | 异常帧用例的 `CASE_LIMITS` | 0.98 / 1 | 极暗/极亮比例上限与亮度标准差下限 |
| sharpness_ratio_min | 清晰度一致性用例的 `CASE_LIMITS` | 0.4 | 五区最小/最大清晰度比下限 |
| channel_max / color_cast_max | 各 AWB 用例的 `CASE_LIMITS` | 245 / 0.15 | 通道上限与偏色比例上限 |
| center_edge_max / corner_delta_max | 各 Shading 用例的 `CASE_LIMITS` | 0.3 / 0.2 | 中心/边缘和四角相对亮度差上限 |
| chroma_tile_max | 异常色块用例的 `CASE_LIMITS` | 25 | 8×8 网格色度异常块上限 |

## 同步与网页查看

```powershell
python -m autotest_runner sync testcases --hub-url http://localhost:8000 --project-id <项目ID>
# 有鉴权的部署另加 --token <令牌>。
```

Hub 后端需更新代码并重启（启动时自动补充元数据字段），前端需重新构建。
网页“用例管理”选择目标项目，筛选“相机 / camera（全部大类）”，或树视图展开“相机 / camera”。
列表展示测试大类、描述、优先级；点击查看图标或树叶可见前置条件、步骤、预期和脚本。
同步按项目+用例编号更新，重复同步不重复建例，不改变既有采纳/启用状态。
`script_path` 相对于 sync 命令传入的根目录（建议一直传 `testcases`）。
同步只读取 `catalog.json`，不导入/执行脚本；没有清单会明确失败，不再虚报同步成功。

## 维护与扩展

`build_catalog.py` 维护当前59条的目录清单；运行时仅更新 `catalog.json`，不会覆盖人工维护的脚本或阈值。
公共图像解码和基础指标放 `src/autotest_runner/camera/metrics.py`；每条用例的业务判定与专用阈值保留在自己的脚本中。
新增业务用例时扩展 ROWS/GROUPS、单独创建脚本的 `CASE_LIMITS` 与 `check()`，并增加算法回归测试；保持已有编号不变。
第一版功能分类数量可用于统计用例分布，不能把15条通过当成所有相机功能覆盖率100%。
二阶段已加入 ColorChecker/ΔE、MTF50/MTF20、9×9 Heatmap、Hot/Dead Pixel/Banding、Distortion/LCA、Noise、Underwater 和 Regression 的可执行基础代理；SHP-010 另提供旧式西门子星的实验性 MTF 输出。
这些结果不替代正式标定：MTF/DeltaE/几何需要标准测试卡和标定模型；冻结、时域噪声、水下配对和版本回归必须配置多帧目录或基线，否则证据中明确记录 N/A 语义并失败，不伪报 PASS。

## 计划与全局配置职责
计划文件只描述计划名称、targets 收集范围、cases 执行顺序和可选 picture_dir。模块从用例脚本的 feature/所在目录自动推导，新增模块无需修改 camera plan。case_catalog 是旧版目录索引兼容字段，不再必填；targets 是 pytest 收集路径，cases 决定收集后的执行顺序。优先级、报告筛选和证据目录属于模块 config.json 的全局默认值；阈值由 common.json 与各用例脚本管理。description_policy 不放在 plan 中，中文描述和判定参数保留在脚本元数据中。

补充：plan 可以省略 `targets`，Runner 会自动递归收集 `testcases/` 下的所有模块，因此同一个 plan 可混合 camera、network、display 等用例。图片归属用例：每条用例通过 `CAMERA_CONFIG` 的 `images.default` 或自身参数选择图片；多条用例复用同一图片时只配置一次即可，临时替换仍可使用 `-pic`。

## OpenCV 扩展

安装 runner 时会自动安装 `opencv-python-headless`。算法层提供 `opencv_available()` 和 `opencv_edges()` 基础接口，后续可在不改变现有 Pillow/NumPy 指标的前提下增加棋盘格定位、ColorChecker 识别、透视校正和 ROI 检测。
