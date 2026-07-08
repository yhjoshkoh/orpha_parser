from pathlib import Path
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_dir", help="Path to the directory containing Orphanet classification XML files.", required=True)
    parser.add_argument("-v", "--version", help="Version string to append to the renamed files. Release date (YYMMDD) recommended for use.", required=True)
    args = parser.parse_args()

    mapping = {
        "en_product3_146.xml"       : "cardiac_diseases",
        "en_product3_147.xml"       : "developmental_anomalies_during_embryogenesis",
        "en_product3_148.xml"       : "cardiac_malformations",
        "en_product3_150.xml"       : "inborn_errors_of_metabolism",
        "en_product3_152.xml"       : "gastroenterological_diseases",
        "en_product3_156.xml"       : "genetic_diseases",
        "en_product3_181.xml"       : "neurological_diseases",
        "en_product3_182.xml"       : "abdominal_surgical_diseases",
        "en_product3_183.xml"       : "hepatic_diseases",
        "en_product3_184.xml"       : "respiratory_diseases",
        "en_product3_185.xml"       : "urogenital_diseases",
        "en_product3_186.xml"       : "surgical_thoracic_diseases",
        "en_product3_187.xml"       : "skin_diseases",
        "en_product3_188.xml"       : "renal_diseases",
        "en_product3_189.xml"       : "ophthalmic_diseases",
        "en_product3_193.xml"       : "endocrine_diseases",
        "en_product3_194.xml"       : "haematological_diseases",
        "en_product3_195.xml"       : "immunological_diseases",
        "en_product3_196.xml"       : "systemic_and_rhumatological_diseases",
        "en_product3_197.xml"       : "odontological_diseases",
        "en_product3_198.xml"       : "circulatory_system_diseases",
        "en_product3_199.xml"       : "bone_diseases",
        "en_product3_200.xml"       : "otorhinolaryngological_diseases",
        "en_product3_201.xml"       : "infertility",
        "en_product3_202.xml"       : "neoplastic_diseases",
        "en_product3_203.xml"       : "infectious_diseases",
        "en_product3_204.xml"       : "diseases_due_to_toxic_effects",
        "en_product3_205.xml"       : "gynaecological_and_obstetric_diseases",
        "en_product3_209.xml"       : "surgical_maxillo-facial_diseases",
        "en_product3_212.xml"       : "allergic_disease",
        "en_product3_216.xml"       : "teratologic_disorders",
        "en_product3_231.xml"       : "systemic_and_rheumatological_diseases_of_childhood",
        "en_product3_233.xml"       : "transplant-related_diseases",
        "en_product3_235.xml"       : "disorder_without_a_determined_diagnosis_after_full_investigation",
        "en_product1.xml"           : "alignment",
        "en_product6.xml"           : "gene_disease_associations",
        "en_product4.xml"           : "phenotypes",
        "en_funct_consequences.xml" : "functional_consequences",
        "en_product9_prev.xml"      : "epidemiology",
        "en_product9_ages.xml"      : "natural_history",
    }

    src_dir = Path(args.input_dir)
    version = args.version

    for f in src_dir.glob("en_product3_*.xml"):
        key = f.name
        if key not in mapping:
            print(f"[SKIP] not in mapping: {key}")
            continue

        dst = f.with_name("orphanet_" + mapping[key] + f"_{version}.xml")  # 확장자 유지
        if dst.exists():
            raise FileExistsError(f"Destination exists: {dst}")

        print(f"[RENAME] {f.name} -> {dst.name}")

        f.rename(dst)

if __name__ == "__main__":
    main()