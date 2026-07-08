import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
from utils.xml_utils import _tn, _tx, _first_child


def _parse_disorder(dis_el):
    if dis_el is None:
        return None
    oc_el = next((c for c in dis_el if _tn(c.tag)=="OrphaCode"), None)
    if oc_el is None:
        return None
    name_el  = _first_child(dis_el, "Name")
    dtype_el = next((c for c in dis_el if _tn(c.tag)=="DisorderType"), None)
    dtype_nm = _tx(next((c for c in dtype_el if _tn(c.tag)=="Name"), None)) if dtype_el is not None else ""
    expert   = _first_child(dis_el, "ExpertLink")

    return {
        "OrphaCode": _tx(oc_el),
        "DisorderName": _tx(name_el) if name_el is not None else "",
        "DisorderType": dtype_nm,
        "ExpertLink": _tx(expert) if expert is not None else "",
    }

def extract_all_classification_rows(neuro_xml: Path) -> pd.DataFrame:
    """
    JDBOR → ClassificationList → Classification → ClassificationNodeRootList
    Recursively walk through ClassificationNodeRootList → ClassificationNodeChildList → ClassificationNode.
    Considers each ClassificationNode's Disorder as a 'single step',
    and records the path of names/types from root to current node.
    (If the same OrphaCode appears at multiple levels, it generates multiple rows accordingly.)
    """
    root = ET.parse(neuro_xml).getroot()
    # Find all roots
    roots = []
    for n in root.iter():
        if _tn(n.tag) == "ClassificationNodeRootList":
            roots.extend([c for c in n if _tn(c.tag) == "ClassificationNode"])

    out_rows = []

    def walk(node, path_names, path_types, path_codes):
        
        
        
        dis = next((c for c in node if _tn(c.tag)=="Disorder"), None)
        info = _parse_disorder(dis)
       
        # Pre-check children so we can label this node as leaf/non-leaf.
        child_list = next((c for c in node if _tn(c.tag)=="ClassificationNodeChildList"), None)
        child_nodes = []
        if child_list is not None:
            child_nodes = [c for c in child_list if _tn(c.tag) == "ClassificationNode"]
        is_leaf = 1 if len(child_nodes) == 0 else 0
       
        # Record current node info with path
        if info:
            curr_names = path_names + ([info["DisorderName"]] if info["DisorderName"] else [])
            curr_types = path_types + ([info["DisorderType"]] if info["DisorderType"] else [])
            curr_codes = path_codes + ([info["OrphaCode"]] if info["OrphaCode"] else [])
            out_rows.append({
                **info,
                "IsLeaf": is_leaf,
                "OrphaCodePath": " > ".join(curr_codes),
                "ClassificationPath": " > ".join(curr_names),
                "ClassificationTypes": " > ".join([t for t in curr_types if t]),
                "ClassificationDepth": len(curr_names),
            })
            path_names, path_types, path_codes = curr_names, curr_types, curr_codes
        # 자식 단계 순회
        if child_list is not None:
            for ch in child_list:
                if _tn(ch.tag) == "ClassificationNode":
                    walk(ch, path_names, path_types, path_codes)

    for r in roots:
        walk(r, [], [], [])

    df = pd.DataFrame(out_rows)
    return df


def main():
    parser = argparse.ArgumentParser(
        description = "Extract Orphanet Scientific Knowledge Files - Classifications of Rare Diseases (en_product3_class.xml) into a raw CSV dump."
    )

    parser.add_argument("-i", "--input", required=True, help="Orphanet classifications of rare diseases XML file (en_product3.xml).")
    parser.add_argument("-o", "--output", required=True, help="Output CSV file path.")

    args = parser.parse_args()

    neuro_xml = Path(args.input)
    out_csv = Path(args.output)
    df = extract_all_classification_rows(neuro_xml)

    columns_list = [
        "IsLeaf",
        "OrphaCode",
        "DisorderName",
        "DisorderType",
        "ExpertLink",
        "OrphaCodePath",
        "ClassificationPath",
        "ClassificationTypes",
        "ClassificationDepth"
    ]

    for c in columns_list:
        if c not in df.columns:
            raise ValueError(f"Expected column '{c}' not found in DataFrame.")
        
    df.to_csv(out_csv, index=False)
    print(f"Saved {len(df)} rows to {out_csv}")



if __name__ == "__main__":
    main()