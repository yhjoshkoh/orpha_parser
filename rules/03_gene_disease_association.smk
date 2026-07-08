# rules/03_gene_disease_association.smk

rule parse_genes:
    input:
        ok = rules.check_inputs.output.ok,
        xml = f"{in_root}/en_product6.xml"
    output:
        csv = f"{rawdump_dir}/orphanet_{RUNNAME}_gene_disease_associations_rawdump.csv"
    log:
        f"{log_dir}/orphanet_{RUNNAME}_gene_disease_associations_rawdump.log"
    shell:
        "python {config[script_dir]}/gene_parser.py -i {input.xml} -o {output.csv} > {log} 2>&1"
