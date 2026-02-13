from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd


# ---------------------------
# Fixed grid (as you specified)
# ---------------------------
GRID_START = 2599.92775
GRID_END   = 3500.37163
GRID_STEP  = 0.394931521929825

WN_MIN = 2600.0
WN_MAX = 3500.0

TH_CLASSIFIED = 0.75
TH_NONPLASTIC = 0.60


def make_grid() -> np.ndarray:
    n = int(round((GRID_END - GRID_START) / GRID_STEP)) + 1
    return np.linspace(GRID_START, GRID_END, n)


GRID = make_grid()
WIN_MASK = (GRID >= WN_MIN) & (GRID <= WN_MAX)
GRID_WIN = GRID[WIN_MASK]


# ---------------------------
# Helpers
# ---------------------------
def _base_name(col: str) -> str:
    col = str(col).strip()
    return re.sub(r"\.\d+$", "", col)


def pearson_r(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.size != b.size or a.size < 3:
        return float("nan")
    am = a - a.mean()
    bm = b - b.mean()
    denom = np.sqrt(np.dot(am, am) * np.dot(bm, bm))
    if denom == 0:
        return float("nan")
    return float(np.dot(am, bm) / denom)


def classify(r: float) -> str:
    if not np.isfinite(r) or r < TH_NONPLASTIC:
        return "non-plastic"
    if r < TH_CLASSIFIED:
        return "unclassified"
    return "classified"


# ---------------------------
# Data structures
# ---------------------------
@dataclass
class Curve:
    curve_id: str
    y_win: np.ndarray   # y on GRID_WIN


@dataclass
class Hit:
    polymer: str
    curve_id: str
    r: float
    library: str        # "amide" or "non-amide"


Library = Dict[str, List[Curve]]  # polymer -> list of curves


# ---------------------------
# Load library from Excel
# ---------------------------
def load_library_sheet(excel_path: str, sheet_index: int, library_tag: str) -> Library:
    """
    Read one sheet and convert all curves onto GRID_WIN.
    """
    df = pd.read_excel(excel_path, sheet_name=sheet_index)
    if df.shape[1] < 2:
        raise ValueError(f"Sheet {sheet_index} must have at least 2 columns (X + Y columns).")

    x = pd.to_numeric(df.iloc[:, 0], errors="coerce").to_numpy(dtype=float)
    if not np.all(np.isfinite(x)):
        raise ValueError(f"Sheet {sheet_index}: X column contains non-numeric values.")

    # sort by x for interpolation safety
    order = np.argsort(x)
    x = x[order]

    lib: Library = {}

    for j, col in enumerate(df.columns[1:], start=1):
        y = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float)
        y = y[order]

        # valid points only
        mask = np.isfinite(x) & np.isfinite(y)
        if mask.sum() < 50:
            continue
        x2 = x[mask]
        y2 = y[mask]

        # interpolate to fixed GRID_WIN (no extrapolation issues if x range covers it)
        if x2.max() < GRID_WIN.min() or x2.min() > GRID_WIN.max():
            continue
        y_win = np.interp(GRID_WIN, x2, y2).astype(float)

        polymer = _base_name(col)
        curve_id = f"{library_tag}:{polymer}__col{j}"
        lib.setdefault(polymer, []).append(Curve(curve_id=curve_id, y_win=y_win))

    if not lib:
        raise ValueError(f"No valid curves loaded from sheet {sheet_index}.")
    return lib


def load_both_libraries(excel_path: str) -> Tuple[Library, Library]:
    lib_amide = load_library_sheet(excel_path, sheet_index=0, library_tag="amide")
    lib_non  = load_library_sheet(excel_path, sheet_index=1, library_tag="non-amide")
    return lib_amide, lib_non


# ---------------------------
# Unknown spectrum TXT
# ---------------------------
def read_unknown_txt(path: str) -> Tuple[Optional[np.ndarray], np.ndarray]:
    """
    Supported:
    - two columns x,y (comma/tab/space)
    - one column y-only
    """
    xs: List[float] = []
    ys: List[float] = []

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = re.split(r"[,\s]+", line)
            parts = [p for p in parts if p != ""]
            if len(parts) >= 2:
                try:
                    x = float(parts[0])
                    y = float(parts[1])
                except ValueError:
                    continue
                xs.append(x)
                ys.append(y)
            elif len(parts) == 1:
                try:
                    y = float(parts[0])
                except ValueError:
                    continue
                ys.append(y)

    if xs:
        x = np.array(xs, dtype=float)
        y = np.array(ys[:len(xs)], dtype=float)
        return x, y

    return None, np.array(ys, dtype=float)


def unknown_to_gridwin(x_unknown: Optional[np.ndarray], y_unknown: np.ndarray) -> np.ndarray:
    """
    Convert unknown to GRID_WIN.

    - If x provided: interpolate onto GRID_WIN
    - If y-only:
        * if length == len(GRID): slice window
        * if length == len(GRID_WIN): use directly
        * else: raise
    """
    y_unknown = np.asarray(y_unknown, dtype=float)

    if x_unknown is None:
        if y_unknown.size == GRID.size:
            return y_unknown[WIN_MASK].astype(float)
        if y_unknown.size == GRID_WIN.size:
            return y_unknown.astype(float)
        raise ValueError(
            f"Unknown txt is y-only, but length={y_unknown.size}. "
            f"Need length={GRID.size} (full grid) or {GRID_WIN.size} (window grid), "
            f"or provide x,y two columns."
        )

    x_unknown = np.asarray(x_unknown, dtype=float)
    order = np.argsort(x_unknown)
    x_unknown = x_unknown[order]
    y_unknown = y_unknown[order]

    if x_unknown.max() < GRID_WIN.min() or x_unknown.min() > GRID_WIN.max():
        raise ValueError(
            f"Unknown x-range [{x_unknown.min()}, {x_unknown.max()}] does not overlap "
            f"required window [{GRID_WIN.min()}, {GRID_WIN.max()}]."
        )

    return np.interp(GRID_WIN, x_unknown, y_unknown).astype(float)


