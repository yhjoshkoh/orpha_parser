
def _tx(el):
    """
    Return the text content of an XML element, stripped of leading/trailing whitespace.
    """
    return (el.text or "").strip() if el is not None else ""

def _tn(tag):
    """
    Strip namespace from XML tag.
    """
    return tag.split("}", 1)[-1] if tag else ""

def _first_child(node, tag_name):
    """
    Return the first child with the given tag name.
    Requires _tn to be defined.
    """
    if node is None:
        return None
    return next((c for c in node if _tn(c.tag) == tag_name), None)

def _child_text(node, tag_name):
    """
    Return the text content of a child element with the given tag name.
    Requires _tx and _first_child to be defined.
    """
    if node is None:
        return ""
    el = _first_child(node, tag_name)
    return _tx(el)

def _id_and_name(node, tag_name):
    """
    Convert <Tag id="..."><Name>...</Name></Tag> to {TagId, TagName}
    Requires _child_text and _first_child to be defined.
    """
    el = _first_child(node, tag_name)
    if el is None:
        return "", ""
    _id = el.get("id", "")
    _name = _child_text(el, "Name")
    return _id, _name

def _list_count(node, tag_name):
    """
    Return the 'count' attribute of the first child with the given tag name.
    Requires _first_child to be defined.
    """
    el = _first_child(node, tag_name)
    if el is None:
        return ""
    return el.get("count", "")