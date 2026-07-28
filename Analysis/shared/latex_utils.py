"""
Utilities for post-processing LaTeX table files produced by Stata's estout.
"""
import re


def add_tabular_environment(file_path):
    """Wrap file contents in a LaTeX tabular environment."""
    with open(file_path, 'r') as f:
        content = f.readlines()

    # Determine column count from the first line containing '&'
    for line in content:
        if line.strip() and '&' in line:
            num_columns = line.count('&') + 1
            break
    else:
        print(f"No data lines found in {file_path} — skipping tabular wrap.")
        return

    tabular_start = (
        r"\begin{tabular}{"
        + "l" + "c" * (num_columns - 1)
        + r"}\\[-1.8ex]\hline \hline \\[-1.8ex]"
    )
    tabular_end = r"\\[-1.8ex]\hline \hline \\[-1.8ex] \end{tabular}"

    modified = tabular_start + "\n" + "".join(content) + tabular_end
    with open(file_path, 'w') as f:
        f.write(modified)

    print(f"Tabular environment ({num_columns} cols) added to {file_path}")


def format_latex(file):
    """Replace variable names with LaTeX macro names and clean up table formatting."""
    with open(file, 'rt') as f:
        data = f.read()

    # Variable name substitutions
    data = data.replace('retained', r'\RETAINED')
    data = data.replace('promo', r'\PROMOTED')
    data = data.replace(r'female\_pre\_2004', r'\FEMALExPREIV')
    data = data.replace(r'female\_2004\_2005', r'\FEMALExIVtoV')
    data = data.replace(r'female\_2006\_2007', r'\FEMALExVItoVII')
    data = data.replace(r'female\_2008\_2009', r'\FEMALExVIIItoIX')
    data = data.replace(r'female\_pre\_2010', r'\FEMALExPREX')
    data = data.replace(r'female\_2010\_2011', r'\FEMALExXtoXI')
    data = data.replace(r'female\_2012\_2013', r'\FEMALExXIItoXIII')
    data = data.replace(r'female\_2014\_2015', r'\FEMALExXIVtoXV')
    data = data.replace(r'female\_2016\_2017', r'\FEMALExXVItoXVII')
    data = data.replace(r'female\_2018\_2019', r'\FEMALExXVIIItoXIX')
    data = data.replace(r'female\_post\_2019', r'\FEMALExPOSTXIX')
    data = data.replace(r'female\_2020\_2021', r'\FEMALExXXtoXXI')
    data = data.replace(r'female\_2022\_2023', r'\FEMALExXXIItoXXIII')
    data = data.replace(r'female\_pre\_eq\_1', r'\FEMALExPREEQONE')
    data = data.replace(r'female\_pre\_eq\_2', r'\FEMALExPREEQTWO')
    data = data.replace(r'female\_pre\_eq\_3', r'\FEMALExPREEQTHREE')
    data = data.replace(r'female\_post\_eq', r'\FEMALExPOSTEQ')
    data = data.replace(r'female\_post\_formap', r'\FEMALExPOSTFORMAP')
    data = data.replace(r'female\_post', r'\FEMALExPOST')
    data = data.replace(r'post\_formap', r'\POSTFORMAP')
    data = data.replace(r'post\_eq', r'\POSTEQ')
    data = data.replace(r'pre\_eq\_1', r'\PREEQONE')
    data = data.replace(r'pre\_eq\_2', r'\PREEQTWO')
    data = data.replace(r'pre\_eq\_3', r'\PREEQTHREE')
    data = data.replace('female', r'\FEMALE')
    data = data.replace('topuniv', r'\TOPUNIV')
    data = data.replace(r'top\_university', r'\TOPUNIVERSITY')
    data = data.replace('masterorhigher', r'\MASTERS')
    data = data.replace('api', r'\APIRACE')
    data = data.replace('black', r'\BLACKRACE')
    data = data.replace('other', r'\OTHERRACE')

    # Rule formatting — keep booktabs rules (needed for r@{.}l multicolumn spanning)
    data = data.replace('toprule', 'toprule')  # no-op: keep \toprule
    data = data.replace('bottomrule', 'bottomrule')  # no-op: keep \bottomrule

    # Remove table float wrapper (keep only tabular content)
    data = data.replace('longtable', 'tabular')
    data = data.replace(r'\begin{table}[!htbp] \centering', '')
    data = data.replace(r' \caption{}', '')
    data = data.replace(r'\label{}', '')
    data = data.replace(r'\end{table}', '')

    with open(file, 'wt') as f:
        f.write(data)


