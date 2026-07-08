import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
from utils.xml_utils import _tn, _tx, _first_child, _child_text, _id_and_name, _list_count


def _parse_disorder_core(disorder_el):
    """Disorder core fields (raw dump, consistent with other parsers)."""
    if disorder_el is None:
        return None

    orphacode = _child_text(disorder_el, "OrphaCode")
    if not orphacode:
        return None

    dtype_id, dtype_name = _id_and_name(disorder_el, "DisorderType")
    dgroup_id, dgroup_name = _id_and_name(disorder_el, "DisorderGroup")

    return {
        "OrphaCode": orphacode,
        "DisorderId": disorder_el.get("id", ""),
        "DisorderName": _child_text(disorder_el, "Name"),
        "ExpertLink": _child_text(disorder_el, "ExpertLink"),
        "DisorderTypeId": dtype_id,
        "DisorderType": dtype_name,
        "DisorderGroupId": dgroup_id,
        "DisorderGroup": dgroup_name,
    }


def _parse_relevance_status_fields(rel_el):
    """
    DisorderDisabilityRelevance block fields (raw dump).

    This file contains status-ish metadata at the relevance block level.
    Tags observed: SourceOfValidation, SpecificManagement, Online, ValidDate.
    """
    if rel_el is None:
        return {
            "DisorderDisabilityRelevanceId": "",
            "SourceOfValidation": "",
            "SpecificManagement": "",
            "Online": "",
            "ValidDate": "",
        }

    return {
        "DisorderDisabilityRelevanceId": rel_el.get("id", ""),
        "SourceOfValidation": _child_text(rel_el, "SourceOfValidation"),
        "SpecificManagement": _child_text(rel_el, "SpecificManagement"),
        "Online": _child_text(rel_el, "Online"),
        "ValidDate": _child_text(rel_el, "ValidDate"),
    }


def _parse_named_block(node, tag_name):
    """
    Parse blocks like:
        <Disability id="61"><Name lang="en">...</Name></Disability>

    Returns (id, name_en).
    """
    el = _first_child(node, tag_name)
    if el is None:
        return "", ""
    return el.get("id", ""), _child_text(el, "Name")


def _parse_disability_association(assoc_el):
    """
    Parse one DisabilityDisorderAssociation.

    NOTE: In this XML, LossOfAbility / Type / Defined are plain-text elements
    (no <Name> wrapper).
    """
    if assoc_el is None:
        return None

    disability_id, disability_name = _parse_named_block(assoc_el, "Disability")
    freq_id, freq_name = _parse_named_block(assoc_el, "FrequenceDisability")
    temp_id, temp_name = _parse_named_block(assoc_el, "TemporalityDisability")
    sev_id, sev_name = _parse_named_block(assoc_el, "SeverityDisability")

    # Plain-text flags/fields
    loss_of_ability = _child_text(assoc_el, "LossOfAbility")
    assoc_type = _child_text(assoc_el, "Type")
    defined = _child_text(assoc_el, "Defined")

    return {
        "DisabilityDisorderAssociationId": assoc_el.get("id", ""),
        "DisabilityId": disability_id,
        "Disability": disability_name,
        "FrequenceDisabilityId": freq_id,
        "FrequenceDisability": freq_name,
        "TemporalityDisabilityId": temp_id,
        "TemporalityDisability": temp_name,
        "SeverityDisabilityId": sev_id,
        "SeverityDisability": sev_name,
        "LossOfAbility": loss_of_ability,
        "Type": assoc_type,
        "Defined": defined,
    }


