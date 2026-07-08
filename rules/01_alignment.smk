# rules/01_alignment.smk
# import os
# import glob

rule parse_alignment:
    input:
        ok = rules.check_inputs.output.ok,
        xml = f"{in_root}/en_product1.xml"
    output:
        csv = f"{rawdump_dir}/orphanet_{RUNNAME}_alignment_rawdump.csv"
    log:
        f"{log_dir}/orphanet_{RUNNAME}_alignment_rawdump.log"
    shell:
        "python {config[script_dir]}/alignment_parser.py --format raw -i {input.xml} -o {output.csv} > {log} 2>&1"
