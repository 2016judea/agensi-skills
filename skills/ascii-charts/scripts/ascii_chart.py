"""
Render charts as monospace Unicode-block text for embedding directly in a
Substack post — no third-party charting service, no branding footer, renders
identically anywhere a monospace font renders (a fenced code block in
Markdown, a <pre> tag in HTML).

See SKILL.md for the chart-type menu, embedding
rules, and the character set.

    from ascii_chart import bar, range_bar, render

    rows = [
        ("Gas fill-up", bar(5, 45, 24), "5 min"),
        ("DC fast charge", bar(45, 45, 24), "45 min"),
    ]
    print(render(rows, axis=("0", "45 min")))

    row = ("DC fast charger", range_bar(100, 300, 300, 24, open_ended=True), "$100K-$300K+")
    print(render([row]))

Run this file directly (`python3 scripts/ascii_chart.py`) to print
one example of every chart type for a quick sanity check.
"""

import math

FILLED = "█"  # █
TRACK = "░"  # ░

# Monospace character cells are taller than they are wide — circles and
# angles need this correction factor on the column axis or they render as
# ellipses. Measured directly (not assumed) against the embedding CSS this
# skill actually prescribes (15px font, 1.5 line-height, SF Mono/Menlo
# stack) in a headless-Chrome render of a <pre>-embedding page: real cell ratio is
# ~2.49 (22.5px row height / 9.03px column width), not the old 2.0 —
# verify again if the embedding CSS's font-size or line-height changes.
ASPECT = 2.49


def _fmt(v: float) -> str:
    v = round(v, 1)
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


# ---------------------------------------------------------------------------
# Bar charts (magnitude comparison, min-max range)
# ---------------------------------------------------------------------------

def bar(value: float, max_value: float, width: int = 18) -> str:
    """A single magnitude bar, value scaled against max_value, filled from 0."""
    filled = round(value / max_value * width) if max_value else 0
    return FILLED * filled + TRACK * (width - filled)


def range_bar(start: float, end: float, scale_max: float, width: int = 18, open_ended: bool = False) -> str:
    """A single min-max range bar (e.g. $100K-$300K), scaled against 0..scale_max.

    open_ended appends a trailing '+' to flag the real number can run higher
    than `end` — don't stretch the bar itself to fake a number you don't have.
    """
    start_pos = round(start / scale_max * width) if scale_max else 0
    end_pos = round(end / scale_max * width) if scale_max else 0
    row = TRACK * start_pos + FILLED * (end_pos - start_pos) + TRACK * (width - end_pos)
    return row + "+" if open_ended else row


def render(rows: list[tuple[str, str, str]], axis: tuple[str, str] | None = None,
           bracket: str | None = None, label_pad: int = 3, value_pad: int = 2) -> str:
    """Align (label, bar_string, value_str) rows into a monospace block.

    axis, if given, is (start_label, end_label) printed under the bars,
    left- and right-aligned to the same columns as the bars above.
    bracket, if given, is a pre-built bar-width string (see gap_bracket())
    printed under the bars with the same label padding — for spanning a
    gap between two of the rows above.
    """
    label_width = max(len(label) for label, _, _ in rows) + label_pad
    value_width = max(len(value) for _, _, value in rows) + value_pad

    lines = [
        label.ljust(label_width) + bar_str + value.rjust(value_width)
        for label, bar_str, value in rows
    ]

    if bracket:
        lines.append(" " * label_width + bracket)

    if axis:
        start_label, end_label = axis
        bar_width = len(rows[0][1])
        axis_line = " " * label_width + start_label.ljust(bar_width - len(end_label)) + end_label
        lines.append(axis_line)

    return "\n".join(lines)


def bullet(value: float, scale_max: float, target: float | None = None,
           benchmark: tuple[float, float] | None = None, width: int = 18) -> str:
    """A bullet chart row: a solid bar for the measured value, drawn over an
    optional shaded benchmark/"normal" band, with an optional target tick.
    Feed the result into render() like bar()/range_bar(). Answers "am I
    inside normal, and how far from target" in one glance — the single bar
    is the actual measure; the band is context, not a second bar."""
    def pos(v):
        return max(0, min(width - 1, round(v / scale_max * (width - 1))))

    cells = [TRACK] * width
    if benchmark:
        lo, hi = pos(benchmark[0]), pos(benchmark[1])
        for i in range(lo, hi + 1):
            cells[i] = "▒"
    for i in range(0, pos(value) + 1):
        cells[i] = FILLED
    if target is not None:
        cells[pos(target)] = "┃"
    return "".join(cells)