def extract_functional_consequences_long(xml_path: Path) -> pd.DataFrame:
    """
    1 row = 1 DisabilityDisorderAssociation (long format).
    """
    root = ET.parse(xml_path).getroot()

    availability = _tx(_first_child(root, "Availability"))
    licence = _tx(_first_child(root, "Licence"))

    rel_list = None
    for n in root.iter():
        if _tn(n.tag) == "DisorderDisabilityRelevanceList":
            rel_list = n
            break

    rows = []
    if rel_list is None:
        return pd.DataFrame(rows)

    for rel in rel_list:
        if _tn(rel.tag) != "DisorderDisabilityRelevance":
            continue

        disorder = _first_child(rel, "Disorder")
        core = _parse_disorder_core(disorder)
        if core is None:
            continue

        status = _parse_relevance_status_fields(rel)

        assoc_list = _first_child(disorder, "DisabilityDisorderAssociationList")
        assoc_list_count = assoc_list.get("count", "") if assoc_list is not None else ""

        if assoc_list is None:
            # keep disorder-level record as a single row with empty assoc fields
            rows.append({
                "Availability": availability,
                "Licence": licence,
                **core,
                **status,
                "DisabilityDisorderAssociationListCount": assoc_list_count,
                # association-level empty columns
                "DisabilityDisorderAssociationId": "",
                "DisabilityId": "",
                "Disability": "",
                "FrequenceDisabilityId": "",
                "FrequenceDisability": "",
                "TemporalityDisabilityId": "",
                "TemporalityDisability": "",
                "SeverityDisabilityId": "",
                "SeverityDisability": "",
                "LossOfAbility": "",
                "Type": "",
                "Defined": "",
            })
            continue

        for assoc in assoc_list:
            if _tn(assoc.tag) != "DisabilityDisorderAssociation":
                continue
            assoc_info = _parse_disability_association(assoc)
            if assoc_info is None:
                continue

            rows.append({
                "Availability": availability,
                "Licence": licence,
                **core,
                **status,
                "DisabilityDisorderAssociationListCount": assoc_list_count,
                **assoc_info,
            })

    df = pd.DataFrame(rows)

    if not df.empty:
        front = [
            "Availability",
            "Licence",
            "OrphaCode", "DisorderId", "DisorderName",
            "DisorderTypeId", "DisorderType",
            "DisorderGroupId", "DisorderGroup",
            "ExpertLink",
            "DisorderDisabilityRelevanceId",
            "SourceOfValidation", "SpecificManagement", "Online", "ValidDate",
            "DisabilityDisorderAssociationListCount",
            "DisabilityDisorderAssociationId",
            "DisabilityId", "Disability",
            "FrequenceDisabilityId", "FrequenceDisability",
            "TemporalityDisabilityId", "TemporalityDisability",
            "SeverityDisabilityId", "SeverityDisability",
            "LossOfAbility", "Type", "Defined",
        ]
        cols = [c for c in front if c in df.columns] + [c for c in df.columns if c not in front]
        df = df[cols]

    return df


def extract_functional_consequences_raw(xml_path: Path) -> pd.DataFrame:
    """
    1 row = 1 disorder (+relevance id) (aggregated associations as semicolon-delimited strings).
    """
    df_long = extract_functional_consequences_long(xml_path)
    if df_long.empty:
        return df_long

    key_cols = [
        "Availability", "Licence",
        "OrphaCode", "DisorderId", "DisorderName",
        "DisorderTypeId", "DisorderType",
        "DisorderGroupId", "DisorderGroup",
        "ExpertLink",
        "DisorderDisabilityRelevanceId",
        "SourceOfValidation", "SpecificManagement", "Online", "ValidDate",
        "DisabilityDisorderAssociationListCount",
    ]

    def agg_block(sub):
        chunks = []
        for _, r in sub.iterrows():
            chunks.append("|".join([
                str(r.get("DisabilityDisorderAssociationId", "") or ""),
                str(r.get("DisabilityId", "") or ""),
                str(r.get("Disability", "") or ""),
                str(r.get("FrequenceDisabilityId", "") or ""),
                str(r.get("FrequenceDisability", "") or ""),
                str(r.get("TemporalityDisabilityId", "") or ""),
                str(r.get("TemporalityDisability", "") or ""),
                str(r.get("SeverityDisabilityId", "") or ""),
                str(r.get("SeverityDisability", "") or ""),
                str(r.get("LossOfAbility", "") or ""),
                str(r.get("Type", "") or ""),
                str(r.get("Defined", "") or ""),
            ]))
        return "; ".join(chunks)

    rows = []
    grp = df_long.groupby(["OrphaCode", "DisorderDisabilityRelevanceId"], dropna=False, sort=False)
    for (_, _), sub in grp:
        base = {c: sub.iloc[0].get(c, "") for c in key_cols}
        base["DisabilityAssociations"] = agg_block(sub)
        base["DisabilityIds"] = "; ".join([x for x in sub["DisabilityId"].astype(str).tolist() if x and x != "nan"])
        base["Disabilities"] = "; ".join([x for x in sub["Disability"].astype(str).tolist() if x and x != "nan"])
        rows.append(base)

    out = pd.DataFrame(rows)
    front = key_cols + ["DisabilityIds", "Disabilities", "DisabilityAssociations"]
    cols = [c for c in front if c in out.columns] + [c for c in out.columns if c not in front]
    return out[cols]


def main():
    parser = argparse.ArgumentParser(
        description="Extract Orphanet - Functional consequences / disability relevance XML into CSV."
    )
    parser.add_argument("-i", "--input", required=True, help="Input XML file.")
    parser.add_argument("-o", "--output", required=True, help="Output CSV file path.")
    parser.add_argument(
        "--format",
        choices=["long", "raw"],
        default="raw",
        help="long=1 row per association, raw=1 row per disorder (aggregated).",
    )

    args = parser.parse_args()
    in_xml = Path(args.input)
    out_csv = Path(args.output)

    if args.format == "long":
        df = extract_functional_consequences_long(in_xml)
    else:
        df = extract_functional_consequences_raw(in_xml)

    df.to_csv(out_csv, index=False)
    print(f"Saved {len(df)} rows to {out_csv}")


if __name__ == "__main__":
    main()
