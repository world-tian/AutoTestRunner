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
