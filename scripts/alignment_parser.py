
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
from utils.xml_utils import _tn, _tx, _first_child, _child_text, _id_and_name, _list_count


def _parse_availability_licence(root):
    availability_el = _first_child(root, "Availability")
    availability = _tx(availability_el)

    licence_el = None
    if availability_el is not None:
        licence_el = _first_child(availability_el, "Licence")
    if licence_el is None:
        licence_el = _first_child(root, "Licence")

    if licence_el is None:
        return availability, ""

    licence = (
        _child_text(licence_el, "ShortIdentifier")
        or _child_text(licence_el, "FullName")
        or _child_text(licence_el, "LegalCode")
        or _tx(licence_el)
    )
    return availability, licence


def _parse_disorder_core(disorder_el):
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


def _parse_flags_raw(disorder_el):
    out = {"DisorderFlagListCount": "", "DisorderFlags": ""}
    fl = _first_child(disorder_el, "DisorderFlagList") if disorder_el is not None else None
    if fl is None:
        return out

    out["DisorderFlagListCount"] = fl.get("count", "") or ""
    chunks = []
    for f in fl:
        if _tn(f.tag) != "DisorderFlag":
            continue
        fid = f.get("id", "") or ""
        val = _child_text(f, "Value")
        lbl = _child_text(f, "Label")  # usually plain text, not <Name>
        if fid or lbl or val:
            chunks.append(f"{fid}:{lbl}:{val}")
    out["DisorderFlags"] = "; ".join(chunks)
    return out


def _parse_synonyms_raw(disorder_el):
    syn_list = _first_child(disorder_el, "SynonymList") if disorder_el is not None else None
    if syn_list is None:
        return {"SynonymListCount": "", "Synonyms": ""}

    cnt = syn_list.get("count", "") or ""
    syns = []
    for s in syn_list:
        if _tn(s.tag) != "Synonym":
            continue
        # Synonym is usually direct text content
        syns.append(_tx(s))
    return {"SynonymListCount": cnt, "Synonyms": "; ".join([x for x in syns if x])}


def _parse_external_refs_raw(disorder_el):
    """
    Raw dump:
      - ExternalReferenceList count
      - ExternalRefs = "id:Source:Reference" joined by "; "
      - ExternalRefsDetailed = "id|Source|Reference|RelId|RelName|IcdRelId|IcdRelName|ValId|ValName|IcdUrl|IcdUri"
      - Convenience singletons (first match only)
    """
    wanted = {
        "OMIM": "OMIM",
        "ICD-10": "ICD10",
        "ICD-11": "ICD11",
        "UMLS": "UMLS",
        "MeSH": "MeSH",
        "MedDRA": "MedDRA",
        "SNOMED CT": "SNOMEDCT",
        "ICD-O": "ICDO",
    }

    out = {
        "ExternalReferenceListCount": "",
        "ExternalRefs": "",
        "ExternalRefsDetailed": "",
        **{v: "" for v in wanted.values()},
    }

    er_list = _first_child(disorder_el, "ExternalReferenceList") if disorder_el is not None else None
    if er_list is None:
        return out

    out["ExternalReferenceListCount"] = er_list.get("count", "") or ""
    pairs = []
    detailed = []
    for er in er_list:
        if _tn(er.tag) != "ExternalReference":
            continue
        er_id = er.get("id", "") or ""
        src = (_child_text(er, "Source") or "").strip()
        ref = (_child_text(er, "Reference") or "").strip()
        if src and ref:
            pairs.append(f"{er_id}:{src}:{ref}")

        rel_el = _first_child(er, "DisorderMappingRelation")
        rel_id = rel_el.get("id", "") if rel_el is not None else ""
        rel_name = _child_text(rel_el, "Name") if rel_el is not None else ""

        icdrel_el = _first_child(er, "DisorderMappingICDRelation")
        icdrel_id = icdrel_el.get("id", "") if icdrel_el is not None else ""
        icdrel_name = _child_text(icdrel_el, "Name") if icdrel_el is not None else ""

        val_el = _first_child(er, "DisorderMappingValidationStatus")
        val_id = val_el.get("id", "") if val_el is not None else ""
        val_name = _child_text(val_el, "Name") if val_el is not None else ""

        icd_url = _child_text(er, "DisorderMappingICDRefUrl")
        icd_uri = _child_text(er, "DisorderMappingICDRefUri")

        detailed.append("|".join([
            er_id, src, ref,
            rel_id, rel_name,
            icdrel_id, icdrel_name,
            val_id, val_name,
            icd_url, icd_uri,
        ]))

        key = wanted.get(src)
        if key and ref and not out[key]:
            out[key] = ref

    out["ExternalRefs"] = "; ".join(pairs)
    out["ExternalRefsDetailed"] = "; ".join([d for d in detailed if d.strip("|")])
    return out


