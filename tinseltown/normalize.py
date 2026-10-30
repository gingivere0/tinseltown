"""Map free-text formats and notes onto the tracker's fixed vocabularies."""
import re

FORMATS = [
    (r"imax\s*3d", "IMAX 3D"), (r"imax", "IMAX"), (r"dolby\s*vision", "Dolby Vision"),
    (r"dolby\s*3d", "Dolby 3D"), (r"dolby", "Dolby Cinema"), (r"prime\s*real\s*d", "PRIME RealD"),
    (r"real\s*d\s*3d|reald", "RealD 3D"), (r"screen\s*x", "ScreenX"), (r"mx4d", "MX4D"),
    (r"4dx", "4DX"), (r"d-?box", "D-BOX"), (r"prime", "PRIME"), (r"\bxl\b", "XL"),
    (r"70\s*mm", "70mm"), (r"35\s*mm", "35mm"), (r"16\s*mm", "16mm"),
    (r"i\.?b\.?\s*tech", "35mm IB Tech"), (r"4k\s*dcp|^4k$", "4K DCP"), (r"\bdcp\b", "DCP"),
    (r"vhs", "VHS"), (r"dvd", "DVD"), (r"nitrate", "Nitrate"),
]

EVENTS = [
    (r"\bQ ?& ?A\b", "Q&A"),
    (r"\bintro(duction|duced)?\b|\bin person\b|\bon stage\b", "Intro/guest"),
    (r"\bDF w/|double feature", "Double feature"),
    (r"premiere", "Premiere"),
    (r"restoration", "Restoration"),
    (r"live (score|music|accompaniment)|live dj", "Live music"),
    (r"sold out", "Sold out"),
    (r"anniversary", "Anniversary"),
    (r"opening night", "Opening night"),
    (r"nitrate", "Nitrate"),
]


def formats(raw: str) -> list[str]:
    out = []
    for part in re.split(r"[,;/]", raw or ""):
        p = part.strip().lower()
        for rx, name in FORMATS:
            if p and re.search(rx, p):
                if name not in out:
                    out.append(name)
                break
    return out


def formats_in_text(text: str) -> list[str]:
    """Formats mentioned anywhere in free text, such as an event description."""
    out = []
    for rx, name in FORMATS:
        if name in ("PRIME", "XL"):  # too ambiguous outside a format field
            continue
        if re.search(rx, text or "", re.I) and name not in out:
            out.append(name)
    return out


def events(*texts: str) -> list[str]:
    text = " ".join(t for t in texts if t)
    return [name for rx, name in EVENTS if re.search(rx, text, re.I)]
