# rules/04_phenotypes.smk
# import os
# import glob

rule parse_phenotypes:
    input:
        ok = rules.check_inputs.output.ok,
        input = f"{in_root}/en_product4.xml"
    output:
        output = f"{rawdump_dir}/orphanet_{RUNNAME}_phenotypes_rawdump.csv"
    log:
        f"{log_dir}/orphanet_{RUNNAME}_phenotypes_rawdump.log"
    shell:
        "python {config[script_dir]}/phenotype_parser.py -i {input.input} -o {output.output} > {log} 2>&1"