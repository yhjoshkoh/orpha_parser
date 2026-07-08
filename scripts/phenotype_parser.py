import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd

from utils.xml_utils import (
    _tn, _tx, _first_child, _child_text, _id_and_name, _list_count
)

def _parse_disorder_core(disorder_el):
    """
    Disorder core fields (raw dump).
    """
    if disorder_el is None:
        return None

    orphacode = _child_text(disorder_el, "OrphaCode")
    if not orphacode:
        return None

    disorder_id = disorder_el.get("id", "")
    disorder_name = _child_text(disorder_el, "Name")
    expert_link = _child_text(disorder_el, "ExpertLink")

    dtype_id, dtype_name = _id_and_name(disorder_el, "DisorderType")
    dgroup_id, dgroup_name = _id_and_name(disorder_el, "DisorderGroup")

    return {
        "OrphaCode": orphacode,
        "DisorderId": disorder_id,
        "DisorderName": disorder_name,
        "ExpertLink": expert_link,
        "DisorderTypeId": dtype_id,
        "DisorderType": dtype_name,
        "DisorderGroupId": dgroup_id,
        "DisorderGroup": dgroup_name,
    }

def _parse_status_fields(status_el):
    """
    HPODisorderSetStatus block fields (raw dump).
    """
    if status_el is None:
        return {
            "HPODisorderSetStatusId": "",
            "Source": "",
            "ValidationStatus": "",
            "Online": "",
            "ValidationDate": "",
        }

    return {
        "HPODisorderSetStatusId": status_el.get("id", ""),
        "Source": _child_text(status_el, "Source"),
        "ValidationStatus": _child_text(status_el, "ValidationStatus"),
        "Online": _child_text(status_el, "Online"),
        "ValidationDate": _child_text(status_el, "ValidationDate"),
    }

def _parse_hpo_associations(disorder_el):
    """
    Raw dump for HPODisorderAssociationList inside Disorder.
    Aggregates all HPO associations into semicolon-delimited strings.
    """
    out = {
        "HPODisorderAssociationListCount": "",
        "HPOAssociations": "",
        "HPOIds": "",
        "HPOTerms": "",
        "HPOFrequencyIds": "",
        "HPOFrequencies": "",
        "DiagnosticCriteriaAny": "",  # '1' if any association has non-empty DiagnosticCriteria
    }

    assoc_list = _first_child(disorder_el, "HPODisorderAssociationList")
    if assoc_list is None:
        return out

    out["HPODisorderAssociationListCount"] = assoc_list.get("count", "")

    assoc_chunks = []
    hpo_ids = []
    hpo_terms = []
    freq_ids = []
    freq_names = []
    has_diag = False

    for assoc in assoc_list:
        if _tn(assoc.tag) != "HPODisorderAssociation":
            continue

        # HPO block
        hpo_el = _first_child(assoc, "HPO")
        hpo_id = _child_text(hpo_el, "HPOId") if hpo_el is not None else ""

        # HPOTerm is plain text in product4 (no <Name>)
        hpo_term_el = _first_child(hpo_el, "HPOTerm") if hpo_el is not None else None
        hpo_term = _tx(hpo_term_el)

        # Frequency block (has <Name>)
        freq_el = _first_child(assoc, "HPOFrequency")
        freq_id = freq_el.get("id", "") if freq_el is not None else ""
        freq_name = _child_text(freq_el, "Name") if freq_el is not None else ""

        # DiagnosticCriteria is plain text
        diag_el = _first_child(assoc, "DiagnosticCriteria")
        diag = _tx(diag_el)
        if diag:
            has_diag = True

        # Raw association chunk
        assoc_chunks.append(f"{hpo_id}|{hpo_term}|{freq_id}|{freq_name}|{diag}")

        if hpo_id:
            hpo_ids.append(hpo_id)
        if hpo_term:
            hpo_terms.append(hpo_term)
        if freq_id:
            freq_ids.append(freq_id)
        if freq_name:
            freq_names.append(freq_name)

    out["HPOAssociations"] = "; ".join(assoc_chunks)
    out["HPOIds"] = "; ".join(hpo_ids)
    out["HPOTerms"] = "; ".join(hpo_terms)
    out["HPOFrequencyIds"] = "; ".join(freq_ids)
    out["HPOFrequencies"] = "; ".join(freq_names)
    out["DiagnosticCriteriaAny"] = "1" if has_diag else "0"
    return out

