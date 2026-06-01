import time
import subprocess
import pytest

def kill_photo_booth():
    """杀掉 Photo Booth 进程"""
    subprocess.run('killall "Photo Booth"', shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

@pytest.fixture(autouse=True)
def manage_camera_app():
    """pytest 专用的前置和后置操作：确保测试前后关闭应用"""
    kill_photo_booth()
    yield
    kill_photo_booth()

def test_mac_camera_open():
    """
    测试打开 Mac 摄像头应用 (Photo Booth)
    """
    # 兼容直接通过 python 执行时的前置清理
    kill_photo_booth()
    
    print("正在下发指令打开 Photo Booth 应用...")
    # 1. 打开摄像头应用
    try:
        subprocess.run('open -a "Photo Booth"', shell=True, check=True)
    except subprocess.CalledProcessError as e:
        assert False, f"执行 open -a 失败: {e}"
    
    # 给予应用启动及初始化时间
    time.sleep(5)
    
    print("检查 Photo Booth 进程是否存在...")
    # 2. 检查是否有这个进程
    result = subprocess.run('pgrep -f "Photo Booth"', shell=True, capture_output=True, text=True)
    
    # 3. 进程存在则通过，否则失败
    assert result.returncode == 0, "测试失败：未检测到 Photo Booth 进程，摄像头应用可能未成功启动！"
    print("测试成功：检测到 Photo Booth 进程已在后台运行。")
    
    # 兼容直接通过 python 执行时的后置清理
    kill_photo_booth()

if __name__ == "__main__":
    test_mac_camera_open()
