import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
from utils.xml_utils import _tn, _tx, _first_child, _child_text, _id_and_name, _list_count


def _parse_disorder_core(disorder_el):
    """
    Disorder core fields (raw dump).
    Mirrors the style used in gene/phenotype/classification parsers.
    """
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


def _parse_named_block(node, tag_name):
    """
    Parse blocks like:
        <PrevalenceType id="..."><Name lang="en">...</Name></PrevalenceType>

    Returns (id, name_en). If tag not present: ("","").
    """
    el = _first_child(node, tag_name)
    if el is None:
        return "", ""
    return el.get("id", ""), _child_text(el, "Name")


def _parse_prevalence(prevalence_el):
    """
    Parse one <Prevalence ...> element.
    """
    if prevalence_el is None:
        return None

    prev_type_id, prev_type = _parse_named_block(prevalence_el, "PrevalenceType")
    prev_qual_id, prev_qual = _parse_named_block(prevalence_el, "PrevalenceQualification")
    prev_class_id, prev_class = _parse_named_block(prevalence_el, "PrevalenceClass")
    prev_geo_id, prev_geo = _parse_named_block(prevalence_el, "PrevalenceGeographic")
    prev_status_id, prev_status = _parse_named_block(prevalence_el, "PrevalenceValidationStatus")

    return {
        "PrevalenceId": prevalence_el.get("id", ""),
        "Source": _child_text(prevalence_el, "Source"),
        "PrevalenceTypeId": prev_type_id,
        "PrevalenceType": prev_type,
        "PrevalenceQualificationId": prev_qual_id,
        "PrevalenceQualification": prev_qual,
        "PrevalenceClassId": prev_class_id,
        "PrevalenceClass": prev_class,
        "ValMoy": _child_text(prevalence_el, "ValMoy"),
        "PrevalenceGeographicId": prev_geo_id,
        "PrevalenceGeographic": prev_geo,
        "PrevalenceValidationStatusId": prev_status_id,
        "PrevalenceValidationStatus": prev_status,
    }


def extract_prevalence_long(xml_path: Path) -> pd.DataFrame:
    """
    1 row = 1 Prevalence entry (long format).
    """
    root = ET.parse(xml_path).getroot()

    availability = _tx(_first_child(root, "Availability"))
    licence = _tx(_first_child(root, "Licence"))  # some products have it, some don't

    disorder_list = _first_child(root, "DisorderList")
    rows = []
    if disorder_list is None:
        return pd.DataFrame(rows)

    for disorder in disorder_list:
        if _tn(disorder.tag) != "Disorder":
            continue

        core = _parse_disorder_core(disorder)
        if core is None:
            continue

        prev_list = _first_child(disorder, "PrevalenceList")
        prev_list_count = prev_list.get("count", "") if prev_list is not None else ""

        if prev_list is None:
            rows.append({
                "Availability": availability,
                "Licence": licence,
                **core,
                "PrevalenceListCount": prev_list_count,
                # empty prevalence columns
                "PrevalenceId": "",
                "Source": "",
                "PrevalenceTypeId": "",
                "PrevalenceType": "",
                "PrevalenceQualificationId": "",
                "PrevalenceQualification": "",
                "PrevalenceClassId": "",
                "PrevalenceClass": "",
                "ValMoy": "",
                "PrevalenceGeographicId": "",
                "PrevalenceGeographic": "",
                "PrevalenceValidationStatusId": "",
                "PrevalenceValidationStatus": "",
            })
            continue

        for prev in prev_list:
            if _tn(prev.tag) != "Prevalence":
                continue
            prev_info = _parse_prevalence(prev)
            if prev_info is None:
                continue

            rows.append({
                "Availability": availability,
                "Licence": licence,
                **core,
                "PrevalenceListCount": prev_list_count,
                **prev_info,
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
            "PrevalenceListCount",
            "PrevalenceId",
            "Source",
            "PrevalenceTypeId", "PrevalenceType",
            "PrevalenceQualificationId", "PrevalenceQualification",
            "PrevalenceClassId", "PrevalenceClass",
            "ValMoy",
            "PrevalenceGeographicId", "PrevalenceGeographic",
            "PrevalenceValidationStatusId", "PrevalenceValidationStatus",
        ]
        cols = [c for c in front if c in df.columns] + [c for c in df.columns if c not in front]
        df = df[cols]

    return df


def extract_prevalence_raw(xml_path: Path) -> pd.DataFrame:
    """
    1 row = 1 disorder (aggregated prevalences as semicolon-delimited strings).
    """
    df_long = extract_prevalence_long(xml_path)
    if df_long.empty:
        return df_long

    key_cols = [
        "Availability", "Licence",
        "OrphaCode", "DisorderId", "DisorderName",
        "DisorderTypeId", "DisorderType",
        "DisorderGroupId", "DisorderGroup",
        "ExpertLink",
        "PrevalenceListCount",
    ]

    def agg_prev(sub):
        chunks = []
        for _, r in sub.iterrows():
            chunks.append("|".join([
                str(r.get("PrevalenceId", "") or ""),
                str(r.get("PrevalenceTypeId", "") or ""),
                str(r.get("PrevalenceType", "") or ""),
                str(r.get("PrevalenceQualificationId", "") or ""),
                str(r.get("PrevalenceQualification", "") or ""),
                str(r.get("PrevalenceClassId", "") or ""),
                str(r.get("PrevalenceClass", "") or ""),
                str(r.get("ValMoy", "") or ""),
                str(r.get("PrevalenceGeographicId", "") or ""),
                str(r.get("PrevalenceGeographic", "") or ""),
                str(r.get("PrevalenceValidationStatusId", "") or ""),
                str(r.get("PrevalenceValidationStatus", "") or ""),
                str(r.get("Source", "") or ""),
            ]))
        return "; ".join(chunks)

    rows = []
    for orphacode, sub in df_long.groupby("OrphaCode", dropna=False, sort=False):
        base = {c: sub.iloc[0].get(c, "") for c in key_cols}
        base["PrevalenceEntries"] = agg_prev(sub)
        base["PrevalenceGeographies"] = "; ".join(
            [x for x in sub["PrevalenceGeographic"].astype(str).tolist() if x and x != "nan"]
        )
        rows.append(base)

    out = pd.DataFrame(rows)
    front = key_cols + ["PrevalenceGeographies", "PrevalenceEntries"]
    cols = [c for c in front if c in out.columns] + [c for c in out.columns if c not in front]
    return out[cols]


def main():
    parser = argparse.ArgumentParser(
        description="Extract Orphanet Product 9 (prevalence) XML into CSV."
    )
    parser.add_argument("-i", "--input", required=True, help="Input XML file.")
    parser.add_argument("-o", "--output", required=True, help="Output CSV file path.")
    parser.add_argument(
        "--format",
        choices=["long", "raw"],
        default="raw",
        help="long=1 row per prevalence entry, raw=1 row per disorder (aggregated).",
    )

    args = parser.parse_args()
    in_xml = Path(args.input)
    out_csv = Path(args.output)

    if args.format == "long":
        df = extract_prevalence_long(in_xml)
    else:
        df = extract_prevalence_raw(in_xml)

    df.to_csv(out_csv, index=False)
    print(f"Saved {len(df)} rows to {out_csv}")


if __name__ == "__main__":
    main()
