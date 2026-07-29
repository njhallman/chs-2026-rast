"""
Produces: LaTeX/Tables/VariableDefinitions.tex
Appendix table defining all regression variables.
No data loading required.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from shared.paths import tables_dir

print("Creating VariableDefinitions.tex")

with open(f"{tables_dir}/VariableDefinitions.tex", 'w') as fout:
    fout.write(r"\begin{longtable}{>{\raggedright\arraybackslash}p{3cm}p{13cm}}")
    fout.write("\n\n")

    fout.write(r"%----- Header/Footer Setup -----%")
    fout.write("\n")
    fout.write(r"\captionsetup{labelfont=bf, singlelinecheck=off, justification=raggedright, labelsep=none}")
    fout.write("\n")
    fout.write(r"\caption{: Variable definitions}")
    fout.write("\n\n")

    fout.write(r"\\[-1.8ex]\hline \hline \\[-1.8ex]")
    fout.write("\n")
    fout.write(r"\endfirsthead")
    fout.write("\n\n")

    fout.write(r"\multicolumn{2}{l}%")
    fout.write("\n")
    fout.write(r"{{\textit{Continued from previous page}}} \\")
    fout.write("\n")
    fout.write(r"\midrule")
    fout.write("\n")
    fout.write(r"\endhead")
    fout.write("\n\n")

    fout.write(r"\multicolumn{2}{r}{{\textit{Continued on next page}}}")
    fout.write("\n")
    fout.write(r"\endfoot")
    fout.write("\n\n")

    fout.write(r"\multicolumn{2}{r}{{ }}")
    fout.write("\n")
    fout.write(r"\endlastfoot")
    fout.write("\n\n")

    fout.write(r"%----- Variable Definitions -----%")
    fout.write("\n\n")

    fout.write(r"\RETAINED & An indicator variable set equal to 1 if the professional remains with the firm the following year, 0 otherwise. \\")
    fout.write("\n")
    fout.write(r"\midrule")
    fout.write("\n\n")

    fout.write(r"\PROMOTED & An indicator variable set equal to 1 if the auditor is promoted to a higher rank in the following year, 0 otherwise. \\")
    fout.write("\n")
    fout.write(r"\midrule")
    fout.write("\n\n")

    fout.write(r"\FEMALE & An indicator variable set equal to 1 if the professional is classified as female by the \textit{sex\_predicted} field Revelio, and 0 otherwise. \\")
    fout.write("\n")
    fout.write(r"\midrule")
    fout.write("\n\n")

    fout.write(r"\MASTERS & An indicator variable set equal to 1 if the auditor holds a master's degree or higher, and 0 otherwise, according to the \textit{highest\_dgree} field in the Revelio data \\")
    fout.write("\n")
    fout.write(r"\midrule")
    fout.write("\n\n")

    fout.write(r"\TOPUNIV & An indicator variable set equal to 1 if the professional attended a top university as defined by \textcite{FGH2022}.\\")
    fout.write("\n")
    fout.write(r"\midrule")
    fout.write("\n\n")

    fout.write(r"\APIRACE & An indicator variable set equal to 1 if the professional is classified as API (i.e., Asian and Pacific Islander) by the \textit{ethnicity\_predicted} field in Revelio, 0 otherwise.\\")
    fout.write("\n")
    fout.write(r"\midrule")
    fout.write("\n\n")

    fout.write(r"\BLACKRACE & An indicator variable set equal to 1 if the professional is classified as Black by the \textit{ethnicity\_predicted} field in Revelio, 0 otherwise.\\")
    fout.write("\n")
    fout.write(r"\midrule")
    fout.write("\n\n")

    fout.write(r"\OTHERRACE & An indicator variable set equal to 1 if the professional is classified as any ethnicity other than API, Black, or White by the \textit{ethnicity\_predicted} field in Revelio, 0 otherwise.\\")
    fout.write("\n")
    fout.write(r"\midrule")
    fout.write("\n\n")

    fout.write(r"\POSTFORMAP & An indicator variable set equal to 1 for calendar years 2015 and later, when the PCAOB's Form AP disclosure requirement was in effect.\\")
    fout.write("\n")
    fout.write(r"\midrule")
    fout.write("\n\n")

    fout.write(r"AC Female \% & The mean share of female audit committee members at Big~4 audit clients, aggregated to the CBSA-firm-year level. Constructed from BoardEx director data linked to Audit Analytics engagement data.\\")
    fout.write("\n")
    fout.write(r"\midrule")
    fout.write("\n\n")

    fout.write(r"Gender Keywords & The standardized count of gender-related keywords in SEC proxy statements (DEF~14A) filed by Big~4 audit clients, aggregated to the CBSA-firm-year level. Extracted from proxy statement text via the local-edgar archive.\\")
    fout.write("\n")
    fout.write(r"\midrule")
    fout.write("\n\n")

    fout.write(r"Salary \% Change & The percentage change in salary from the auditor's final Big~4 position to their first post-Big~4 position. Computed as $(S_{next} - S_{B4}) / S_{B4} \times 100$. Available only for leavers (\RETAINED\ = 0) with an observed next position and valid salary data. Winsorized at the 1st and 99th percentiles.\\")
    fout.write("\n")
    fout.write(r"\midrule")
    fout.write("\n\n")

    fout.write(r"Gap Days & The number of calendar days between the end of the auditor's Big~4 position and the start of their next position. Available only for leavers (\RETAINED\ = 0) with an observed next position. Winsorized at the 1st and 99th percentiles. Log-transformed in regressions.\\")
    fout.write("\n\n")

    fout.write(r"\\[-1.8ex]\hline \hline \\[-1.8ex]")
    fout.write("\n\n")

    fout.write(r"\label{table:variableDefinitions}")
    fout.write("\n")
    fout.write(r"\end{longtable}")
    fout.write("\n\n\n")

print(f"Saved {tables_dir}/VariableDefinitions.tex")