def extract_product4_raw(hpo_xml: Path) -> pd.DataFrame:
    root = ET.parse(hpo_xml).getroot()

    # Optional: availability (root child)
    availability_el = _first_child(root, "Availability")
    availability = _tx(availability_el)

    # HPODisorderSetStatusList holds many HPODisorderSetStatus
    status_list = None
    for n in root.iter():
        if _tn(n.tag) == "HPODisorderSetStatusList":
            status_list = n
            break

    rows = []
    if status_list is None:
        return pd.DataFrame(rows)

    for status in status_list:
        if _tn(status.tag) != "HPODisorderSetStatus":
            continue

        disorder = _first_child(status, "Disorder")
        core = _parse_disorder_core(disorder)
        if core is None:
            continue

        row = {
            "Availability": availability,
            **core,
            **_parse_status_fields(status),
        }

        # HPO association list is inside Disorder (not Status)
        row.update(_parse_hpo_associations(disorder))

        rows.append(row)

    df = pd.DataFrame(rows)

    # Readable column ordering (raw dump keeps the rest)
    if not df.empty:
        front = [
            "Availability",
            "OrphaCode","DisorderId","DisorderName",
            "DisorderTypeId","DisorderType",
            "DisorderGroupId","DisorderGroup",
            "ExpertLink",
            "HPODisorderSetStatusId","Source","ValidationStatus","Online","ValidationDate",
            "HPODisorderAssociationListCount",
            "HPOIds","HPOTerms","HPOFrequencyIds","HPOFrequencies","DiagnosticCriteriaAny",
            "HPOAssociations",
        ]
        cols = [c for c in front if c in df.columns] + [c for c in df.columns if c not in front]
        df = df[cols]

    return df

def extract_product4_long(hpo_xml: Path) -> pd.DataFrame:
    """
    1 row = 1 HPODisorderAssociation (long format)
    """
    root = ET.parse(hpo_xml).getroot()

    availability_el = _first_child(root, "Availability")
    availability = _tx(availability_el)

    status_list = None
    for n in root.iter():
        if _tn(n.tag) == "HPODisorderSetStatusList":
            status_list = n
            break

    rows = []
    if status_list is None:
        return pd.DataFrame(rows)

    for status in status_list:
        if _tn(status.tag) != "HPODisorderSetStatus":
            continue

        disorder = _first_child(status, "Disorder")
        core = _parse_disorder_core(disorder)
        if core is None:
            continue

        base = {
            "Availability": availability,
            **core,
            **_parse_status_fields(status),
        }

        assoc_list = _first_child(disorder, "HPODisorderAssociationList")
        if assoc_list is None:
            # association이 없는 disorder도 남기고 싶으면 아래 rows.append({**base, ...}) 추가하면 됨
            continue

        for assoc in assoc_list:
            if _tn(assoc.tag) != "HPODisorderAssociation":
                continue

            hpo_el = _first_child(assoc, "HPO")
            hpo_id = _child_text(hpo_el, "HPOId") if hpo_el is not None else ""
            hpo_term_el = _first_child(hpo_el, "HPOTerm") if hpo_el is not None else None
            hpo_term = _tx(hpo_term_el)

            freq_el = _first_child(assoc, "HPOFrequency")
            freq_id = freq_el.get("id", "") if freq_el is not None else ""
            freq_name = _child_text(freq_el, "Name") if freq_el is not None else ""

            diag_el = _first_child(assoc, "DiagnosticCriteria")
            diag = _tx(diag_el)

            rows.append({
                **base,
                "HPOId": hpo_id,
                "HPOTerm": hpo_term,
                "HPOFrequencyId": freq_id,
                "HPOFrequency": freq_name,
                "DiagnosticCriteria": diag,
            })

    df = pd.DataFrame(rows)

    if not df.empty:
        front = [
            "Availability",
            "OrphaCode","DisorderId","DisorderName",
            "DisorderTypeId","DisorderType",
            "DisorderGroupId","DisorderGroup",
            "ExpertLink",
            "HPODisorderSetStatusId","Source","ValidationStatus","Online","ValidationDate",
            "HPOId","HPOTerm","HPOFrequencyId","HPOFrequency","DiagnosticCriteria",
        ]
        cols = [c for c in front if c in df.columns] + [c for c in df.columns if c not in front]
        df = df[cols]

    return df

def main():
    parser = argparse.ArgumentParser(
        description="Extract Orphanet Scientific Knowledge Files - HPO associations (en_product4.xml) into raw CSV dumps."
    )
    parser.add_argument("-i", "--input", required=True, help="HPO associations XML file (en_product4.xml).")
    parser.add_argument("-o", "--output", required=True, help="Output CSV file path (collapsed).")
    parser.add_argument(
    "--format",
    choices=["long", "raw"],
    default="raw",
    help="long = 1 row per entry, raw=1 row per disorder (aggregated).",
    )

    args = parser.parse_args()

    in_xml = Path(args.input)
    out_csv = Path(args.output)

    if args.format == "long":
        df = extract_product4_long(in_xml)
        if df.empty:
            raise ValueError("No rows extracted. Check you passed en_product4.xml and that tags match.")
    else:
        df = extract_product4_raw(in_xml)
        if df.empty:
            raise ValueError("No rows extracted. Check you passed en_product4.xml and that tags match.")        

    df.to_csv(out_csv, index=False)
    print(f"Saved {len(df)} rows to {out_csv}")

    
if __name__ == "__main__":
    main()
