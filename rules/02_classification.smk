# rules/02_classification.smk

rule parse_classification:
    input:
        ok = rules.check_inputs.output.ok,
        xml = lambda wc: os.path.join(classification_dir, KEY_TO_XML[wc.cls_key]),
    output:
        csv = f"{rawdump_dir}/orphanet_{RUNNAME}_classifications_{{cls_key}}_rawdump.csv"
    log:
        f"{log_dir}/orphanet_{RUNNAME}_classifications_{{cls_key}}_rawdump.log"
    shell:
        "python {config[script_dir]}/classification_parser.py -i {input.xml} -o {output.csv} > {log} 2>&1"
