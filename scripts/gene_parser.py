import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
from utils.xml_utils import _tn, _tx, _first_child, _child_text, _id_and_name, _list_count

def _parse_external_refs_raw(gene_el):
    """
    Raw dump:
      - ExternalReferenceList count
      - All entries as:
          ExternalRefs = "id:Source:Reference" joined by "; "
    Also keep the "wanted" singletons (for convenience).
    """
    wanted = {
        "Ensembl": "Ensembl",
        "HGNC": "HGNC",
        "OMIM": "OMIM",
        "ClinVar": "ClinVar",
        "SwissProt": "SwissProt",
        "Reactome": "Reactome",
        "Genatlas": "Genatlas",
    }

    # Always include convenience columns so downstream column ordering is stable
    out = {
        "ExternalReferenceListCount": "",
        "ExternalRefs": "",
        **{v: "" for v in wanted.values()},
    }

    if gene_el is None:
        return out

    er_list = _first_child(gene_el, "ExternalReferenceList")
    if er_list is None:
        return out

    out["ExternalReferenceListCount"] = er_list.get("count", "") or ""

    pairs = []
    for er in er_list:
        if _tn(er.tag) != "ExternalReference":
            continue

        er_id = er.get("id", "") or ""
        src = (_child_text(er, "Source") or "").strip()
        ref = (_child_text(er, "Reference") or "").strip()

        if src and ref:
            pairs.append(f"{er_id}:{src}:{ref}")

        key = wanted.get(src)
        if key and ref and not out[key]:
            # keep first hit only (if you want)
            out[key] = ref

    out["ExternalRefs"] = "; ".join(pairs)
    return out


def _parse_synonyms_raw(gene_el):
    syn_list = _first_child(gene_el, "SynonymList")
    if syn_list is None:
        return {"SynonymListCount": "", "Synonyms": ""}
    cnt = syn_list.get("count", "")
    syns = []
    for s in syn_list:
        if _tn(s.tag) != "Synonym":
            continue
        syns.append(_tx(s))
    return {"SynonymListCount": cnt, "Synonyms": "; ".join([x for x in syns if x])}

def _parse_locus_raw(gene_el):
    locus_list = _first_child(gene_el, "LocusList")
    if locus_list is None:
        return {"LocusListCount": "", "GeneLocus": "", "LocusKeys": "", "LocusIds": ""}

    cnt = locus_list.get("count", "")
    loci = []
    keys = []
    ids = []
    for locus in locus_list:
        if _tn(locus.tag) != "Locus":
            continue
        if locus.get("id"):
            ids.append(locus.get("id"))
        gl = _child_text(locus, "GeneLocus")
        lk = _child_text(locus, "LocusKey")
        if gl:
            loci.append(gl)
        if lk:
            keys.append(lk)

    return {
        "LocusListCount": cnt,
        "GeneLocus": "; ".join(loci),
        "LocusKeys": "; ".join(keys),
        "LocusIds": "; ".join(ids),
    }