def gap_bracket(a: float, b: float, scale_max: float, width: int = 18, label: str | None = None) -> str:
    """A bracket line spanning between two bar-end positions on the same
    scale_max/width used for the bar() rows above it — pass the result to
    render(bracket=...). Use to call out the gap between a client bar and a
    benchmark bar explicitly, instead of leaving the reader to eyeball it."""
    lo = round(min(a, b) / scale_max * width)
    hi = round(max(a, b) / scale_max * width)
    if hi <= lo:
        return ""
    text = label or f"gap: {abs(b - a):,.0f}"
    line = [" "] * width
    line[lo] = "└"
    line[hi] = "┘"
    for i in range(lo + 1, hi):
        line[i] = "─"
    span = hi - lo - 1
    if span >= len(text) + 2:
        start = lo + 1 + (span - len(text)) // 2
        for i, ch in enumerate(text):
            line[start + i] = ch
    return "".join(line)


def star_histogram(counts: list[tuple[int, int]], width: int = 18) -> str:
    """A rating-distribution histogram, e.g. Google/Yelp's 5-star breakdown.
    counts is [(stars, count), ...] — pass in whatever order you want it
    printed (usually 5 down to 1). Filled/open star glyphs double as the
    row label, so there's no need to spell out "5 stars" in text."""
    total = sum(c for _, c in counts)
    max_count = max(c for _, c in counts)
    rows = [
        (("★" * stars).ljust(5, "☆"), bar(count, max_count, width), f"{count/total*100:.0f}%")
        for stars, count in counts
    ]
    return render(rows)


# ---------------------------------------------------------------------------
# Heatmaps
# ---------------------------------------------------------------------------

HEAT_CHARS = "·░▒▓█"  # · (not space) for the lowest level, so a "quiet" cell
                      # still reads as an intentional part of the grid


def heatmap(matrix: list[list[float]], row_labels: list[str],
            col_ticks: list[tuple[int, str]] | None = None) -> str:
    """A day×hour (or any category×category) shade heatmap — the "when are
    you busy/dead" chart. Normalizes across the *whole* matrix (not
    per-row) so shading is comparable across rows. col_ticks, if given, is
    [(column_index, label), ...] printed on an axis row below — e.g.
    [(0, "12am"), (6, "6am"), (12, "12pm"), (18, "6pm")] for a 24-column
    hour grid; there's no auto-spacing, so pick positions that won't
    collide for the labels you pass."""
    flat = [v for row in matrix for v in row]
    lo, hi = min(flat), max(flat)
    span = (hi - lo) or 1
    label_width = max(len(l) for l in row_labels) + 1
    ncols = len(matrix[0])

    lines = []
    for label, row in zip(row_labels, matrix):
        cells = "".join(HEAT_CHARS[min(4, int((v - lo) / span * 5))] for v in row)
        lines.append(label.ljust(label_width) + cells)

    if col_ticks:
        axis = [" "] * ncols
        for idx, tick_label in col_ticks:
            for i, ch in enumerate(tick_label):
                if 0 <= idx + i < ncols:
                    axis[idx + i] = ch
        lines.append(" " * label_width + "".join(axis))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Line charts
# ---------------------------------------------------------------------------

SPARK_CHARS = "▁▂▃▄▅▆▇█"


def sparkline(values: list[float]) -> str:
    """A single-row trend indicator — for one inline sentence, not a full chart."""
    min_v, max_v = min(values), max(values)
    span = (max_v - min_v) or 1
    return "".join(SPARK_CHARS[min(7, int((v - min_v) / span * 8))] for v in values)


