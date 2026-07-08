# rules/05_functional_consequences.smk

rule parse_functional_consequences:
    input:
        ok = rules.check_inputs.output.ok,
        xml = f"{in_root}/en_funct_consequences.xml"
    output:
        csv = f"{rawdump_dir}/orphanet_{RUNNAME}_functional_consequences_rawdump.csv"
    log:
        f"{log_dir}/orphanet_{RUNNAME}_functional_consequences_rawdump.log"
    shell:
        "python {config[script_dir]}/fc_parser.py -i {input.xml} -o {output.csv} > {log} 2>&1"