def extract_pairs_from_genes_raw(genes_xml: Path) -> pd.DataFrame:
    root = ET.parse(genes_xml).getroot()
    rows = []

    for disorder in root.findall(".//Disorder"):
        disorder_id = disorder.get("id", "")
        orphacode = _child_text(disorder, "OrphaCode")
        if not orphacode:
            continue

        disorder_name = _child_text(disorder, "Name")
        expert_link = _child_text(disorder, "ExpertLink")

        dtype_id, dtype_name = _id_and_name(disorder, "DisorderType")
        dgroup_id, dgroup_name = _id_and_name(disorder, "DisorderGroup")

        assoc_list = _first_child(disorder, "DisorderGeneAssociationList")
        assoc_list_count = assoc_list.get("count", "") if assoc_list is not None else ""
        if assoc_list is None:
            # raw dump 목적이면 association 없는 disorder도 남길 수 있는데,
            # 네 step3 merge가 gene 중심이라 여기서는 스킵 유지.
            continue

        for assoc in assoc_list:
            if _tn(assoc.tag) != "DisorderGeneAssociation":
                continue

            source_of_validation = _child_text(assoc, "SourceOfValidation")

            atype_el = _first_child(assoc, "DisorderGeneAssociationType")
            atype_id = atype_el.get("id", "") if atype_el is not None else ""
            atype_name = _child_text(atype_el, "Name") if atype_el is not None else ""

            astatus_el = _first_child(assoc, "DisorderGeneAssociationStatus")
            astatus_id = astatus_el.get("id", "") if astatus_el is not None else ""
            astatus_name = _child_text(astatus_el, "Name") if astatus_el is not None else ""

            gene = _first_child(assoc, "Gene")
            gene_id = gene.get("id", "") if gene is not None else ""

            gene_name = _child_text(gene, "Name")
            gene_symbol = _child_text(gene, "Symbol")

            gtype_el = _first_child(gene, "GeneType") if gene is not None else None
            gtype_id = gtype_el.get("id", "") if gtype_el is not None else ""
            gtype_name = _child_text(gtype_el, "Name") if gtype_el is not None else ""

            row = {
                # Disorder
                "OrphaCode": orphacode,
                "DisorderId": disorder_id,
                "DisorderName": disorder_name,
                "ExpertLink": expert_link,
                "DisorderTypeId": dtype_id,
                "DisorderType": dtype_name,
                "DisorderGroupId": dgroup_id,
                "DisorderGroup": dgroup_name,
                "DisorderGeneAssociationListCount": assoc_list_count,

                # Association
                "SourceOfValidation": source_of_validation,
                "AssociationTypeId": atype_id,
                "AssociationType": atype_name,
                "AssociationStatusId": astatus_id,
                "AssociationStatus": astatus_name,

                # Gene
                "GeneId": gene_id,
                "GeneSymbol": gene_symbol,
                "GeneName": gene_name,
                "GeneTypeId": gtype_id,
                "GeneType": gtype_name,
            }

            # Gene substructures (raw). Each helper already returns the correct
            # default dict when passed None, so no separate fallback branch is needed.
            row.update(_parse_synonyms_raw(gene))
            row.update(_parse_external_refs_raw(gene))
            row.update(_parse_locus_raw(gene))

            rows.append(row)

    df = pd.DataFrame(rows)

    # 컬럼 순서(읽기 좋게) - raw dump라 전체는 그대로 두되 앞부분만 정렬
    if not df.empty:
        front = [
            "OrphaCode","DisorderId","DisorderName","DisorderTypeId","DisorderType","DisorderGroupId","DisorderGroup",
            "ExpertLink","DisorderGeneAssociationListCount",
            "GeneId","GeneSymbol","GeneName","GeneTypeId","GeneType",
            "SynonymListCount","Synonyms",
            "ExternalReferenceListCount","ExternalRefs",
            "Ensembl","HGNC","OMIM","ClinVar","SwissProt","Reactome","Genatlas",
            "LocusListCount","GeneLocus","LocusKeys","LocusIds",
            "SourceOfValidation","AssociationTypeId","AssociationType","AssociationStatusId","AssociationStatus",
        ]
        cols = [c for c in front if c in df.columns] + [c for c in df.columns if c not in front]
        df = df[cols]

    return df


def main():

    parser = argparse.ArgumentParser(
        description = "Extract Orphanet Scientific Knowledge Files - Genes associated with rare diseases (en_product6.xml) into a raw CSV dump."
    )

    parser.add_argument("-i", "--input", required=True, help="Genes associated with rare diseases XML file (en_product6.xml).")
    parser.add_argument("-o", "--output", required=True, help="Output CSV file path.")

    args = parser.parse_args()
    
    genes_xml = Path(args.input)
    out_csv = Path(args.output)
    
    df = extract_pairs_from_genes_raw(genes_xml)

    columns_list = [
        "OrphaCode",
        "DisorderId",
        "ExpertLink",
        "DisorderName",
        "DisorderTypeId",
        "DisorderType",
        "DisorderGroupId",
        "DisorderGroup",
        "DisorderGeneAssociationListCount",
        "SourceOfValidation",
        "GeneId",
        "GeneName",
        "GeneSymbol",
        "SynonymListCount",
        "Synonyms",
        "GeneTypeId",
        "GeneType",
        "ExternalReferenceListCount",
        "ExternalRefs",
        "LocusListCount",
        "LocusIds",
        "LocusKeys",
        "AssociationTypeId",
        "AssociationType",
        "AssociationStatusId",
        "AssociationStatus"
    ]   
    for c in columns_list:
        if c not in df.columns:
            raise ValueError(f"Expected column '{c}' not found in DataFrame.")
        
    df.to_csv(out_csv, index=False)
    print(f"Saved {len(df)} rows to {out_csv}")

if __name__ == "__main__":
    main()
