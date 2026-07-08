# rules/07_natural_history.smk

rule parse_natural_history:
    input:
        ok = rules.check_inputs.output.ok,
        xml = f"{in_root}/en_product9_ages.xml"
    output:
        csv = f"{rawdump_dir}/orphanet_{RUNNAME}_natural_history_rawdump.csv"
    log:
        f"{log_dir}/orphanet_{RUNNAME}_natural_history_rawdump.log"
    shell:
        "python {config[script_dir]}/nh_parser.py -i {input.xml} -o {output.csv} > {log} 2>&1"