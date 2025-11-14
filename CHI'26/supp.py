# # -*- coding: utf-8 -*-
# import json
# from pathlib import Path

# from PIL import Image, ImageDraw, ImageFont

# root = Path("output")  # output/<participant>/<timestamp>/...
# out_dir = Path("combined_with_text")
# out_dir.mkdir(exist_ok=True)


# # ===== 폰트 =====
# def get_font(size=28):
#     for fp in [
#         "/System/Library/Fonts/Supplemental/Arial.ttf",  # macOS
#         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
#         "C:/Windows/Fonts/arial.ttf",  # Windows
#     ]:
#         if Path(fp).exists():
#             return ImageFont.truetype(fp, size)
#     return ImageFont.load_default()


# font = get_font(28)


# # ===== 유틸 =====
# def wrap_text(draw, text, font, max_width):
#     if not text:
#         return []
#     words, lines, cur = text.split(), [], []
#     for w in words:
#         trial = (" ".join(cur + [w])).strip()
#         bbox = draw.textbbox((0, 0), trial, font=font)
#         if bbox[2] - bbox[0] <= max_width or not cur:
#             cur.append(w)
#         else:
#             lines.append(" ".join(cur))
#             cur = [w]
#     if cur:
#         lines.append(" ".join(cur))
#     return lines


# def draw_bold(draw, pos, text, font, fill="black"):
#     x, y = pos
#     for dx, dy in [(0, 0), (1, 0), (0, 1), (1, 1)]:
#         draw.text((x + dx, y + dy), text, font=font, fill=fill)


# def add_border(img, color="black", width=5):
#     W, H = img.size
#     out = img.copy()
#     d = ImageDraw.Draw(out)
#     for i in range(width):
#         d.rectangle([i, i, W - 1 - i, H - 1 - i], outline=color)
#     return out


# # ===== 메인 =====
# for participant_dir in sorted(p for p in root.iterdir() if p.is_dir()):
#     participant = participant_dir.name
#     scene_idx = 0

#     for run_dir in sorted(d for d in participant_dir.iterdir() if d.is_dir()):
#         prompt_path = run_dir / "prompt.json"
#         gen_img_path = run_dir / "image.png"
#         if not (prompt_path.exists() and gen_img_path.exists()):
#             continue

#         scene_idx += 1

#         # prompt.json 읽기
#         with open(prompt_path, "r", encoding="utf-8") as f:
#             meta = json.load(f)
#         global_cap = meta.get("global_caption", "") or ""
#         region_caps = meta.get("region_captions", []) or []
#         region_boxes = meta.get("region_bboxes", []) or []

#         # 생성 이미지
#         gen_img = Image.open(gen_img_path).convert("RGB")
#         W, H = gen_img.size

#         # (a) Bounding Boxes
#         bbox_img = Image.new("RGB", (W, H), "white")
#         dbox = ImageDraw.Draw(bbox_img)
#         for i, box in enumerate(region_boxes, start=1):
#             if not (isinstance(box, (list, tuple)) and len(box) == 4):
#                 continue
#             x1, y1, x2, y2 = [int(v * W) for v in box]
#             if x2 < x1:
#                 x1, x2 = x2, x1
#             if y2 < y1:
#                 y1, y2 = y2, y1
#             dbox.rectangle([x1, y1, x2, y2], outline="black", width=3)
#             dbox.text((x1 + 10, max(y1 + 12, 0)), str(i), fill="black", font=font)

#         bbox_img = add_border(bbox_img)
#         gen_img = add_border(gen_img)

#         # 상단 2열
#         padding, top_caption_h = 20, 40
#         total_w = W * 2 + padding
#         top_h = H + top_caption_h
#         top = Image.new("RGB", (total_w, top_h), "white")
#         positions = [
#             (0, "(a) Bounding Boxes", bbox_img),
#             (W + padding, "(b) Generated Image", gen_img),
#         ]
#         dtp = ImageDraw.Draw(top)
#         for x, caption, img in positions:
#             top.paste(img, (x, 0))
#             bb = dtp.textbbox((0, 0), caption, font=font)
#             dtp.text(
#                 (x + (W - (bb[2] - bb[0])) // 2, H + 6),
#                 caption,
#                 fill="black",
#                 font=font,
#             )

