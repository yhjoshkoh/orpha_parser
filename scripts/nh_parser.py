import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
from utils.xml_utils import _tn, _tx, _first_child, _child_text, _id_and_name, _list_count


def _parse_disorder_core(disorder_el):
    """
    Disorder core fields (raw dump).
    Mirrors the style used in gene/phenotype/classification/prevalence parsers.
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


def _parse_average_age_of_onset(age_el):
    """
    Parse one <AverageAgeOfOnset id="..."><Name lang="en">...</Name></AverageAgeOfOnset>
    """
    if age_el is None:
        return None
    return {
        "AverageAgeOfOnsetId": age_el.get("id", ""),
        "AverageAgeOfOnset": _child_text(age_el, "Name"),
    }

def _parse_inheritance_list(disorder_el):
    """
    Parse <TypeOfInheritanceList> into aggregated strings.
    """
    if disorder_el is None:
        return {
            "TypeOfInheritanceListCount": "",
            "TypeOfInheritanceIds": "",
            "TypeOfInheritance": "",
            "TypeOfInheritancePairs": "",
        }

    toi_list = _first_child(disorder_el, "TypeOfInheritanceList")
    count = _list_count(disorder_el, "TypeOfInheritanceList")
    ids, names, pairs = [], [], []
    if toi_list is not None:
        for toi in toi_list:
            if _tn(toi.tag) != "TypeOfInheritance":
                continue
            tid = toi.get("id", "")
            tname = _child_text(toi, "Name")
            if tid or tname:
                ids.append(tid)
                names.append(tname)
                pairs.append("|".join([tid, tname]))
    return {
        "TypeOfInheritanceListCount": count,
        "TypeOfInheritanceIds": "; ".join([x for x in ids if x]),
        "TypeOfInheritance": "; ".join([x for x in names if x]),
        "TypeOfInheritancePairs": "; ".join([x for x in pairs if x]),
    }



def extract_ages_long(xml_path: Path) -> pd.DataFrame:
    """
    1 row = 1 AverageAgeOfOnset entry (long format).
    """
    root = ET.parse(xml_path).getroot()

    availability = _tx(_first_child(root, "Availability"))
    licence = _tx(_first_child(root, "Licence"))  # may be absent in some product dumps

    disorder_list = _first_child(root, "DisorderList")
    if disorder_list is None:
        return pd.DataFrame([])

    rows = []
    for disorder in disorder_list:
        if _tn(disorder.tag) != "Disorder":
            continue

        core = _parse_disorder_core(disorder)
        if core is None:
            continue

        inheritance = _parse_inheritance_list(disorder)

        age_list_count = _list_count(disorder, "AverageAgeOfOnsetList")
        age_list = _first_child(disorder, "AverageAgeOfOnsetList")

        if age_list is None:
            rows.append({
                "Availability": availability,
                "Licence": licence,
                **core,
                **inheritance,
                "AverageAgeOfOnsetListCount": age_list_count,
                "AverageAgeOfOnsetId": "",
                "AverageAgeOfOnset": "",
            })
            continue

        any_entry = False
        for age in age_list:
            if _tn(age.tag) != "AverageAgeOfOnset":
                continue
            any_entry = True
            age_info = _parse_average_age_of_onset(age)
            if age_info is None:
                continue

            rows.append({
                "Availability": availability,
                "Licence": licence,
                **core,
                **inheritance,
                "AverageAgeOfOnsetListCount": age_list_count,
                **age_info,
            })

        if not any_entry:
            # List exists but had no parsed entries
            rows.append({
                "Availability": availability,
                "Licence": licence,
                **core,
                **inheritance,
                "AverageAgeOfOnsetListCount": age_list_count,
                "AverageAgeOfOnsetId": "",
                "AverageAgeOfOnset": "",
            })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    front = [
        "Availability", "Licence",
        "OrphaCode", "DisorderId", "DisorderName",
        "DisorderTypeId", "DisorderType",
        "DisorderGroupId", "DisorderGroup",
        "ExpertLink",
        "TypeOfInheritanceListCount",
        "TypeOfInheritanceIds", "TypeOfInheritance", "TypeOfInheritancePairs",
        "AverageAgeOfOnsetListCount",
        "AverageAgeOfOnsetId", "AverageAgeOfOnset",
    ]
    cols = [c for c in front if c in df.columns] + [c for c in df.columns if c not in front]
    return df[cols]


def extract_ages_raw(xml_path: Path) -> pd.DataFrame:
    """
    1 row = 1 disorder (aggregated ages as semicolon-delimited strings).
    """
    df_long = extract_ages_long(xml_path)
    if df_long.empty:
        return df_long

    key_cols = [
        "Availability", "Licence",
        "OrphaCode", "DisorderId", "DisorderName",
        "DisorderTypeId", "DisorderType",
        "DisorderGroupId", "DisorderGroup",
        "ExpertLink",
        "TypeOfInheritanceListCount",
        "TypeOfInheritanceIds", "TypeOfInheritance", "TypeOfInheritancePairs",
        "AverageAgeOfOnsetListCount",
    ]

    rows = []
    grp = df_long.groupby(["OrphaCode"], dropna=False, sort=False)
    for _, sub in grp:
        base = {c: sub.iloc[0].get(c, "") for c in key_cols}

        # preserve order (as in xml) by iterating rows
        ids = []
        names = []
        pairs = []
        for _, r in sub.iterrows():
            aid = str(r.get("AverageAgeOfOnsetId", "") or "")
            an = str(r.get("AverageAgeOfOnset", "") or "")
            if aid or an:
                ids.append(aid)
                names.append(an)
                pairs.append("|".join([aid, an]))

        base["AverageAgeOfOnsetIds"] = "; ".join([x for x in ids if x and x != "nan"])
        base["AverageAgeOfOnset"] = "; ".join([x for x in names if x and x != "nan"])
        base["AverageAgeOfOnsetPairs"] = "; ".join([x for x in pairs if x and x != "nan"])
        rows.append(base)

    out = pd.DataFrame(rows)
    front = key_cols + ["AverageAgeOfOnsetIds", "AverageAgeOfOnset", "AverageAgeOfOnsetPairs"]
    cols = [c for c in front if c in out.columns] + [c for c in out.columns if c not in front]
    return out[cols]


def main():
    parser = argparse.ArgumentParser(
        description="Extract Orphanet Product 9 (Ages / Average age of onset) XML into CSV."
    )
    parser.add_argument("-i", "--input", required=True, help="Input XML file.")
    parser.add_argument("-o", "--output", required=True, help="Output CSV file path.")
    parser.add_argument(
        "--format",
        choices=["long", "raw"],
        default="raw",
        help="long=1 row per age entry, raw=1 row per disorder (aggregated).",
    )

    args = parser.parse_args()
    in_xml = Path(args.input)
    out_csv = Path(args.output)

    if args.format == "long":
        df = extract_ages_long(in_xml)
    else:
        df = extract_ages_raw(in_xml)

    df.to_csv(out_csv, index=False)
    print(f"Saved {len(df)} rows to {out_csv}")


if __name__ == "__main__":
    main()