def _parse_disorder_disorder_assocs_raw(disorder_el):
    out = {
        "DisorderDisorderAssociationListCount": "",
        "DisorderDisorderAssociations": "",
    }
    al = _first_child(disorder_el, "DisorderDisorderAssociationList") if disorder_el is not None else None
    if al is None:
        return out

    out["DisorderDisorderAssociationListCount"] = al.get("count", "") or ""
    chunks = []

    for assoc in al:
        if _tn(assoc.tag) != "DisorderDisorderAssociation":
            continue

        target = _first_child(assoc, "TargetDisorder")
        rootd = _first_child(assoc, "RootDisorder")
        atype = _first_child(assoc, "DisorderDisorderAssociationType")

        target_id = target.get("id", "") if target is not None else ""
        target_code = _child_text(target, "OrphaCode") if target is not None else ""
        target_name = _child_text(target, "Name") if target is not None else ""

        root_id = rootd.get("id", "") if rootd is not None else ""
        root_cycle = rootd.get("cycle", "") if rootd is not None else ""

        atype_id = atype.get("id", "") if atype is not None else ""
        atype_name = _child_text(atype, "Name") if atype is not None else ""

        # stable, parseable chunk
        chunks.append("|".join([
            target_id, target_code, target_name,
            root_id, root_cycle,
            atype_id, atype_name
        ]))

    out["DisorderDisorderAssociations"] = "; ".join([c for c in chunks if c])
    return out


def _iter_text_sections(disorder_el):
    """
    Yield dicts for each TextSection:
      SummaryInformationId, SummaryLang, TextSectionId, TextSectionTypeId, TextSectionType, Contents
    If no summary info exists, yield a single empty section dict.
    """
    si_list = _first_child(disorder_el, "SummaryInformationList") if disorder_el is not None else None
    if si_list is None:
        yield {
            "SummaryInformationListCount": "",
            "SummaryInformationId": "",
            "SummaryLang": "",
            "TextSectionListCount": "",
            "TextSectionId": "",
            "TextSectionTypeId": "",
            "TextSectionType": "",
            "Contents": "",
        }
        return

    si_cnt = si_list.get("count", "") or ""
    any_yielded = False

    for si in si_list:
        if _tn(si.tag) != "SummaryInformation":
            continue
        # keep only english blocks if present (to avoid mixing languages)
        lang = si.get("lang", "") or ""
        if lang and lang != "en":
            continue

        tsi_id = si.get("id", "") or ""
        tsl = _first_child(si, "TextSectionList")
        tsl_cnt = tsl.get("count", "") if tsl is not None else ""

        if tsl is None:
            any_yielded = True
            yield {
                "SummaryInformationListCount": si_cnt,
                "SummaryInformationId": tsi_id,
                "SummaryLang": lang,
                "TextSectionListCount": tsl_cnt,
                "TextSectionId": "",
                "TextSectionTypeId": "",
                "TextSectionType": "",
                "Contents": "",
            }
            continue

        for ts in tsl:
            if _tn(ts.tag) != "TextSection":
                continue
            any_yielded = True
            tstype = _first_child(ts, "TextSectionType")
            tstype_id = tstype.get("id", "") if tstype is not None else ""
            tstype_name = _child_text(tstype, "Name") if tstype is not None else ""
            contents = _child_text(ts, "Contents")

            yield {
                "SummaryInformationListCount": si_cnt,
                "SummaryInformationId": tsi_id,
                "SummaryLang": lang,
                "TextSectionListCount": tsl_cnt,
                "TextSectionId": ts.get("id", "") or "",
                "TextSectionTypeId": tstype_id,
                "TextSectionType": tstype_name,
                "Contents": contents,
            }

    if not any_yielded:
        # if SummaryInformationList exists but no 'en' entries were yielded
        yield {
            "SummaryInformationListCount": si_cnt,
            "SummaryInformationId": "",
            "SummaryLang": "",
            "TextSectionListCount": "",
            "TextSectionId": "",
            "TextSectionTypeId": "",
            "TextSectionType": "",
            "Contents": "",
        }


