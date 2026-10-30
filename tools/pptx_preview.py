import sys, subprocess, tempfile, os, glob
from PIL import Image, ImageDraw

src, out = sys.argv[1], sys.argv[2]
pages = [int(x) for x in sys.argv[3:]]
d = tempfile.mkdtemp()
subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", d, src],
               check=True, capture_output=True)
pdf = glob.glob(os.path.join(d, "*.pdf"))[0]
imgs = []
for p in pages:
    pre = os.path.join(d, f"p{p}")
    subprocess.run(["pdftoppm", "-png", "-scale-to-x", "480", "-scale-to-y", "-1",
                    "-f", str(p), "-l", str(p), "-singlefile", pdf, pre], check=True)
    im = Image.open(pre + ".png").convert("RGB")
    ImageDraw.Draw(im).text((6, 4), f"S{p}", fill=(255, 0, 0))
    imgs.append(im)
cols = min(3, len(imgs))
rows = -(-len(imgs) // cols)
w, h = imgs[0].size
grid = Image.new("RGB", (w * cols, h * rows), "white")
for i, im in enumerate(imgs):
    grid.paste(im, ((i % cols) * w, (i // cols) * h))
grid.save(out)
