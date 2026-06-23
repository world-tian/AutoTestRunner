# AutoTestRunner 🏃‍♂️

`AutoTestRunner` 是专为智能硬件、嵌入式系统和 App UI 打造的**本地自动化测试执行框架**。

它可以作为 `AutoTestHub` (云端管控平台) 的本地执行引擎，也**完全支持作为独立的本地框架（离线模式）脱离云端使用**。

## 📦 安装
```bash
pip install -e .
```

## 🛠️ 核心特性
1. **Try-Except-Finally 硬件安全执行引擎**：保证测试崩溃时，设备锁等资源能被安全释放。
2. **内置硬件测试工具箱 (Toolbox)**：开箱即用的 `ADBTool`, `SerialTool`, `RelayTool`（继电器控制），以及新集成的 `U2Tool`（基于 uiautomator2 的安卓 UI 自动化）。
3. **YAML 测试计划驱动 (Test Plan)**：支持通过配置文件圈定测试范围、注入环境变量。
4. **双模运行 (Dual-Mode)**：离线模式生成本地 HTML 报告；协同模式可将结果上报云端。
5. **硬件执行生命周期管理**：支持串口持续日志采集、串口失败关键字检测、ADB 失败附件采集、失败保留现场、用例间清理和日志打包。

## 📖 使用指南

### 1. 编写测试用例 (使用内置工具)
```python
import os
from autotest_runner import autotest
from autotest_runner.tools import RelayTool, U2Tool

@autotest(case_id="TC-001", title="继电器测试", priority="P0")
def test_relay():
    # 框架支持从 yaml 中读取并自动注入环境变量
    relay = RelayTool(ip_address=os.getenv("DEVICE_IP"))
    relay.restart(port=1)

@autotest(case_id="TC-002", title="安卓 UI 自动化测试", priority="P0")
def test_android_ui():
    # 使用集成的 uiautomator2 工具
    u2 = U2Tool()
    u2.app_start("com.android.settings")
    u2.screenshot("settings.jpg")
```

### 2. 编写测试计划 (plan.yaml)
```yaml
name: "V1.0 回归测试计划"
targets:
  - "examples/test_hardware.py"
env:
  DEVICE_IP: "192.168.1.100"

execution:
  continue_on_fail: true           # 单条失败后是否继续执行后续用例
  keep_on_fail: false              # 失败后是否保留现场并终止
  keep_on_fail_timeout_sec: 0      # 0 表示一直等待人工介入
  cleanup_between_cases: true      # 用例间是否执行恢复动作

serial:
  enabled: false                   # 用户配置为 true 才会打开串口
  port: "/dev/ttyUSB0"
  baudrate: 115200
  log: true
  fail_patterns:
    - "ERROR"
    - "ASSERT"
    - "HardFault"
    - "panic"
  timeout_sec: 10

adb:
  enabled: false                   # 用户配置为 true 才会执行 ADB 采集
  device_id: ""
  clear_logcat_before_case: true
  collect_on_fail:
    logcat: true
    bugreport: false
    screenshot: true
    pull_paths:
      - "/sdcard/Android/data/com.demo/files/logs"

cleanup:
  enabled: false
  actions:
    - type: adb
      command: ["shell", "logcat", "-c"]

artifacts:
  output_dir: "reports/artifacts"
  zip_logs: true
```

### 3. 执行测试计划
```bash
# 基于 YAML 测试计划执行
# 使用 python -m 模块方式直接启动（支持 -plan 或 --plan）
python3 -m autotest_runner run -plan examples/plan.yaml
```

执行时框架会自动挂载 pytest 生命周期插件：

- 用例开始前记录串口日志偏移，按需清理 logcat。
- 用例失败时采集串口片段、ADB logcat、截图、bugreport 和用户配置的 pull 路径。
- 串口日志命中 `fail_patterns` 时，即使 Python 断言通过，也会将当前用例标记为失败。
- `keep_on_fail=true` 时，失败后跳过 cleanup，保留现场并终止后续用例。
- `cleanup_between_cases=true` 时，正常执行用例间恢复动作，降低对下一条用例的影响。
- 整批结束后在 `reports/artifacts` 下生成用例级日志目录和 zip 包。

### 4. 云端协同同步
```bash
# 将代码元数据同步到云端
python3 -m autotest_runner sync examples/ --hub-url=https://hub.local --token=XXX
```

## 🏗️ 项目脚手架 (目录与用例管理)
测试用例写在哪？报告存哪？不需要自己从头建！框架提供了标准的工程脚手架。

```bash
python3 -m autotest_runner init my_project
```
执行后会生成如下标准结构：
```text
my_project/
├── testcases/         # 存放所有的自动化用例代码
│   ├── network/       # 可以按模块自由创建子文件夹
│   │   └── test_online.py
│   ├── power/
│   └── conftest.py    # 全局配置与 Fixtures
├── plans/             # 存放所有的 YAML 测试计划
│   └── smoke_plan.yaml
├── reports/           # 每次执行自动生成的本地 HTML 报告存放于此
└── logs/              # 硬件执行的串口/系统日志存放于此
```
**云端映射机制**：当你执行 `python3 -m autotest_runner sync testcases/` 时，本地 `testcases` 下的文件夹层级（如 `network`）会自动映射为云端 `AutoTestHub` 中的**模块树 (Module Tree)**，保证云端与本地的结构完全一致！
