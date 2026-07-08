# rules/00_check.smk
import os
import glob

def _glob_xml(dirpath):
    pattern = os.path.join(dirpath, "*.xml")
    return sorted(glob.glob(pattern))



rule check_inputs:
    output:
        ok = temp(f"{rawdump_dir}/.checks/inputs.ok")
    run:
        os.makedirs(os.path.dirname(output.ok), exist_ok=True)
        os.makedirs(rawdump_dir, exist_ok=True)
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(final_dir, exist_ok=True)

        # Check directory existance
        for d in (classification_dir, in_root):
            absd = os.path.abspath(d)
            if not os.path.isdir(absd):
                raise ValueError(f"[check_inputs] Missing directory: {absd}")

        # XML existance check
        cls_xml = _glob_xml(classification_dir)
        src_xml = _glob_xml(in_root)

        if len(cls_xml) != 34:
            print(f"[check_inputs] Expected 34 classification XMLs, found {len(cls_xml)} in {classification_dir}")
        if len(src_xml) != 6:
            print(f"[check_inputs] Expected 6 source XMLs, found {len(src_xml)} in {in_root}")

        with open(output.ok, "w") as f:
            f.write("OK\n")


rule check_rawdumps:
    input:
        alignment = f"{rawdump_dir}/orphanet_{RUNNAME}_alignment_rawdump.csv",
        gene_disease = f"{rawdump_dir}/orphanet_{RUNNAME}_gene_disease_associations_rawdump.csv",
        phenotypes = f"{rawdump_dir}/orphanet_{RUNNAME}_phenotypes_rawdump.csv",
        functional = f"{rawdump_dir}/orphanet_{RUNNAME}_functional_consequences_rawdump.csv",
        epidemiology = f"{rawdump_dir}/orphanet_{RUNNAME}_epidemiology_rawdump.csv",
        natural_history = f"{rawdump_dir}/orphanet_{RUNNAME}_natural_history_rawdump.csv",
        classifications = expand(
            f"{rawdump_dir}/orphanet_{RUNNAME}_classifications_{{cls_key}}_rawdump.csv",
            cls_key=CLS_KEYS,
        )
    output:
        ok = temp(f"{rawdump_dir}/.checks/rawdumps.ok")
    run:
        os.makedirs(os.path.dirname(output.ok), exist_ok=True)
        with open(output.ok, "w") as f:
            f.write("OK\n")