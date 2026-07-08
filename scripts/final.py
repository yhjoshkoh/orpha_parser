import argparse
import glob
import os
from pathlib import Path
import pandas as pd


def find_cls_csv(in_dir):
    return sorted(glob.glob(os.path.join(in_dir, "orphanet_*_classifications_*_rawdump.csv")))

def find_csv(in_dir, pattern):
    return sorted(glob.glob(os.path.join(in_dir, pattern)))


def main():
    """
    Finds rawdump CSV files and process them into final CSV files.
    Classification files are used as the base to merge other files.
    """
    parser = argparse.ArgumentParser(
        description="Merge other rawdump CSVs into classification CSVs."
    )
    parser.add_argument("-i","--input", required=True, help="Rawdump directory.")
    parser.add_argument("-o","--output", required=True, help="Output CSV directory")
    parser.add_argument("-H","--headers", nargs= "+", required=False, help="List of headers to include.")

    args = parser.parse_args()
    in_dir = Path(args.input)
    out_dir = Path(args.output)
    headers = args.headers

    rd_alignment = pd.read_csv(find_csv(in_dir, "*_alignment_rawdump.csv")[0], dtype=str)
    rd_alignment = rd_alignment.rename(columns={"OMIM": "OMIM_disorder"})
    rd_gene_disease = pd.read_csv(find_csv(in_dir, "*_gene_disease_associations_rawdump.csv")[0], dtype=str)
    rd_gene_disease = rd_gene_disease.rename(columns={"OMIM": "OMIM_gene"})
    rd_phenotypes = pd.read_csv(find_csv(in_dir, "*_phenotypes_rawdump.csv")[0], dtype=str)
    rd_functional = pd.read_csv(find_csv(in_dir, "*_functional_consequences_rawdump.csv")[0], dtype=str)
    rd_epidemiology = pd.read_csv(find_csv(in_dir, "*_epidemiology_rawdump.csv")[0], dtype=str)
    rd_natural_history = pd.read_csv(find_csv(in_dir, "*_natural_history_rawdump.csv")[0], dtype=str)

    for cls in find_cls_csv(in_dir):
        df_cls = pd.read_csv(cls, dtype=str)
        df_cls = df_cls[df_cls["IsLeaf"] == "1"]

        # Collapse to 1 row per OrphaCode: the classification structure is a DAG
        # (classification_parser.py), so the same OrphaCode can be a leaf under many
        # parent paths -> df_cls here is still "1 row per (OrphaCode, path)". Left-merging
        # that against gene_disease_associations (many rows per OrphaCode) on OrphaCode
        # alone would cartesian-product explode. Join path-dependent columns with "; "
        # (doesn't collide with ClassificationPath's own " > " segment delimiter); take
        # the first row for the rest, which are identical across a disorder's duplicate rows.
        path_cols = ["OrphaCodePath", "ClassificationPath", "ClassificationTypes", "ClassificationDepth"]
        first_cols = [c for c in df_cls.columns if c not in path_cols]

        agg_rows = []
        for _, sub in df_cls.groupby("OrphaCode", dropna=False, sort=False):
            base = {c: sub.iloc[0][c] for c in first_cols}
            for c in path_cols:
                base[c] = "; ".join(str(v) for v in sub[c].tolist())
            agg_rows.append(base)
        df_cls = pd.DataFrame(agg_rows)
        if not df_cls.empty:
            df_cls = df_cls[first_cols + path_cols]

        def _merge_left(base_df, other_df):
            overlap = [c for c in other_df.columns if c in base_df.columns and c != "OrphaCode"]
            if overlap:
                other_df = other_df.drop(columns=overlap)
            return base_df.merge(other_df, how="left", on="OrphaCode")

        df_merged = _merge_left(df_cls, rd_alignment)
        df_merged = _merge_left(df_merged, rd_gene_disease)
        df_merged = _merge_left(df_merged, rd_phenotypes)
        df_merged = _merge_left(df_merged, rd_functional)
        df_merged = _merge_left(df_merged, rd_epidemiology)
        df_merged = _merge_left(df_merged, rd_natural_history)

        if headers is not None:
            keep = [h for h in headers if h in df_merged.columns]
            if "OMIM" in headers:
                disID_idx = keep.index("DisorderId")
                keep.insert(disID_idx,"OMIM_disorder")
                gsymbol_idx = keep.index("GeneSymbol")
                keep.insert(gsymbol_idx,"OMIM_gene")
                if "Ensembl" in headers:
                    keep.remove("Ensembl")
                keep.insert(gsymbol_idx,"Ensembl")

        

            if "OMIM" not in headers:
                if "Ensembl" in headers and "GeneSymbol" in keep:
                    gsymbol_idx = keep.index("GeneSymbol")
                    keep.remove("Ensembl")
                    keep.insert(gsymbol_idx, "Ensembl")
            df_merged = df_merged[keep]
        

        df_merged = df_merged.drop(columns=["OMIM"], errors="ignore")


        out_path = out_dir / f"{Path(cls).stem.replace('_classifications','').replace('_rawdump', '_merged')}.csv"
        df_merged.to_csv(out_path, index=False)
    
if __name__ == "__main__":
    main()