def _line_grid(rows_per_col: list[int], height: int) -> list[list[str]]:
    """Connect consecutive (already row-scaled) columns with box-drawing
    characters — flat '─' when the value doesn't change, a '╭'/'╮'/'╰'/'╯'
    + '│' vertical jump when it does. Shared by line_chart and the trend
    line in scatter_with_trend."""
    width = len(rows_per_col) - 1
    grid = [[" "] * width for _ in range(height)]
    for x in range(width):
        y0, y1 = rows_per_col[x], rows_per_col[x + 1]
        if y0 == y1:
            grid[y0][x] = "─"
        elif y0 > y1:  # value rising (row 0 = top = max)
            grid[y1][x] = "╭"
            grid[y0][x] = "╯"
            for y in range(y1 + 1, y0):
                grid[y][x] = "│"
        else:  # value falling
            grid[y0][x] = "╮"
            grid[y1][x] = "╰"
            for y in range(y0 + 1, y1):
                grid[y][x] = "│"
    return grid


def line_chart(values: list[float], height: int = 10, x_labels: tuple[str, str] | None = None) -> str:
    """A connected line chart. Width is fixed at len(values) - 1 columns (one
    per segment between points) — that's the plain-text-line-drawing tradeoff,
    not a bug: there's no character for an arbitrary in-between slope, so each
    transition needs its own column. x_labels, if given, is (first, last),
    printed left/right on the axis row (exact positions in between aren't
    labeled — say them in the surrounding prose instead)."""
    if len(values) < 2:
        raise ValueError("line_chart needs at least 2 points")

    min_v, max_v = min(values), max(values)
    span = (max_v - min_v) or 1
    rows = [round((max_v - v) / span * (height - 1)) for v in values]
    grid = _line_grid(rows, height)

    label_width = max(len(_fmt(max_v)), len(_fmt(min_v))) + 1
    lines = []
    for r in range(height):
        if r == 0:
            label = _fmt(max_v).rjust(label_width)
        elif r == height - 1:
            label = _fmt(min_v).rjust(label_width)
        else:
            label = " " * label_width
        lines.append(label + " " + "".join(grid[r]))

    if x_labels:
        first, last = x_labels
        width = len(values) - 1
        lines.append(" " * (label_width + 1) + first.ljust(width - len(last)) + last)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Venn diagrams (2 or 3 sets)
# ---------------------------------------------------------------------------

def venn(labels: list[str], width: int = 50, height: int = 22) -> tuple[str, str]:
    """Rasterize 2 or 3 overlapping circles onto a character grid. Each region
    is filled with a digit (a bitmask of which sets it belongs to — 1, 2, 4
    for the plain sets, 3/5/6 for pairwise overlaps, 7 for all three) rather
    than trying to fit label text inside a curved boundary, which doesn't
    survive monospace rendering. Returns (diagram, legend) — print both, the
    legend maps each digit back to the real label combination.
    """
    n = len(labels)
    if n not in (2, 3):
        raise ValueError("venn supports 2 or 3 sets")

    r_row = height * 0.34
    r_col = r_row * ASPECT
    cy, cx = height / 2, width / 2

    if n == 2:
        d = r_col * 0.85
        centers = [(cy, cx - d / 2), (cy, cx + d / 2)]
    else:
        d_row = r_row * 0.55
        d_col = r_col * 0.55
        centers = [
            (cy - d_row, cx),
            (cy + d_row * 0.8, cx - d_col),
            (cy + d_row * 0.8, cx + d_col),
        ]

    grid = [[" "] * width for _ in range(height)]
    for row in range(height):
        for col in range(width):
            mask = 0
            for i, (crow, ccol) in enumerate(centers):
                dy = (row - crow) / r_row
                dx = (col - ccol) / r_col
                if dx * dx + dy * dy <= 1:
                    mask |= 1 << i
            if mask:
                grid[row][col] = str(mask)

    diagram = "\n".join("".join(r) for r in grid)

    present = sorted({int(c) for row in grid for c in row if c != " "})
    legend_lines = []
    for mask in present:
        parts = [labels[i] for i in range(n) if mask & (1 << i)]
        marker = " <- all of them" if mask == (1 << n) - 1 else ""
        legend_lines.append(f"{mask} = {' + '.join(parts)}{marker}")
    legend = "\n".join(legend_lines)

    return diagram, legend


# ---------------------------------------------------------------------------
# Pie / donut charts
# ---------------------------------------------------------------------------

SLICE_CHARS = ["█", "▓", "▒", "░", "▚", "▞", "▤", "▥"]


