# Source Data

This pipeline requires Orphanet Scientific Knowledge XML files, which are freely available for
research use from [Orphadata](https://www.orphadata.com/orphanet-scientific-knowledge-files/).

XML files are **not committed to this repository** (see `.gitignore`). Download them manually and
place them in the `sources/` directory as described below.

---

## Required files

### Source XMLs — place in `sources/`

| Filename | Pipeline stage |
|---|---|
| `en_product1.xml` | Alignment (disorder list, nomenclature, external references) |
| `en_product4.xml` | Phenotypes (HPO associations) |
| `en_product6.xml` | Gene–disease associations |
| `en_product9_ages.xml` | Natural history (average age of onset, inheritance) |
| `en_product9_prev.xml` | Epidemiology (prevalence) |
| `en_funct_consequences.xml` | Functional consequences (disability associations) |

### Classification XMLs — place in `sources/classifications/`

All `en_product3_*.xml` files (one per disease category, e.g. `en_product3_156.xml` for genetic
diseases). The full list and their category keys are in `config/config.yaml` under `CLS_MAP`.

---

## Download

Visit the Orphadata download page to find current direct links:

> https://www.orphadata.com/orphanet-scientific-knowledge-files/

Once you have the URLs, download with `curl`:

```bash
# Source XMLs
cd sources/
curl -O https://www.orphadata.com/data/xml/en_product1.xml
curl -O https://www.orphadata.com/data/xml/en_product4.xml
curl -O https://www.orphadata.com/data/xml/en_product6.xml
curl -O https://www.orphadata.com/data/xml/en_product9_ages.xml
curl -O https://www.orphadata.com/data/xml/en_product9_prev.xml
curl -O https://www.orphadata.com/data/xml/en_funct_consequences.xml

# Classification XMLs
mkdir -p classifications/
cd classifications/
# Download all en_product3_*.xml files listed on the Orphadata page
```

> **Note:** Verify the exact URLs from the Orphadata page above — Orphanet periodically updates
> their file distribution structure. Use the English-language files (`en_` prefix) only; see
> the **Language** section in `Readme.md`.

---

## Citation

If you use Orphanet data in your work, please cite:

> Rath A, Olry A, Dhombres F, Brandt MM, Urbero B, Ayme S. Representation of rare diseases in
> health information systems: The Orphanet approach to serve a wide range of end users.
> *Hum Mutat.* 2012;33(5):803–808. doi:[10.1002/humu.22078](https://doi.org/10.1002/humu.22078)
> PMID: 22422702

And acknowledge Orphanet directly:

> Orphanet: an online database of rare diseases and orphan drugs. Copyright, INSERM 1997.
> Available at https://www.orpha.net
