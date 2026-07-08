# rules/99_final.smk

def _header_args(wc):
    headers = config.get("HEADERS_TO_KEEP")
    if not headers:
        return ""
    if isinstance(headers, str):
        headers = " ".join(headers.split())
    else:
        headers = " ".join(headers)
    return f"--headers {headers}"


rule final_processing:
    input:
        ok = rules.check_rawdumps.output.ok,
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
        expand(f"{final_dir}/orphanet_{RUNNAME}_{{cls_key}}_merged.csv", cls_key=CLS_KEYS)
    log:
        f"{log_dir}/orphanet_{RUNNAME}_final_processing.log"
    params:
        headers = _header_args,
        outdir = final_dir,
        indir = rawdump_dir

    shell:
        "python {config[script_dir]}/final.py -i {params.indir} -o {params.outdir} {params.headers} > {log} 2>&1"