def extract_product1_long(xml_path: Path) -> pd.DataFrame:
    """
    Product 1 (Disorder list / nomenclature)
    long format: 1 row = 1 TextSection (summary) for a disorder (disorder duplicated).
    If no summary text exists, keeps one row with empty summary columns.
    """
    root = ET.parse(xml_path).getroot()

    availability, licence = _parse_availability_licence(root)

    disorder_list = _first_child(root, "DisorderList")
    rows = []
    if disorder_list is None:
        return pd.DataFrame(rows)

    disorder_list_count = disorder_list.get("count", "") or ""

    for disorder in disorder_list:
        if _tn(disorder.tag) != "Disorder":
            continue

        core = _parse_disorder_core(disorder)
        if core is None:
            continue

        flags = _parse_flags_raw(disorder)
        syns = _parse_synonyms_raw(disorder)
        ext = _parse_external_refs_raw(disorder)
        dd = _parse_disorder_disorder_assocs_raw(disorder)

        for sec in _iter_text_sections(disorder):
            rows.append({
                "Availability": availability,
                "Licence": licence,
                "DisorderListCount": disorder_list_count,
                **core,
                **flags,
                **syns,
                **ext,
                **dd,
                **sec,
            })

    df = pd.DataFrame(rows)

    if not df.empty:
        front = [
            "Availability","Licence","DisorderListCount",
            "OrphaCode","DisorderId","DisorderName",
            "DisorderTypeId","DisorderType","DisorderGroupId","DisorderGroup",
            "ExpertLink",
            "DisorderFlagListCount","DisorderFlags",
            "SynonymListCount","Synonyms",
            "ExternalReferenceListCount","ExternalRefs","ExternalRefsDetailed",
            "OMIM","ICD10","ICD11","UMLS","MeSH","MedDRA","SNOMEDCT","ICDO",
            "DisorderDisorderAssociationListCount","DisorderDisorderAssociations",
            "SummaryInformationListCount","SummaryInformationId","SummaryLang",
            "TextSectionListCount","TextSectionId","TextSectionTypeId","TextSectionType","Contents",
        ]
        cols = [c for c in front if c in df.columns] + [c for c in df.columns if c not in front]
        df = df[cols]

    return df


def extract_product1_raw(xml_path: Path) -> pd.DataFrame:
    """
    raw format: 1 row = 1 disorder (aggregate summary text sections).
    Other list-like fields already come as joined strings from *_raw helpers.
    """
    df_long = extract_product1_long(xml_path)
    if df_long.empty:
        return df_long

    key_cols = [
        "Availability","Licence","DisorderListCount",
        "OrphaCode","DisorderId","DisorderName",
        "DisorderTypeId","DisorderType","DisorderGroupId","DisorderGroup",
        "ExpertLink",
        "DisorderFlagListCount","DisorderFlags",
        "SynonymListCount","Synonyms",
        "ExternalReferenceListCount","ExternalRefs","ExternalRefsDetailed",
        "OMIM","ICD10","ICD11","UMLS","MeSH","MedDRA","SNOMEDCT","ICDO",
        "DisorderDisorderAssociationListCount","DisorderDisorderAssociations",
    ]

    def agg_sections(sub):
        chunks = []
        for _, r in sub.iterrows():
            t = str(r.get("TextSectionType", "") or "")
            c = str(r.get("Contents", "") or "")
            if c and c != "nan":
                chunks.append(f"{t}:{c}" if t else c)
        return "; ".join(chunks)

    out_rows = []
    for _, sub in df_long.groupby(["OrphaCode"], dropna=False, sort=False):
        base = {c: sub.iloc[0].get(c, "") for c in key_cols}
        base["SummaryTextSections"] = agg_sections(sub)
        base["SummaryTextSectionCount"] = int(sum(bool(str(x or "").strip()) for x in sub.get("Contents", []))) if "Contents" in sub.columns else 0
        out_rows.append(base)

    out = pd.DataFrame(out_rows)

    front = key_cols + ["SummaryTextSectionCount","SummaryTextSections"]
    cols = [c for c in front if c in out.columns] + [c for c in out.columns if c not in front]
    return out[cols]


def main():
    parser = argparse.ArgumentParser(
        description="Extract Orphanet Product 1 (en_product1.xml) disorder list into CSV (long/raw)."
    )
    parser.add_argument("-i","--input", required=True, help="Input XML (en_product1.xml).")
    parser.add_argument("-o","--output", required=True, help="Output CSV path.")
    parser.add_argument("--format", choices=["long","raw"], default="long",
                        help="long=1 row per summary text section, raw=1 row per disorder (aggregated).")

    args = parser.parse_args()
    in_xml = Path(args.input)
    out_csv = Path(args.output)

    if args.format == "long":
        df = extract_product1_long(in_xml)
    else:
        df = extract_product1_raw(in_xml)

    df.to_csv(out_csv, index=False)
    print(f"Saved {len(df)} rows to {out_csv}")


if __name__ == "__main__":
    main()
