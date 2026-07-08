configfile: "config/config.yaml"


import os
import glob
from pathlib import Path

RUNNAME = config["run_name"]
ROOT = os.path.join(config["ROOT"], RUNNAME)

in_root = os.path.join(ROOT, config["inputs"]["in_root"])
classification_dir = os.path.join(in_root, config["inputs"]["classification_dir"])

out_root = os.path.join(ROOT, config["outputs"]["out_root"])
rawdump_dir = os.path.join(out_root, config["outputs"]["rawdump_dir"])
final_dir = os.path.join(out_root, config["outputs"]["final_dir"])

if config.get("log_dir"):
    log_dir = os.path.join(out_root, config["log_dir"])
else:
    log_dir = os.path.join(out_root, "log")


CLS_MAP = config["CLS_MAP"]

# cls_key -> xml filename (invert)
KEY_TO_XML = {v: k for k, v in CLS_MAP.items()}

def _cls_xml():
    return sorted(glob.glob(os.path.join(classification_dir, "*.xml")))

# Exclude classifications not in CLS_MAP
CLS_KEYS = [CLS_MAP[Path(x).name] for x in _cls_xml() if Path(x).name in CLS_MAP]

include: "rules/00_check.smk"
include: "rules/01_alignment.smk"
include: "rules/02_classification.smk"
include: "rules/03_gene_disease_association.smk"
include: "rules/04_phenotypes.smk"
include: "rules/05_functional_consequences.smk"
include: "rules/06_epidemiology.smk"
include: "rules/07_natural_history.smk"
include: "rules/99_final.smk"


rule all:
    input:
        expand(f"{rawdump_dir}/orphanet_{RUNNAME}_classifications_{{cls_key}}_rawdump.csv", cls_key=CLS_KEYS),
        f"{rawdump_dir}/orphanet_{RUNNAME}_alignment_rawdump.csv",
        f"{rawdump_dir}/orphanet_{RUNNAME}_gene_disease_associations_rawdump.csv",
        f"{rawdump_dir}/orphanet_{RUNNAME}_phenotypes_rawdump.csv",
        f"{rawdump_dir}/orphanet_{RUNNAME}_functional_consequences_rawdump.csv",
        f"{rawdump_dir}/orphanet_{RUNNAME}_epidemiology_rawdump.csv",
        f"{rawdump_dir}/orphanet_{RUNNAME}_natural_history_rawdump.csv",
        expand(f"{final_dir}/orphanet_{RUNNAME}_{{cls_key}}_merged.csv", cls_key=CLS_KEYS)