def fix_cells_column_spec(file, wide_labels=False):
    r"""Fix tabular column spec for esttab cells("b se") SE-beside format.

    Uses r@{.}l columns for decimal-aligned coefficients (split at the
    decimal point) paired with r columns for parenthesized SEs.  This
    avoids dcolumn's internal-2-column problem that breaks \multicolumn
    spanning while preserving true decimal alignment.

    Transformations applied:
      - Column spec: *{N}{r} → (r@{.}l r) × N
      - Model headers: \multicolumn{2}{c} → \multicolumn{3}{c}
      - Sub-headers: b → \multicolumn{2}{c}{$b$}, se → {se}
      - Data rows: coefficient decimals split (. → &), minus → $-$
      - Stats rows: values wrapped in \multicolumn{2}{r}{...}
    """
    with open(file, 'r') as f:
        tex = f.read()

    # 1. Column spec: *{N}{r} → (r@{.}l r) × N
    tex = re.sub(
        r'\*\{(\d+)\}\{r\}',
        lambda m: r' r@{.}l r' * int(m.group(1)),
        tex
    )
    if wide_labels:
        tex = re.sub(r'\{l ', r'{p{5cm} ', tex, count=1)

    # 2. Model headers: span all 3 columns per model (r@{.}l + r)
    tex = re.sub(r'\\multicolumn\{2\}\{c\}', r'\\multicolumn{3}{c}', tex)

    # 3. Sub-headers: b spans r@{.}l pair, se in r column
    tex = re.sub(r'&\s+b\s+', r'& \\multicolumn{2}{c}{$b$} ', tex)
    tex = re.sub(r'&\s+se', r'& \\multicolumn{1}{c}{se}', tex)

    # 4. Process data rows line-by-line: split decimals, handle empties,
    #    wrap stats values — all in one pass.
    new_lines = []
    in_stats = False
    midrule_count = 0
    for line in tex.split('\n'):
        if '\\midrule' in line:
            midrule_count += 1
            # Stats section starts after the 2nd midrule
            if midrule_count >= 2:
                in_stats = True
            new_lines.append(line)
            continue
        # Skip non-data lines
        if '&' not in line or '\\hline' in line \
                or '\\multicolumn' in line or 'shortstack' in line:
            new_lines.append(line)
            continue
        # Split into cells and process pairs (coeff, se)
        parts = line.split('&')
        label = parts[0]
        cells = parts[1:]
        out = [label]
        i = 0
        while i < len(cells):
            cell = cells[i]
            if in_stats:
                # Stats row: split decimal values for alignment, wrap others
                stripped = cell.strip().rstrip('\\\\').strip()
                m_stat = re.match(r'^(\s*)([-]?\d+)\.(\d+)\s*$', cell.rstrip('\\\\').rstrip())
                if m_stat:
                    # Decimal value (e.g. 0.005) — split for alignment
                    pre, left, right = m_stat.groups()
                    out.append(pre + left)
                    out.append(right)
                elif stripped:
                    # Non-decimal value (e.g. 713,607 or C,Y,E)
                    out.append(' \\multicolumn{2}{r}{' + stripped + '} ')
                else:
                    # Empty cell
                    out.append(' \\multicolumn{2}{c}{} ')
            else:
                # Data row: try to split at decimal
                m = re.match(r'^(\s*)([-]?\d+)\.(\d+.*)$', cell)
                if m:
                    pre, left, right = m.groups()
                    left = re.sub(r'^-', '$-$', left)
                    out.append(pre + left)
                    out.append(right)
                elif cell.strip() == '':
                    # Empty coefficient cell
                    out.append(' \\multicolumn{2}{c}{} ')
                else:
                    # Non-decimal value (shouldn't happen in data)
                    out.append(cell)
                    out.append('')
            # Next cell is the SE
            i += 1
            if i < len(cells):
                out.append(cells[i])
            i += 1
        new_lines.append('&'.join(out))
    tex = '\n'.join(new_lines)

    with open(file, 'w') as f:
        f.write(tex)
