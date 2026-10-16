"""
Derivative-image pipeline for the static site.

The repository keeps full-resolution cover scans (~54 MB) under `assets/images/`.
Publishing those unchanged would make a slow site and double the repo, so the
site ships two downscaled derivatives per image and links the untouched original
in the repository as the citable artifact:

    docs/assets/img/<path>            display copy  (long edge <= 1100 px, 1800 for scans)
    docs/assets/img/thumb/<path>      gallery thumb (long edge <=  420 px)

The encoder is chosen from the pixels, not from the source filename: a good part
of the pool is PNG-encoded photographs (several of them saved with a `.jpg`
name, and some with a fully opaque alpha channel), which cost ten times what the
same cover costs as a JPEG. So an image keeps PNG only when it really uses
transparency, and the derivative's extension is corrected to match — call
``url()`` for the published path rather than assuming the source name.

Rebuilds are incremental: a derivative is regenerated only when the source is
newer. Animated GIFs and anything PIL cannot open are copied verbatim.
"""
import os
import shutil

from PIL import Image, ImageOps

DISPLAY_MAX = 1100
DISPLAY_MAX_SCAN = 1800      # page scans of Tartt's essays must stay readable
THUMB_MAX = 420
JPEG_QUALITY = 82
THUMB_QUALITY = 78
FLATTEN_BG = (255, 255, 255)   # transparency that turns out to be unused


class ImageSet:
    def __init__(self, src_root, out_root, url_prefix, verbose=False):
        self.src_root = src_root
        self.out_root = out_root
        self.url_prefix = url_prefix.rstrip("/")
        self.verbose = verbose
        self.built = self.skipped = self.copied = self.failed = 0
        self._out = {}           # source rel -> published rel, or None if unusable

    # ------------------------------------------------------------------ public
    def url(self, rel, thumb=False):
        """Published URL for an image given its path relative to `assets/images/`."""
        rel = self._norm(rel)
        out = self._out[rel] if rel in self._out else (rel if self.ensure(rel) else rel)
        out = out or rel
        return f"{self.url_prefix}/{'thumb/' if thumb else ''}{out}"

    def ensure(self, rel):
        """Build both derivatives for one image. Returns True if usable."""
        rel = self._norm(rel)
        if rel in self._out:
            return self._out[rel] is not None
        src = os.path.join(self.src_root, rel)
        if not os.path.isfile(src):
            self._out[rel] = None
            return False
        out_rel = self._plan(src, rel)
        big = DISPLAY_MAX_SCAN if rel.startswith("scans/") else DISPLAY_MAX
        ok = (self._derive(src, os.path.join(self.out_root, out_rel), big, JPEG_QUALITY)
              and self._derive(src, os.path.join(self.out_root, "thumb", out_rel),
                               THUMB_MAX, THUMB_QUALITY))
        self._out[rel] = out_rel if ok else None
        return ok

    def ensure_all(self):
        for dp, _, files in os.walk(self.src_root):
            for fn in sorted(files):
                if fn.startswith("."):
                    continue
                if os.path.splitext(fn)[1].lower() in (
                        ".jpg", ".jpeg", ".png", ".webp", ".gif"):
                    self.ensure(os.path.relpath(os.path.join(dp, fn), self.src_root))

    def report(self):
        return (f"images: {self.built} built, {self.skipped} up-to-date, "
                f"{self.copied} copied verbatim, {self.failed} failed")

    # ----------------------------------------------------------------- private
    @staticmethod
    def _norm(rel):
        return rel.replace(os.sep, "/").lstrip("/")

    def _plan(self, src, rel):
        """Published path for `rel`, with the extension the derivative will use."""
        stem, ext = os.path.splitext(rel)
        ext = ext.lower()
        try:
            with Image.open(src) as im:
                if getattr(im, "is_animated", False):
                    return rel
                if ext == ".webp":           # already compact; leave the format alone
                    return stem + ".webp"
                return stem + (".png" if _has_alpha(im) else ".jpg")
        except Exception:                                         # noqa: BLE001
            return rel

    def _derive(self, src, dst, max_edge, quality):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            self.skipped += 1
            return True
        out_ext = os.path.splitext(dst)[1].lower()
        try:
            with Image.open(src) as im:
                if getattr(im, "is_animated", False):
                    shutil.copy2(src, dst)
                    self.copied += 1
                    return True
                im = ImageOps.exif_transpose(im)
                if max(im.size) > max_edge:
                    im.thumbnail((max_edge, max_edge), Image.LANCZOS)
                if out_ext in (".jpg", ".jpeg"):
                    _flatten(im).save(dst, "JPEG", quality=quality,
                                      optimize=True, progressive=True)
                elif out_ext == ".webp":
                    im.save(dst, "WEBP", quality=quality, method=5)
                elif out_ext == ".png":
                    im.save(dst, "PNG", optimize=True)
                else:
                    im.save(dst)
            self.built += 1
            return True
        except Exception as exc:                                  # noqa: BLE001
            if self.verbose:
                print(f"  ! {os.path.basename(src)}: {exc} — copied verbatim")
            try:
                shutil.copy2(src, dst)
                self.copied += 1
                return True
            except OSError:
                self.failed += 1
                return False


def _flatten(im):
    """RGB copy of `im`, compositing any transparency onto a plain background."""
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, FLATTEN_BG)
        bg.paste(im, mask=im.getchannel("A"))
        return bg
    return im.convert("RGB")


def _has_alpha(im):
    """True only when transparency is actually used, not merely available."""
    if im.mode == "P":
        if "transparency" not in im.info:
            return False
        im = im.convert("RGBA")
    elif im.mode not in ("RGBA", "LA"):
        return False
    lo, _hi = im.getchannel("A").getextrema()
    return lo < 250