# ---------------------------
# Matching
# ---------------------------
def match_one_library(y_u_win: np.ndarray, lib: Library, lib_tag: str, top_n: int = 5) -> Tuple[Hit, List[Hit]]:
    hits: List[Hit] = []
    for polymer, curves in lib.items():
        for c in curves:
            r = pearson_r(y_u_win, c.y_win)
            if np.isfinite(r):
                hits.append(Hit(polymer=polymer, curve_id=c.curve_id, r=float(r), library=lib_tag))

    if not hits:
        raise RuntimeError(f"No valid matches computed in {lib_tag} library.")

    hits.sort(key=lambda h: h.r, reverse=True)
    return hits[0], hits[:max(1, top_n)]


def choose_final_hit(amide_input: str, best_amide: Hit, best_non: Optional[Hit]) -> Hit:
    if amide_input == "no":
        assert best_non is not None
        return best_non

    # amide_input == "yes"
    if best_amide.r >= TH_CLASSIFIED or best_non is None:
        return best_amide

    # r < 0.75 -> compare both and choose higher
    return best_non if best_non.r > best_amide.r else best_amide


# ---------------------------
# CLI
# ---------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--library-xlsx", default="MP library.xlsx", help="MP library Excel with 2 sheets")
    ap.add_argument("--unknown-txt", default=None, help="Unknown spectrum txt path")
    ap.add_argument("--amide", default=None, choices=["yes", "no"], help="User input: does unknown contain amide feature?")
    ap.add_argument("--top", type=int, default=5, help="Print top-N hits per searched library (default 5)")
    args = ap.parse_args()

    if args.unknown_txt is None:
        args.unknown_txt = input("Enter unknown spectrum txt path: ").strip().strip('"').strip("'")
    if args.amide is None:
        args.amide = input("Does the unknown contain amide feature? (yes/no): ").strip().lower()

    if args.amide not in ("yes", "no"):
        raise SystemExit("Invalid amide flag. Use yes/no.")
    if not os.path.exists(args.library_xlsx):
        raise SystemExit(f"Library file not found: {args.library_xlsx}")
    if not os.path.exists(args.unknown_txt):
        raise SystemExit(f"Unknown txt not found: {args.unknown_txt}")

    lib_amide, lib_non = load_both_libraries(args.library_xlsx)

    x_u, y_u = read_unknown_txt(args.unknown_txt)
    y_u_win = unknown_to_gridwin(x_u, y_u)

    # Always match required library
    best_non = None
    top_non: List[Hit] = []
    best_amide = None
    top_amide: List[Hit] = []

    if args.amide == "yes":
        best_amide, top_amide = match_one_library(y_u_win, lib_amide, "amide", top_n=args.top)
        # Only if amide-best < 0.75, do the fallback search in non-amide
        if best_amide.r < TH_CLASSIFIED:
            best_non, top_non = match_one_library(y_u_win, lib_non, "non-amide", top_n=args.top)
    else:
        best_non, top_non = match_one_library(y_u_win, lib_non, "non-amide", top_n=args.top)

    # choose final
    if args.amide == "yes":
        final = choose_final_hit("yes", best_amide, best_non)
    else:
        final = choose_final_hit("no", best_amide=None, best_non=best_non)  # type: ignore

    status = classify(final.r)

    print("\n===== Identification Result =====")
    print(f"Window: {WN_MIN:.0f}–{WN_MAX:.0f} cm^-1 (fixed grid: start={GRID_START}, step={GRID_STEP})")
    print(f"User amide input: {args.amide}")
    print(f"Final library used: {final.library}")
    print(f"Best polymer: {final.polymer}")
    print(f"Best curve_id: {final.curve_id}")
    print(f"Pearson r: {final.r:.6f}")
    print(f"Status: {status}")

    if args.amide == "yes":
        print("\n----- Primary (amide) best -----")
        print(f"{best_amide.polymer}  r={best_amide.r:.6f}  ({best_amide.curve_id})")
        print("Top hits (amide):")
        for i, h in enumerate(top_amide, 1):
            print(f"{i:02d}. {h.polymer:<25s} r={h.r:.6f}  status={classify(h.r):<12s} ({h.curve_id})")

        if best_non is not None:
            print("\n----- Fallback (non-amide) best (triggered because amide r < 0.75) -----")
            print(f"{best_non.polymer}  r={best_non.r:.6f}  ({best_non.curve_id})")
            print("Top hits (non-amide):")
            for i, h in enumerate(top_non, 1):
                print(f"{i:02d}. {h.polymer:<25s} r={h.r:.6f}  status={classify(h.r):<12s} ({h.curve_id})")
        else:
            print("\n(Fallback non-amide search not triggered because amide best r ≥ 0.75.)")
    else:
        print("\nTop hits (non-amide):")
        for i, h in enumerate(top_non, 1):
            print(f"{i:02d}. {h.polymer:<25s} r={h.r:.6f}  status={classify(h.r):<12s} ({h.curve_id})")


if __name__ == "__main__":
    main()
