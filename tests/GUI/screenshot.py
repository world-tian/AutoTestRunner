import os
import time
import subprocess
from pathlib import Path

def test_mac_screenshot():
    """
    测试 Mac 本地截图功能
    """
    # 获取桌面路径和截图文件路径
    desktop_path = Path.home() / "Desktop"
    screenshot_path = desktop_path / "screen.png"
    
    # 1. 每次用例执行前判断 desktop 是否有该截图文件，有的话则删除
    if screenshot_path.exists():
        print(f"发现历史截图文件，正在删除: {screenshot_path}")
        screenshot_path.unlink()
        
    # 断言确认文件已被清理
    assert not screenshot_path.exists(), "前置清理失败：无法删除已存在的截图文件"

    # 2. 通过 mac 的本地终端下发指令并执行 screencapture
    # 注意：直接使用绝对路径以防 ~ 解析问题
    cmd = f"screencapture {screenshot_path}"
    print(f"正在下发截图指令: {cmd}")
    
    try:
        # 执行终端命令
        result = subprocess.run(
            cmd, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True, 
            timeout=10
        )
    except subprocess.CalledProcessError as e:
        assert False, f"截图指令执行失败，错误码: {e.returncode}, 错误信息: {e.stderr}"
    except subprocess.TimeoutExpired:
        assert False, "截图指令执行超时"
        
    # 等待一小段时间，确保文件系统完成写入
    time.sleep(1)
    
    # 3. 如果桌面有保存的 screen.png 则成功，否则失败
    if screenshot_path.exists():
        print(f"测试成功！截图已保存至: {screenshot_path}")
        # 确保生成的文件大小不为 0
        assert screenshot_path.stat().st_size > 0, "测试失败：生成的截图文件大小为 0"
    else:
        assert False, "测试失败：未在桌面找到 screen.png 截图文件"

if __name__ == "__main__":
    test_mac_screenshot()