def pie(slices: list[tuple[str, float]], radius: int = 10, inner_ratio: float = 0.0,
        center_text: str | None = None) -> tuple[str, str]:
    """Rasterize a circle (or, with inner_ratio > 0, a donut) sliced by angle
    in proportion to each value, starting at 12 o'clock and going clockwise
    — the standard pie-chart convention. Each slice gets its own character
    from SLICE_CHARS (never reused on an adjacent slice for small counts) so
    boundaries stay legible without color. Returns (diagram, legend); legend
    has the real percentage per slice. center_text, for a donut, is centered
    in the hollow middle (e.g. a total count) — the one thing an ASCII donut
    can do that a real one usually wastes on a plain circle.
    """
    total = sum(v for _, v in slices)
    r_row = float(radius)
    r_col = r_row * ASPECT
    height = int(r_row * 2) + 1
    width = int(r_col * 2) + 1
    cy, cx = height / 2, width / 2
    inner_r_row = r_row * inner_ratio
    inner_r_col = r_col * inner_ratio

    bounds = []
    acc = 0.0
    for _, v in slices:
        start = acc / total * 360
        acc += v
        end = acc / total * 360
        bounds.append((start, end))
    bounds[-1] = (bounds[-1][0], 360.0)

    grid = [[" "] * width for _ in range(height)]
    for row in range(height):
        for col in range(width):
            dy, dx = (row - cy) / r_row, (col - cx) / r_col
            if dx * dx + dy * dy > 1:
                continue
            if inner_ratio > 0:
                idy, idx = (row - cy) / inner_r_row, (col - cx) / inner_r_col
                if idx * idx + idy * idy <= 1:
                    continue
            angle = (90 - math.degrees(math.atan2(cy - row, col - cx))) % 360
            for i, (a0, a1) in enumerate(bounds):
                if a0 <= angle < a1:
                    grid[row][col] = SLICE_CHARS[i % len(SLICE_CHARS)]
                    break

    if center_text:
        r = height // 2
        start_c = max(0, width // 2 - len(center_text) // 2)
        for i, ch in enumerate(center_text):
            if start_c + i < width:
                grid[r][start_c + i] = ch

    diagram = "\n".join("".join(r) for r in grid)
    legend = "\n".join(
        f"{SLICE_CHARS[i % len(SLICE_CHARS)]} {label} - {v/total*100:.0f}%"
        for i, (label, v) in enumerate(slices)
    )
    return diagram, legend


def donut(slices: list[tuple[str, float]], radius: int = 10, inner_ratio: float = 0.5,
          center_text: str | None = None) -> tuple[str, str]:
    """A pie chart with a hollow center — see pie() for everything else."""
    return pie(slices, radius=radius, inner_ratio=inner_ratio, center_text=center_text)


# ---------------------------------------------------------------------------
# Scatter charts
# ---------------------------------------------------------------------------

def _scale(values: list[float], lo: float, hi: float, size: int, invert: bool = False) -> list[int]:
    span = (hi - lo) or 1
    scaled = [round((v - lo) / span * (size - 1)) for v in values]
    return [size - 1 - s for s in scaled] if invert else scaled


def scatter(points: list[tuple[float, float]], width: int = 50, height: int = 20,
            marker: str = "●") -> str:
    """Plot (x, y) points on a grid. Two points that round to the same cell
    just overwrite — for the point counts this is built for (a few dozen at
    most) that's an acceptable, honest simplification, not a bug to fix."""
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    cols = _scale(xs, x_min, x_max, width)
    rows = _scale(ys, y_min, y_max, height, invert=True)

    grid = [[" "] * width for _ in range(height)]
    for col, row in zip(cols, rows):
        grid[row][col] = marker

    label_width = max(len(_fmt(y_max)), len(_fmt(y_min))) + 1
    lines = []
    for r in range(height):
        label = _fmt(y_max).rjust(label_width) if r == 0 else (
            _fmt(y_min).rjust(label_width) if r == height - 1 else " " * label_width)
        lines.append(label + " " + "".join(grid[r]))
    lines.append(" " * (label_width + 1) + _fmt(x_min).ljust(width - len(_fmt(x_max))) + _fmt(x_max))
    return "\n".join(lines)


def scatter_with_trend(points: list[tuple[float, float]], width: int = 50, height: int = 20,
                        marker: str = "●") -> str:
    """scatter() plus a least-squares trend line, drawn with the same
    box-drawing connector as line_chart. The line is computed independently
    per column (not just at the data points) and drawn first; scatter markers
    are drawn on top so real data always stays visible over the fit."""
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    n = len(points)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in points)
    denom = n * sxx - sx * sx
    if denom == 0:
        slope, intercept = 0.0, sy / n
    else:
        slope = (n * sxy - sx * sy) / denom
        intercept = (sy - slope * sx) / n

    fitted_y = []
    for c in range(width):
        x_at_col = x_min + (x_max - x_min) * c / (width - 1) if width > 1 else x_min
        fitted_y.append(slope * x_at_col + intercept)
    fit_span = (y_max - y_min) or 1
    fit_rows = [
        max(0, min(height - 1, round((y_max - fy) / fit_span * (height - 1))))
        for fy in fitted_y
    ]
    line = _line_grid(fit_rows, height)
    grid = [[" "] * width for _ in range(height)]
    for c in range(width - 1):
        for r in range(height):
            if line[r][c] != " ":
                grid[r][c] = line[r][c]

    cols = _scale(xs, x_min, x_max, width)
    rows = _scale(ys, y_min, y_max, height, invert=True)
    for col, row in zip(cols, rows):
        grid[row][col] = marker

    label_width = max(len(_fmt(y_max)), len(_fmt(y_min))) + 1
    lines = []
    for r in range(height):
        label = _fmt(y_max).rjust(label_width) if r == 0 else (
            _fmt(y_min).rjust(label_width) if r == height - 1 else " " * label_width)
        lines.append(label + " " + "".join(grid[r]))
    lines.append(" " * (label_width + 1) + _fmt(x_min).ljust(width - len(_fmt(x_max))) + _fmt(x_max))
    return "\n".join(lines)


