#!/usr/bin/env python3
"""Transliterate the pre-registration to ASCII for rendering.

The rendered PDF/HTML are a convenience copy; the Markdown is authoritative.
Rendering from ASCII keeps the output identical across font stacks and makes
the text-extraction checks (which is how the numbers in the PDF get verified)
work on a predictable character set.

Nothing here may change a NUMBER.  The map is symbols and letters only, and
`verify` below asserts that the multiset of numeric tokens is unchanged.
"""
import re
import sys
from collections import Counter
import unicodedata

MAP = {
    "—": "--", "–": "-", "−": "-",       # em/en dash, minus
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "…": "...", " ": " ", " ": " ", " ": " ",
    "·": "-", "•": "*",
    "→": "->", "←": "<-", "⇒": "=>",
    "≥": ">=", "≤": "<=", "≠": "!=", "≈": "~=",
    "÷": "/", "±": "+/-",
    "∈": "in", "⊆": "subset-of", "⊇": "superset-of",
    "∞": "inf", "∑": "sum", "√": "sqrt",
    "§": "Sec.", "‖": "||", "∥": "||",
    "α": "alpha", "β": "beta", "γ": "gamma",
    "δ": "delta", "Δ": "Delta", "ε": "epsilon",
    "κ": "kappa", "λ": "lambda", "μ": "mu",
    "ρ": "rho", "σ": "sigma", "τ": "tau", "φ": "phi",
    "₀": "_0", "₁": "_1", "₂": "_2",
    "✓": "[ok]", "✅": "[OK]", "❌": "[X]", "⛔": "[STOP]",
    "ὓ4": "[X]",
    "⎧": "", "⎬": "", "⎩": "", "⎫": "",  # brace pieces
    "≡": "===",
}

# Combining marks used for r-hat, p-hat, m-bar: strip the mark, name the base.
COMBINING = {"̂": "_hat", "̄": "_bar", "̃": "_tilde"}

EMOJI = {
    "\U0001f534": "[X]", "\U0001f7e2": "[ok]", "\U0001f7e1": "[!]",
    "⚠️": "[!]", "⚠": "[!]", "\U0001f4c8": "", "\U0001f4d5": "",
    "\U0001f511": "", "\U0001f4e6": "", "\U0001f5c2️": "", "\U0001f512": "",
    "️": "",
}


# U+00B7 MIDDLE DOT is used in this package for TWO unrelated things: as a list
# separator ("117 control - 39 per dose") and as a multiplication sign. MAP sends
# it to "-", which is harmless for the first and CORRUPTS THE SECOND: the source
# `(m_bar - 1)*rho`, written with a middle dot, rendered as `(m_bar - 1)-rho`,
# which a reader parses as subtraction. The numeric guard is structurally blind to
# this -- no value changed, only an operator -- and it stood in the v1.9 and v1.10
# deposits. Fixed at the source on 2026-08-17 (multiplication is now U+00D7, which
# asciify spaces), and this guard exists so the class cannot silently return.
#
# The discriminator is TIGHT AND DELIBERATELY INCOMPLETE: a middle dot with no
# whitespace on at least one side is multiplication (`)*rho`, `0.55*importance`,
# `K*T`, `delta*|p1-p0|`). A separator in this package always has whitespace on
# both sides, so this yields no false positives -- which is the property that
# matters for a guard that aborts a render.
#
# What it does NOT catch, stated rather than glossed: multiplication written WITH
# spaces on both sides, e.g. `(0.043 . sev)`. Two such cases existed and were
# fixed by hand. There is no mechanical way to tell them from a separator, so the
# residual risk is real and is recorded here instead of being papered over.
MULTIPLICATION_DOT = re.compile(r"\S\u00b7|\u00b7\S")


def check_no_multiplication_dot(text: str, label: str = "input") -> None:
    """Abort if U+00B7 touches an operand, i.e. is being used as multiplication."""
    hits = [
        text[max(0, m.start() - 45):m.end() + 45].replace("\n", " ")
        for m in MULTIPLICATION_DOT.finditer(text)
    ]
    if hits:
        raise SystemExit(
            f"{label}: U+00B7 used as multiplication in {len(hits)} place(s) -- it "
            f"transliterates to '-' and would read as subtraction. Use U+00D7.\n  "
            + "\n  ".join(hits[:8])
        )


def asciify(text: str) -> str:
    check_no_multiplication_dot(text, "source")
    for k, v in EMOJI.items():
        text = text.replace(k, v)
    # "x" is a word character, so a bare substitution glues: `)x0.098459`.
    # The guard then reads `098459` as a NEW number that was never in the
    # source -- the transliterator inventing a value is exactly what it must
    # never do.  Always spaced.
    text = re.sub(r"\s*\u00d7\s*", " x ", text)
    # combining marks: "r" + U+0302 -> "r_hat"
    for mark, name in COMBINING.items():
        text = re.sub(r"(\w)" + mark, r"\1" + name, text)
    for k, v in MAP.items():
        text = text.replace(k, v)
    # anything left: strip accents, then drop what is still non-ASCII
    out = []
    for ch in text:
        if ord(ch) < 128:
            out.append(ch)
            continue
        d = unicodedata.normalize("NFKD", ch)
        stripped = "".join(c for c in d if ord(c) < 128)
        out.append(stripped)
    return "".join(out)


# Comparing numeric tokens is only meaningful if both sides are tokenised the
# same way, and two rewrites of this guard got that wrong before it worked:
#
#   - digits that are part of an IDENTIFIER are not values.  `p0_hat`, `H1`,
#     `S2`, `lambda_0` must not count.  The lookbehind excludes any token
#     glued to a letter, digit or underscore.
#   - combining marks break word boundaries.  In the source, `p-hat-0` is
#     "p" + U+0302 + "0", so the mark makes `\b` fire and the 0 reads as a
#     free-standing value; after transliteration it is `p0_hat` and it does
#     not.  Same character, two answers.  Marks are therefore stripped from
#     BOTH sides before tokenising.
# str.translate keys are ORDINALS, not characters.  Built from chr() this
# silently did nothing and the marks survived -- a no-op guard that reports
# success is worse than an absent one.
MARKS = dict.fromkeys(range(0x300, 0x370))
NUM = re.compile(r"(?<!\w)\d[\d,._]*")  # \w, not [A-Za-z]: `lambda-0` is Greek


def numbers(text: str) -> list[str]:
    """Value-like numeric tokens.  Identifier digits and marks excluded."""
    flat = unicodedata.normalize("NFKD", text).translate(MARKS)
    return sorted(t.rstrip(".,_").replace(",", "") for t in NUM.findall(flat))


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    raw = open(src, encoding="utf-8").read()
    conv = asciify(raw)

    # Multiset, not set: an earlier version compared with `not in`, which is
    # blind to multiplicity and reported "lost: [] new: []" while aborting --
    # a failure message that says nothing is worse than no message.
    ca, cb = Counter(numbers(raw)), Counter(numbers(conv))
    if ca != cb:
        sys.exit(
            "ABORT: numeric tokens changed.\n"
            f"  lost: {(ca - cb).most_common(10)}\n"
            f"  new : {(cb - ca).most_common(10)}"
        )

    left = sorted({c for c in conv if ord(c) > 127})
    if left:
        sys.exit(f"ABORT: non-ASCII survived: {[hex(ord(c)) for c in left]}")

    open(dst, "w", encoding="utf-8").write(conv)
    print(f"{src} -> {dst}: {sum(ca.values())} numeric tokens preserved, pure ASCII")
