from PIL import Image, ImageDraw, ImageFont
import math

SIZE = 512
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Background circle — dark navy
cx, cy, r = SIZE // 2, SIZE // 2, SIZE // 2
draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(10, 12, 30, 255))

# Outer glow rings
for i, (rad, alpha) in enumerate([(248, 60), (238, 40), (228, 25)]):
    draw.ellipse(
        [cx - rad, cy - rad, cx + rad, cy + rad],
        outline=(130, 80, 255, alpha), width=3
    )

# Inner accent ring
draw.ellipse(
    [cx - 200, cy - 200, cx + 200, cy + 200],
    outline=(80, 180, 255, 80), width=1
)

# Circuit dots around the ring
for deg in range(0, 360, 30):
    rad_pos = 220
    x = cx + int(rad_pos * math.cos(math.radians(deg)))
    y = cy + int(rad_pos * math.sin(math.radians(deg)))
    dot_r = 5 if deg % 90 == 0 else 3
    color = (130, 80, 255, 255) if deg % 90 == 0 else (80, 120, 200, 180)
    draw.ellipse([x - dot_r, y - dot_r, x + dot_r, y + dot_r], fill=color)

# Z shape — bold geometric
col_bright = (160, 100, 255, 255)
col_accent = (80, 180, 255, 255)
lw = 28

# Top bar of Z
draw.line([(165, 175), (345, 175)], fill=col_bright, width=lw)
# Diagonal of Z
draw.line([(345, 175), (165, 340)], fill=col_accent, width=lw)
# Bottom bar of Z
draw.line([(165, 340), (345, 340)], fill=col_bright, width=lw)

# End caps (rounded feel)
for pt, col in [((165, 175), col_bright), ((345, 175), col_bright),
                ((165, 340), col_bright), ((345, 340), col_bright)]:
    r2 = lw // 2
    draw.ellipse([pt[0]-r2, pt[1]-r2, pt[0]+r2, pt[1]+r2], fill=col)

# Small glow dot center
draw.ellipse([cx-6, cy-6, cx+6, cy+6], fill=(200, 160, 255, 200))

# Save
out = "eleeBo_avatar.png"
img.save(out)
print(f"Saved: {out}")
