"""Generate acquisition-layout references, not camera test inputs or calibrated charts."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math

OUT = Path(__file__).resolve().parent
W, H = 1200, 900
FONT = Path("C:/Windows/Fonts/msyh.ttc")


def font(size):
    return ImageFont.truetype(str(FONT), size) if FONT.exists() else ImageFont.load_default()


def canvas(title, subtitle):
    im = Image.new("RGB", (W, H), "#eef3f8")
    d = ImageDraw.Draw(im)
    d.text((55, 32), title, fill="#102439", font=font(34))
    d.text((55, 80), subtitle, fill="#38536c", font=font(20))
    d.rounded_rectangle((55, 130, 1145, 805), radius=16, fill="white", outline="#a9bbcc", width=2)
    return im, d


def footer(d, lines):
    y = 825
    for line in lines:
        d.text((55, y), line, fill="#314b62", font=font(18))
        y += 27


def save(im, name):
    path = OUT / name
    im.save(path)
    print(path)


# Shading: an optically uniform illumination field; grid lines are annotation only.
im, d = canvas("LSC / Shading：均匀场采集示意", "对应 CAM-SHD-001～004；9×9 线框仅表示软件统计区域")
d.rectangle((145, 175, 1055, 740), fill=(150, 150, 150))
for i in range(1, 9):
    x = 145 + 910 * i / 9
    y = 175 + 565 * i / 9
    d.line((x, 175, x, 740), fill="#d4dce2", width=2)
    d.line((145, y, 1055, y), fill="#d4dce2", width=2)
d.text((350, 448), "真实靶面应无格线、无纹理、无色块", fill="white", font=font(25))
footer(d, ["实物：积分球或已测量均匀度的漫射背光板；锁定曝光/增益/白平衡。"])
save(im, "vendor_flat_field_reference.png")


# AWB: entire frame neutral because current metrics use full-frame channel means.
im, d = canvas("AWB：中性灰卡采集示意", "对应 CAM-COLOR-001～005；现有算法统计整幅图 RGB")
d.rectangle((145, 175, 1055, 740), fill=(126, 126, 126))
d.text((410, 390), "中性灰实物靶面", fill="white", font=font(31))
d.text((383, 435), "拍摄时尽量充满取景画面", fill="white", font=font(24))
footer(d, ["实物：经验证光谱中性的灰卡；记录色温、照度和光源型号。"])
save(im, "vendor_neutral_gray_reference.png")


# Sharpness: repeat the same edge pattern in all nine grid regions.
im, d = canvas("SFR / 清晰度：斜边位置示意", "对应 CAM-SHP-001～009；中心/四角及 3×3 各区均需有可比较的边缘")
d.rectangle((145, 175, 1055, 740), fill="white")
centers = [(300 + col*300, 270 + row*190) for row in range(3) for col in range(3)]
for cx, cy in centers:
    # ~5-degree slant: useful layout reference, not a calibrated ISO12233 target.
    pts = [(cx-40, cy-55), (cx+19, cy-55), (cx+40, cy+55), (cx-19, cy+55)]
    d.polygon(pts, fill="#172027")
    d.rectangle((cx-85, cy-80, cx+85, cy+80), outline="#637e95", width=2)
footer(d, ["实物：供应商认可的 SFR / ISO12233 靶卡；全视场清晰、无遮挡。"])
save(im, "vendor_slanted_edge_reference.png")


# Geometry: evenly spaced, measured checkerboard. Current code does not calibrate it yet.
im, d = canvas("Geometry：标定棋盘格位置示意", "对应 CAM-GEO-001～004；当前脚本仅计算边缘分布代理")
left, top, sq, cols, rows = 246, 190, 78, 9, 7
for row in range(rows):
    for col in range(cols):
        color = "#152331" if (row + col) % 2 == 0 else "#ffffff"
        d.rectangle((left + col*sq, top + row*sq,
                     left + (col+1)*sq, top + (row+1)*sq), fill=color)
d.rectangle((left, top, left+cols*sq, top+rows*sq), outline="#7e9ab2", width=3)
d.text((252, 748), "实物方格边长必须测量；印刷比例与平整度需确认", fill="#2a435b", font=font(20))
footer(d, ["正式几何标定还需多角度图、角点检测、内参与畸变系数拟合。"])
save(im, "vendor_geometry_grid_reference.png")


# Combined target is for current proxy screening only. SFR patches interrupt
# the grid, so formal checkerboard calibration requires another unbroken chart.
im, d = canvas("常用综合靶图：清晰度 + 几何代理", "同一张实拍图可运行 camera_vendor_lens_optics.yaml；不是正式标定靶卡")
left, top, cell, cols, rows = 255, 205, 75, 9, 7
for row in range(rows):
    for col in range(cols):
        d.rectangle((left+col*cell, top+row*cell,
                     left+(col+1)*cell, top+(row+1)*cell),
                    fill="#293744" if (row+col)%2 == 0 else "white")
for cy in (270, 455, 640):
    for cx in (300, 600, 900):
        d.rectangle((cx-55, cy-66, cx+55, cy+66), fill="white", outline="#708ba0", width=3)
        d.polygon([(cx-31,cy-50),(cx+13,cy-50),(cx+31,cy+50),(cx-13,cy+50)], fill="#152533")
footer(d, ["九处重复斜边供3×3清晰度筛查；背景网格供当前几何代理。", "正式几何角点/MTF测量须另拍无覆盖的标准棋盘格/ISO12233卡。"])
save(im, "vendor_combined_screening_reference.png")


# Underwater: paired acquisition, same physical target with medium changed.
im, d = canvas("Underwater IQ：空气 / 水下配对示意", "对应 CAM-UW-001～005；同一设备、同一实物靶卡、同一距离和构图")
for x0, label, bg in [(95, "AIR / 空气", "#ffffff"), (620, "WATER / 水下", "#dceff3")]:
    d.rounded_rectangle((x0, 180, x0+480, 740), radius=10, fill=bg, outline="#8199ad", width=2)
    d.text((x0+135, 205), label, fill="#17354a", font=font(24))
    for dx, dy in [(95, 140), (330, 140), (215, 300), (95, 450), (330, 450)]:
        cx, cy = x0+dx, 180+dy
        d.polygon([(cx-27,cy-35),(cx+18,cy-35),(cx+27,cy+35),(cx-18,cy+35)], fill="#20323e")
    d.text((x0+78, 690), "同一斜边实物靶卡", fill="#314f62", font=font(20))
footer(d, ["AWB 另拍全画面中性灰卡；对比度需灰阶靶卡；散射需连续帧。"])
save(im, "vendor_air_water_pair_reference.png")