if __name__ == "__main__":
    print("--- bar ---")
    rows = [("Gas fill-up", bar(5, 45, 24), "5 min"), ("DC fast charge", bar(45, 45, 24), "45 min")]
    print(render(rows, axis=("0", "45 min")))

    print("\n--- range_bar ---")
    print(render([("DC fast charger", range_bar(100, 300, 300, 24, open_ended=True), "$100k-$300k+")]))

    print("\n--- sparkline ---")
    print(sparkline([3, 5, 4, 8, 12, 10, 15, 14, 18]))

    print("\n--- line_chart ---")
    print(line_chart([120, 135, 128, 150, 175, 190, 205, 198, 220], height=10, x_labels=("Jan", "Sep")))

    print("\n--- venn (3-set) ---")
    d, l = venn(["Highway exit", "Big store", "Grid capacity"])
    print(d)
    print(l)

    print("\n--- pie ---")
    d, l = pie([("Coffee", 40), ("Hot food", 25), ("Drinks", 20), ("Lottery", 15)], radius=9)
    print(d)
    print(l)

    print("\n--- donut ---")
    d, l = donut([("Coffee", 40), ("Hot food", 25), ("Drinks", 20), ("Lottery", 15)], radius=9, center_text="247")
    print(d)
    print(l)

    print("\n--- scatter ---")
    import random
    random.seed(0)
    pts = [(x, x * 1.5 + random.uniform(-8, 8)) for x in range(1, 30)]
    print(scatter(pts))

    print("\n--- scatter_with_trend ---")
    print(scatter_with_trend(pts))

    print("\n--- bullet ---")
    rows = [("Avg rating", bullet(4.2, 5.0, target=4.7, benchmark=(3.8, 4.5), width=24), "4.2 (target 4.7)")]
    print(render(rows, axis=("0", "5.0")))

    print("\n--- gap_bracket ---")
    rows = [("You", bar(42000, 60000, 24), "$42,000"), ("Market median", bar(58000, 60000, 24), "$58,000")]
    print(render(rows, bracket=gap_bracket(42000, 58000, 60000, 24)))

    print("\n--- star_histogram ---")
    print(star_histogram([(5, 61), (4, 22), (3, 9), (2, 4), (1, 4)]))

    print("\n--- heatmap ---")
    random.seed(1)
    matrix = [[max(0, 8 - abs(h - (12 if d < 5 else 19)) + random.uniform(-1, 1)) for h in range(24)]
              for d in range(7)]
    print(heatmap(matrix, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                  col_ticks=[(0, "12am"), (6, "6am"), (12, "12pm"), (18, "6pm")]))
