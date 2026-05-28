# AutoTestRunner 🏃‍♂️

`AutoTestRunner` 是专为智能硬件、嵌入式系统和 App UI 打造的**本地自动化测试执行框架**。

它可以作为 `AutoTestHub` (云端管控平台) 的本地执行引擎，也**完全支持作为独立的本地框架（离线模式）脱离云端使用**。

## 📁 目录结构
当前 `AutoTestRunner` 项目与云端 `AutoTestHub` 项目在文件系统上是完全物理隔离的（位于两个独立的文件夹中），确保它是一个纯粹的、可独立分发的本地 SDK。

## 📦 安装
```bash
# 进入项目目录安装
pip install -e .
```

## 🛠️ 核心特性
1. **Try-Except-Finally 硬件安全执行引擎**：保证测试崩溃时，设备的继电器电源、串口锁等硬件资源能被安全释放。
2. **双模运行 (Dual-Mode)**：
   - **离线模式 (Standalone)**：完全在本地执行，生成本地 HTML 测试报告。
   - **协同模式 (Connected)**：与云端 `AutoTestHub` 打通，实现用例大盘同步与执行结果上报。

---

## 📖 使用指南

### 1. 编写本地测试用例
使用提供的 `@autotest` 装饰器对 `pytest` 函数进行打标。打标主要用于云端同步，**完全不影响离线本地执行**。

```python
# 文件: tests/test_hardware.py
from autotest_runner import autotest

@autotest(case_id="TC-001", title="测试智能插座继电器通断", priority="P0")
def test_relay_power_cycle():
    print("正在发送指令关闭继电器...")
    assert True
```

### 2. 离线模式执行 (Standalone)
**无需配置任何云端地址，直接在本地执行！**
```bash
autotest-runner run examples/
```
**执行效果**：
- 自动触发安全执行引擎 (SafeExecutionPlugin)。
- 捕获测试过程中的 `AssertionError` (业务 Bug) 和其他环境异常。
- 自动在当前目录生成单机版测试报告：`local_report.html`。

### 3. 云端协同模式执行 (Connected)

#### A. 代码元数据同步 (Sync Up)
如果你需要让团队负责人在云端大盘看到你写的自动化用例进度，可以执行 Sync 命令：
```bash
autotest-runner sync examples/ --hub-url=https://your-hub.com --token=YOUR_TOKEN
```
*这会自动解析你的 Python 脚本中的 `@autotest` 装饰器，并将用例标题、优先级推送到云端展示（只读）。*

#### B. 在线执行与结果上报 (Report Up)
在本地插着硬件跑测试，但希望结果能推送到云端：
```bash
autotest-runner run examples/ --hub-url=https://your-hub.com --token=YOUR_TOKEN
```
*这会在生成本地 `local_report.html` 的同时，静默将通过/失败状态、本地收集的截图/串口日志上传给云端。*

---

## 🤖 AI 辅助编写
在本地，你可以使用 IDE 的 AI 助手插件（如 GitHub Copilot / Cursor）直接生成带 `@autotest` 装饰器的 pytest 代码。云端也支持直接向开发者下发 AI 生成的伪代码骨架。
