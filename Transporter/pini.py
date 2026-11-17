"""Desenarea pin-urilor de pe hartă și a logo-ului (cu PIL), plus mici funcții de formatare."""
import math
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from stil import INDIGO, CIAN

S = 4  # supraeșantionare: desenăm de 4 ori mai mare și micșorăm, ca marginile să fie fine


# ───────── Formatare text ─────────
def nume_scurt(text, limita=30):
    """Scurtează o adresă lungă: păstrează primele 2 părți și taie la `limita` caractere."""
    t = text or ""
    if t.startswith("Depozit (") and t.endswith(")"):
        t = t[9:-1]
    elif t.startswith("Colet ") and ": " in t:
        t = t.split(": ", 1)[1]
    parti = [p.strip() for p in t.split(",") if p.strip()]
    if parti:
        t = ", ".join(parti[:2])
    return t if len(t) <= limita else t[:limita - 1].rstrip() + "…"


def fmt_timp(minute):
    """85 -> '1h 25m', 40 -> '40 min'."""
    m = int(round(minute))
    return f"{m // 60}h {m % 60:02d}m" if m >= 60 else f"{m} min"


# ───────── Ajutoare de desen ─────────
def _rgba(hex_, a=255):
    hex_ = hex_.lstrip("#")
    return (int(hex_[0:2], 16), int(hex_[2:4], 16), int(hex_[4:6], 16), a)


@lru_cache(maxsize=None)
def _font_pil(px, bold=True):
    """Caută un font care există pe sistem (Windows / Mac / Linux)."""
    nume = (["segoeuib.ttf", "arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "Helvetica.ttc"]
            if bold else ["segoeui.ttf", "arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "Helvetica.ttc"])
    for n in nume:
        try:
            return ImageFont.truetype(n, px)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=px)
    except TypeError:
        return ImageFont.load_default()


def _picatura(d, cx, cy, r, tip_y, fill):
    """Forma pinului: un cerc cu un vârf în jos."""
    dist = tip_y - cy
    cos_a = min(r / dist, 0.999)
    sin_a = math.sqrt(1 - cos_a * cos_a)
    d.polygon([(cx - r * sin_a, cy + r * cos_a), (cx, tip_y), (cx + r * sin_a, cy + r * cos_a)], fill=fill)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)


def _casuta(d, cx, cy, culoare):
    """Pictograma de clădire (depozit) din interiorul pinului."""
    k = S
    d.polygon([(cx - 9.5 * k, cy - 0.5 * k), (cx, cy - 9.5 * k), (cx + 9.5 * k, cy - 0.5 * k)], fill=(255, 255, 255, 255))
    d.rectangle([cx - 7 * k, cy - 0.5 * k, cx + 7 * k, cy + 8 * k], fill=(255, 255, 255, 255))
    d.rectangle([cx - 2 * k, cy + 3 * k, cx + 2 * k, cy + 8 * k], fill=culoare)


# ───────── Pin ─────────
@lru_cache(maxsize=None)
def construieste_pin(culoare, simbol, eticheta=None, culoare_text="#FFFFFF"):
    """Imagine RGBA cu pinul. Vârful pinului e la mijlocul marginii de jos.

    simbol   = numărul din pin, sau "home" pentru depozit
    eticheta = textul din căsuța de deasupra pinului (None = fără căsuță)
    """
    r, h_pin = 17, 55
    lab_h, gap = 24, 5
    w = 46
    font_e = _font_pil(12 * S, True)
    top = 0
    if eticheta:
        lw = font_e.getlength(eticheta) / S + 24
        w = max(w, int(lw) + 8)
        top = lab_h + gap
    h = top + h_pin
    cx, cy, tip = w / 2, top + 21, top + 53

    img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))

    # 1) umbra de sub vârf
    umbra = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(umbra).ellipse([(cx - 9) * S, (tip - 3) * S, (cx + 9) * S, (tip + 2) * S], fill=(0, 0, 0, 170))
    img.alpha_composite(umbra.filter(ImageFilter.GaussianBlur(2 * S)))

    # 2) pinul: contur alb + corp colorat
    d = ImageDraw.Draw(img)
    c = _rgba(culoare)
    inel = 3
    _picatura(d, cx * S, cy * S, r * S, tip * S, (255, 255, 255, 255))
    tip_in = tip - inel * (tip - cy) / r
    _picatura(d, cx * S, cy * S, (r - inel) * S, tip_in * S, c)

    # 3) reflex fin sus-stânga
    lum = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lum).ellipse([(cx - 11) * S, (cy - 12) * S, (cx + 2) * S, (cy - 3) * S], fill=(255, 255, 255, 38))
    img.alpha_composite(lum.filter(ImageFilter.GaussianBlur(1.5 * S)))
    d = ImageDraw.Draw(img)

    # 4) numărul sau căsuța de depozit
    if simbol == "home":
        _casuta(d, cx * S, cy * S, c)
    else:
        px = 17 if len(simbol) == 1 else 14 if len(simbol) == 2 else 11
        d.text((cx * S, (cy + 0.5) * S), simbol, font=_font_pil(px * S, True), fill=_rgba(culoare_text), anchor="mm")

    # 5) eticheta de deasupra
    if eticheta:
        x0, x1 = (w - lw) / 2, (w + lw) / 2
        d.rounded_rectangle([x0 * S, 1 * S, x1 * S, (lab_h - 1) * S], radius=(lab_h / 2) * S,
                            fill=(10, 14, 24, 238), outline=c, width=int(1.6 * S))
        d.text((w / 2 * S, (lab_h / 2) * S), eticheta, font=font_e, fill=(236, 240, 248, 255), anchor="mm")

    resample = getattr(Image, "Resampling", Image).LANCZOS
    return img.resize((w, h), resample)


# ───────── Logo ─────────
def construieste_logo(dim=176):
    """Pătrat rotunjit cu gradient indigo→cian și un mic traseu desenat în alb."""
    a = Image.new("RGBA", (dim, dim), _rgba(INDIGO))
    b = Image.new("RGBA", (dim, dim), _rgba(CIAN))
    vert = Image.linear_gradient("L").resize((dim, dim))
    rotit = vert.transpose(Image.Transpose.ROTATE_90) if hasattr(Image, "Transpose") else vert.transpose(Image.ROTATE_90)
    fund = Image.composite(b, a, Image.blend(vert, rotit, 0.5))

    masca = Image.new("L", (dim, dim), 0)
    ImageDraw.Draw(masca).rounded_rectangle([0, 0, dim - 1, dim - 1], radius=int(dim * 0.28), fill=255)
    out = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    out.paste(fund, (0, 0), masca)

    d = ImageDraw.Draw(out)
    d.line([(52, 128), (52, 92), (124, 92), (124, 54)], fill=(255, 255, 255, 255), width=12, joint="curve")
    d.ellipse([36, 112, 68, 144], outline=(255, 255, 255, 255), width=9)
    d.ellipse([106, 36, 142, 72], fill=(255, 255, 255, 255))
    return out
