# rules/06_epidemiology.smk

rule parse_epidemiology:
    input:
        ok = rules.check_inputs.output.ok,
        xml = f"{in_root}/en_product9_prev.xml"
    output:
        csv = f"{rawdump_dir}/orphanet_{RUNNAME}_epidemiology_rawdump.csv"
    log:
        f"{log_dir}/orphanet_{RUNNAME}_epidemiology_rawdump.log"
    shell:
        "python {config[script_dir]}/epi_parser.py -i {input.xml} -o {output.csv} > {log} 2>&1"