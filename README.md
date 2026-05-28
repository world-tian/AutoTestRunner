# AutoTestRunner 🏃‍♂️

`AutoTestRunner` 是专为智能硬件、嵌入式系统和 App UI 打造的**本地自动化测试执行框架**。

它可以作为 `AutoTestHub` (云端管控平台) 的本地执行引擎，也**完全支持作为独立的本地框架（离线模式）脱离云端使用**。

## 📦 安装
```bash
pip install -e .
```

## 🛠️ 核心特性
1. **Try-Except-Finally 硬件安全执行引擎**：保证测试崩溃时，设备锁等资源能被安全释放。
2. **内置硬件测试工具箱 (Toolbox)**：开箱即用的 `ADBTool`, `SerialTool`, `RelayTool`（继电器控制）。
3. **YAML 测试计划驱动 (Test Plan)**：支持通过配置文件圈定测试范围、注入环境变量。
4. **双模运行 (Dual-Mode)**：离线模式生成本地 HTML 报告；协同模式可将结果上报云端。

## 📖 使用指南

### 1. 编写测试用例 (使用内置工具)
```python
import os
from autotest_runner import autotest
from autotest_runner.tools import RelayTool

@autotest(case_id="TC-001", title="继电器测试", priority="P0")
def test_relay():
    # 框架支持从 yaml 中读取并自动注入环境变量
    relay = RelayTool(ip_address=os.getenv("DEVICE_IP"))
    relay.restart(port=1)
```

### 2. 编写测试计划 (plan.yaml)
```yaml
name: "V1.0 回归测试计划"
targets:
  - "examples/test_hardware.py"
env:
  DEVICE_IP: "192.168.1.100"
```

### 3. 执行测试计划
```bash
# 基于 YAML 测试计划执行
autotest-runner run --plan examples/plan.yaml
```

### 4. 云端协同同步
```bash
# 将代码元数据同步到云端
autotest-runner sync examples/ --hub-url=https://hub.local --token=XXX
```

## 🏗️ 项目脚手架 (目录与用例管理)
测试用例写在哪？报告存哪？不需要自己从头建！框架提供了标准的工程脚手架。

```bash
autotest-runner init my_project
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
**云端映射机制**：当你执行 `autotest-runner sync testcases/` 时，本地 `testcases` 下的文件夹层级（如 `network`）会自动映射为云端 `AutoTestHub` 中的**模块树 (Module Tree)**，保证云端与本地的结构完全一致！