#         # 하단 텍스트
#         side_margin = 30
#         text_max_w = total_w - side_margin * 2
#         dummy = ImageDraw.Draw(Image.new("RGB", (10, 10), "white"))
#         lines, bold = [], []
#         if global_cap:
#             lines.append("Global caption:")
#             bold.append(True)
#             for l in wrap_text(dummy, global_cap, font, text_max_w):
#                 lines.append(l)
#                 bold.append(False)
#             lines.append("")
#             bold.append(False)
#         if region_caps:
#             lines.append("Regional captions:")
#             bold.append(True)
#             for i, cap in enumerate(region_caps, start=1):
#                 for l in wrap_text(dummy, f"{i}. {cap}", font, text_max_w):
#                     lines.append(l)
#                     bold.append(False)

#         if lines:
#             bboxA = dummy.textbbox((0, 0), "A", font=font)
#             line_h = (bboxA[3] - bboxA[1]) + 6
#             text_block_h = 30 + line_h * len(lines) + 30
#         else:
#             line_h, text_block_h = 0, 0

#         sep_h = 2 if lines else 0
#         final_h = top_h + sep_h + text_block_h
#         final_img = Image.new("RGB", (total_w, final_h), "white")
#         final_img.paste(top, (0, 0))

#         if lines:
#             dfinal = ImageDraw.Draw(final_img)
#             dfinal.rectangle([0, top_h, total_w, top_h + sep_h], fill=(220, 220, 220))
#             y = top_h + sep_h + 30
#             x0 = side_margin
#             for ln, is_bold in zip(lines, bold):
#                 if is_bold:
#                     draw_bold(dfinal, (x0, y), ln, font=font)
#                 else:
#                     dfinal.text((x0, y), ln, font=font, fill="black")
#                 y += line_h

#         # 저장
#         save_name = f"{participant}_scene{scene_idx:02d}.png"
#         out_path = out_dir / save_name
#         final_img.save(out_path, dpi=(300, 300))
#         print("saved", out_path)
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

img_dir = Path("combined_with_text")
out_pdf = Path("Study2_Generated_images_with_prompts.pdf")


def get_font(size=28):
    for fp in [
        "/System/Library/Fonts/Supplemental/Arial.ttf",  # macOS
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "C:/Windows/Fonts/arial.ttf",  # Windows
    ]:
        if Path(fp).exists():
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


font = get_font(28)

# 파일명: P{num}_scene{num}.png
pat = re.compile(r"^P(\d+)_scene(\d+)$")


def sort_key(p: Path):
    m = pat.match(p.stem)
    if not m:
        return (999999, 999999)
    pi, si = map(int, m.groups())
    return (pi, si)


def add_header(img: Image.Image, text: str, font: ImageFont.ImageFont, header_h=60):
    W, H = img.size
    canvas = Image.new("RGB", (W, H + header_h), "white")
    canvas.paste(img, (0, header_h))
    draw = ImageDraw.Draw(canvas)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((W - tw) // 2, (header_h - th) // 2), text, fill="black", font=font)
    draw.line([(0, header_h - 1), (W, header_h - 1)], fill=(200, 200, 200), width=2)
    return canvas


imgs = sorted(img_dir.glob("*.png"), key=sort_key)
pages = []

for p in imgs:
    im = Image.open(p).convert("RGB")
    m = pat.match(p.stem)
    if m:
        pi, si = m.groups()
        header = f"P{pi} — Scene {int(si):02d}"
    else:
        header = p.stem
    pages.append(add_header(im, header, font))

if not pages:
    raise SystemExit("이미지를 찾지 못했습니다. 폴더 경로/파일명을 확인하세요.")

first, rest = pages[0], pages[1:]
first.save(out_pdf, save_all=True, append_images=rest)
print(f"[ok] PDF saved: {out_pdf}")
print(f"[ok] PDF saved: {out_pdf}")
