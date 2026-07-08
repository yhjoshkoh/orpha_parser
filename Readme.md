# orpha_parser

Parses Orphanet Scientific Knowledge XML files into per-category CSVs enriched with gene,
phenotype, epidemiology, natural-history, and functional-consequence data.

**Pipeline:** Orphanet `en_product*.xml` files → per-source rawdump CSVs → merged, annotated CSV per disease category

---

## Setup

No `requirements.txt`/`environment.yml` is checked in yet — install directly:

```bash
conda create -n orpha_parser -c conda-forge python=3.12 snakemake pandas
conda activate orpha_parser
```

The parsers use only the Python standard library's `xml.etree.ElementTree` for XML parsing (no
`lxml` dependency) plus `pandas` for the CSV/merge steps.

**Source XML files are not included in this repository.** See [`sources/sources.md`](sources/sources.md) for
download instructions and data citation.

---

## Language

Only use the **English-language** Orphanet product files (`en_product*.xml`). The parsers do not
filter by `lang="en"` internally — they take the first matching element/text as-is, so a
non-English source file would silently produce wrong-language values instead of falling back
correctly.

---

## Config (`config/config.yaml`)

| Field | Purpose |
|---|---|
| `run_name` | Version tag for this run (recommended: Orphanet release date, `YYMMDD`). Included in output directory/file names. |
| `ROOT` | Base directory. The Snakefile builds `os.path.join(ROOT, run_name)` as the working root. |
| `inputs.in_root` | Directory (under the run root) holding the 6 `XML_MAP` source XMLs. |
| `inputs.classification_dir` | Subdirectory (under `in_root`) holding the `CLS_MAP` classification XMLs. |
| `outputs.out_root` / `outputs.rawdump_dir` / `outputs.final_dir` | Output directory names for raw dumps and merged/processed CSVs. |
| `script_dir` | Absolute path to this repo's `scripts/` directory, used by every rule's shell command. |
| `log_dir` | Optional; defaults to `{out_root}/log` if unset. |
| `HEADERS_TO_KEEP` | Column allowlist (and order) for the final merged CSVs. If unset, all rawdump columns are kept. See **Output** below for the OMIM split behavior. |
| `CLS_MAP` | Maps each classification XML filename (`en_product3_*.xml`) to a short category key (e.g. `genetic_diseases`) — this key names the corresponding output files. |
| `XML_MAP` | Maps each of the 6 non-classification source XML filenames to a pipeline stage name (`alignment`, `gene_disease_associations`, `phenotypes`, `functional_consequences`, `epidemiology`, `natural_history`). |

**Do not rename the XML source files.** If Orphanet changes a filename or you add/remove a
classification category, update the mapping in `CLS_MAP`/`XML_MAP` instead.

---

## Usage

```bash
snakemake --cores 4 --configfile config/config.yaml
```

To test against a local checkout instead of the deployment path baked into `config.yaml`'s `ROOT`
and `script_dir`, override them on the command line, e.g.:

```bash
snakemake --cores 4 \
  --config ROOT="$(pwd)/_local_root" script_dir="$(pwd)/scripts"
```

where `_local_root/<run_name>/sources` is a symlink (or copy) pointing at your local `sources/`
directory.

---

## Pipeline stages

| Rule file | Produces |
|---|---|
| `rules/00_check.smk` | Verifies expected input directories/file counts exist before anything runs. |
| `rules/01_alignment.smk` | `*_alignment_rawdump.csv` from `en_product1.xml`. |
| `rules/02_classification.smk` | One `*_classifications_{cls_key}_rawdump.csv` per `CLS_MAP` entry. |
| `rules/03_gene_disease_association.smk` | `*_gene_disease_associations_rawdump.csv` from `en_product6.xml`. |
| `rules/04_phenotypes.smk` | `*_phenotypes_rawdump.csv` from `en_product4.xml`. |
| `rules/05_functional_consequences.smk` | `*_functional_consequences_rawdump.csv` from `en_funct_consequences.xml`. |
| `rules/06_epidemiology.smk` | `*_epidemiology_rawdump.csv` from `en_product9_prev.xml`. |
| `rules/07_natural_history.smk` | `*_natural_history_rawdump.csv` from `en_product9_ages.xml`. |
| `rules/99_final.smk` | Merges all of the above onto each classification rawdump (leaf disorders only), producing one final CSV per `CLS_MAP` category. |

---

## Output

- **`results/raw_dumps/orphanet_{run_name}_{stage}_rawdump.csv`** — one per source file
  (`alignment`, `gene_disease_associations`, `phenotypes`, `functional_consequences`,
  `epidemiology`, `natural_history`), plus one per classification category.
- **`results/processed/orphanet_{run_name}_{cls_key}_merged.csv`** — one per `CLS_MAP` category:
  leaf disorders in that category, one row per gene-disease association, annotated with
  alignment/phenotype/epidemiology/natural-history/functional-consequence fields. Each disorder's
  classification paths (a disorder can appear under multiple parent categories) are aggregated
  into a single `; `-joined `ClassificationPath` field per disorder — this file is not a cartesian
  product of paths × genes.
- **OMIM split**: the raw `OMIM` column is disambiguated into `OMIM_disorder` (disorder-level,
  from alignment) and `OMIM_gene` (gene-level, from gene-disease associations) in the merged
  output.
- **`HEADERS_TO_KEEP`**: controls which columns (and in what order) appear in the merged output.
  Required for the pipeline to run regardless of this setting: `OrphaCode`, `DisorderId`,
  `GeneSymbol`.

---

## Notebooks

`notebooks/merge.ipynb` is an example of a project-specific downstream analysis built on top of
this pipeline's rawdump/merged output (e.g. joining an external gene list against Orphanet
annotations) — it is not part of the automated pipeline and is not run by Snakemake.
