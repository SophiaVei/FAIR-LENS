# slr_pipeline.py
import os, time, csv, json, re
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests
import pandas as pd
from scholarly import scholarly
from bs4 import BeautifulSoup
import regex as re2

DATA = Path("data")
RAW = DATA / "raw"
INTERIM = DATA / "interim"
SCREENED = DATA / "screened"
INCLUDED = DATA / "included"
EXTRACTION = DATA / "extraction"
for p in [RAW, INTERIM, SCREENED, INCLUDED, EXTRACTION]: p.mkdir(parents=True, exist_ok=True)

# --- Boolean blocks (exactly as in your spec) ---
BLOCK_A_TERMS = [
    "fairness", "bias", "non-discrimination", "demographic parity",
    "equalized odds", "equal opportunity", "representational harm",
    "toxicity", r"stereotype.*"
]
BLOCK_B_TERMS = [
    r"explainab.*", r"interpretab.*", "attribution", "feature attribution",
    r"counterfactual.*", "example-based", r"prototype.*",
    "concept activation", "TCAV", "model card", "datasheet"
]
BLOCK_C_TERMS = [
    r"large language model.*", "LLM", r"transformer.*", "GPT",
    "instruction tuning", "RLHF", "safety policy", "jailbreak", r"red team.*"
]

# Build a printable query string (for logging / Crossref)
QUERY_PLAIN = "(" + " OR ".join([
    'fairness', 'bias', '"non-discrimination"', '"demographic parity"',
    '"equalized odds"', '"equal opportunity"', '"representational harm"',
    'toxicity', 'stereotype*'
]) + ") AND (" + " OR ".join([
    'explainab*', 'interpretab*', 'attribution', '"feature attribution"',
    'counterfactual*', '"example-based"', 'prototype*', '"concept activation"',
    'TCAV', '"model card"', 'datasheet'
]) + ") AND (" + " OR ".join([
    '"large language model*"', 'LLM', 'transformer*', 'GPT',
    '"instruction tuning"', 'RLHF', '"safety policy"', 'jailbreak',
    '"red team*"'
]) + ")"

YEARS = (2016, 2025)  # inclusive

# --- Regex-based AND-of-blocks filter over title+abstract ---
def _compile_block_regex(terms):
    # convert * -> .* and escape others
    pats = []
    for t in terms:
        if t.endswith(".*") or t.endswith("*"):
            base = t[:-2] if t.endswith(".*") else t[:-1]
            pats.append(r"\b" + re.escape(base) + r".*")
        else:
            # keep spaces as-is to match phrases
            pats.append(r"\b" + t.replace(" ", r"\s+") + r"\b" if not any(ch in t for ch in r".*") else t)
    return [re2.compile(p, re2.I) for p in pats]

RX_A = _compile_block_regex(BLOCK_A_TERMS)
RX_B = _compile_block_regex(BLOCK_B_TERMS)
RX_C = _compile_block_regex(BLOCK_C_TERMS)

def matches_blocks(title:str, abstract:str) -> bool:
    text = " ".join([str(title or ""), str(abstract or "")]).lower()
    def any_match(rx_list): return any(r.search(text) for r in rx_list)
    return any_match(RX_A) and any_match(RX_B) and any_match(RX_C)

def apply_block_filter(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["__ok"] = df.apply(lambda r: matches_blocks(r.get("title"), r.get("abstract")), axis=1)
    out = df[df["__ok"]].drop(columns=["__ok"])
    return out

def _lower_safe(x) -> str:
    # Treat NaN/None as empty string; always return a lowercase string
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    try:
        return str(x).lower()
    except Exception:
        return ""


def smoke_test_openalex():
    url = "https://api.openalex.org/works"
    params = {
        "search": "fairness large language model",
        "per_page": 5,
        "page": 1,
        "mailto": OPENALEX_EMAIL,
    }
    r = requests.get(url, params=params, headers=HEADERS_OA, timeout=60)
    print("Smoke test status:", r.status_code, r.url)
    if r.status_code != 200:
        print("Body:", r.text[:500])
    r.raise_for_status()
    js = r.json()
    first = (js.get("results") or [{}])[0].get("title")
    print("Smoke test first title:", first)

OPENALEX_EMAIL = os.getenv("OPENALEX_EMAIL")
if not OPENALEX_EMAIL:
    raise RuntimeError("Set OPENALEX_EMAIL to your real email (e.g., sofiavei@csd.auth.gr)")

HEADERS_OA = {
    "User-Agent": f"FAIR-LEARN-SLR (mailto:{OPENALEX_EMAIL})",
    "Accept": "application/json"
}

print("Testing OpenAlex header:", HEADERS_OA)

def _save(df: pd.DataFrame, path: Path, label: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Saved {label}: {len(df)} rows → {path}")


def _oa_page(url, params):
    """Fetch a page from OpenAlex with polite retry and backoff."""
    for attempt in range(5):
        r = requests.get(url, params=params, headers=HEADERS_OA, timeout=60)
        if r.status_code == 200:
            return r.json()
        elif r.status_code in (429, 500, 503):
            sleep_time = 2 ** attempt
            print(f"Rate limit or server error ({r.status_code}); sleeping {sleep_time}s...")
            time.sleep(sleep_time)
        elif r.status_code == 403:
            raise RuntimeError(
                "❌ 403 Forbidden: OpenAlex blocked the request.\n"
                "Make sure your OPENALEX_EMAIL is a real, valid academic or work email "
                "and that the User-Agent includes it."
            )
        else:
            r.raise_for_status()
    r.raise_for_status()



# -----------------------------
# 1) Your SLR query blocks
# -----------------------------
# --- Boolean blocks (exactly as in spec) ---
BLOCK_A_TERMS = [
    "fairness", "bias", "non-discrimination", "demographic parity",
    "equalized odds", "equal opportunity", "representational harm",
    "toxicity", r"stereotype.*"
]
BLOCK_B_TERMS = [
    r"explainab.*", r"interpretab.*", "attribution", "feature attribution",
    r"counterfactual.*", "example-based", r"prototype.*",
    "concept activation", "TCAV", "model card", "datasheet"
]
BLOCK_C_TERMS = [
    r"large language model.*", "LLM", r"transformer.*", "GPT",
    "instruction tuning", "RLHF", "safety policy", "jailbreak", r"red team.*"
]

# Build a printable query string (for logging / Crossref)
QUERY_PLAIN = "(" + " OR ".join([
    'fairness', 'bias', '"non-discrimination"', '"demographic parity"',
    '"equalized odds"', '"equal opportunity"', '"representational harm"',
    'toxicity', 'stereotype*'
]) + ") AND (" + " OR ".join([
    'explainab*', 'interpretab*', 'attribution', '"feature attribution"',
    'counterfactual*', '"example-based"', 'prototype*', '"concept activation"',
    'TCAV', '"model card"', 'datasheet'
]) + ") AND (" + " OR ".join([
    '"large language model*"', 'LLM', 'transformer*', 'GPT',
    '"instruction tuning"', 'RLHF', '"safety policy"', 'jailbreak',
    '"red team*"'
]) + ")"

YEARS = (2016, 2025)  # inclusive

# --- Regex-based AND-of-blocks filter over title+abstract ---
import regex as re2  # 'regex' lib handles overlapped and is installed with many dists; fallback to re if needed
def _compile_block_regex(terms):
    # convert * -> .* and escape others
    pats = []
    for t in terms:
        if t.endswith(".*") or t.endswith("*"):
            base = t[:-2] if t.endswith(".*") else t[:-1]
            pats.append(r"\b" + re.escape(base) + r".*")
        else:
            # keep spaces as-is to match phrases
            pats.append(r"\b" + t.replace(" ", r"\s+") + r"\b" if not any(ch in t for ch in r".*") else t)
    return [re2.compile(p, re2.I) for p in pats]

RX_A = _compile_block_regex(BLOCK_A_TERMS)
RX_B = _compile_block_regex(BLOCK_B_TERMS)
RX_C = _compile_block_regex(BLOCK_C_TERMS)

def matches_blocks(title:str, abstract:str) -> bool:
    text = " ".join([str(title or ""), str(abstract or "")]).lower()
    def any_match(rx_list): return any(r.search(text) for r in rx_list)
    return any_match(RX_A) and any_match(RX_B) and any_match(RX_C)

def apply_block_filter(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["__ok"] = df.apply(lambda r: matches_blocks(r.get("title"), r.get("abstract")), axis=1)
    out = df[df["__ok"]].drop(columns=["__ok"])
    return out


# -----------------------------
# 2) Helper: normalize rows
# -----------------------------
CANON_COLS = ["source_db","title","authors","year","venue","abstract","doi","url","doc_type"]

def norm(s):
    return None if pd.isna(s) else str(s).strip()

def normalize(records: List[Dict[str, Any]], source: str) -> pd.DataFrame:
    rows = []
    for r in records:
        rows.append({
            "source_db": source,
            "title": norm(r.get("title")),
            "authors": norm(r.get("authors")),
            "year": r.get("year"),
            "venue": norm(r.get("venue")),
            "abstract": norm(r.get("abstract")),
            "doi": norm(r.get("doi")),
            "url": norm(r.get("url")),
            "doc_type": norm(r.get("doc_type")),
        })
    df = pd.DataFrame(rows)
    for c in CANON_COLS:
        if c not in df.columns: df[c] = None
    return df[CANON_COLS]

# -----------------------------
# 3) Providers
# -----------------------------

def search_openalex(y1: int, y2: int) -> pd.DataFrame:
    base = "https://api.openalex.org/works"
    rows, page = [], 1
    params = {
        "search": QUERY_PLAIN,
        "filter": f"from_publication_date:{y1}-01-01,to_publication_date:{y2}-12-31",
        "per_page": 200, "page": page, "mailto": OPENALEX_EMAIL,
    }
    while True:
        r = requests.get(base, params=params, headers=HEADERS_OA, timeout=60)
        if r.status_code == 403:
            return search_openalex_fallback(y1, y2)
        if r.status_code in (429, 500, 503):
            time.sleep(2); continue
        r.raise_for_status()
        data = r.json() or {}
        results = data.get("results", []) or []
        for w in results:
            rows.append({
                "title": w.get("title"),
                "authors": ", ".join(a["author"]["display_name"] for a in w.get("authorships", [])),
                "year": int(w["publication_year"]) if w.get("publication_year") else None,
                "venue": (w["host_venue"]["display_name"] if w.get("host_venue") else None),
                "abstract": None,
                "doi": (w.get("doi") or "").replace("https://doi.org/","") if w.get("doi") else None,
                "url": w.get("id"),
                "doc_type": w.get("type"),
            })
        meta = data.get("meta", {})
        total = meta.get("count", 0)
        print(f"[OpenAlex] page {page} +{len(results)} collected={len(rows)} / total≈{total}")
        if not results or len(rows) >= total:
            break
        page += 1
        params["page"] = page
        time.sleep(1.0)
    df = normalize(rows, "openalex")
    df = df[(df["year"].fillna(0).astype(int) >= y1) & (df["year"].fillna(0).astype(int) <= y2)]
    df = apply_block_filter(df)
    df["k1"] = df["doi"].str.lower().fillna(""); df["k2"] = df["title"].str.lower().fillna("")
    df = df.sort_values(["k1","year"], na_position="last").drop_duplicates(subset=["k1"], keep="first")
    df = pd.concat([df[df["k1"]!=""], df[df["k1"]==""].drop_duplicates(subset=["k2","year"], keep="first")], ignore_index=True)
    return df.drop(columns=["k1","k2"])

def search_openalex_fallback(y1: int, y2: int) -> pd.DataFrame:
    queries = [
        "fairness large language model", "fairness bias explainability",
        "attribution counterfactual fairness", "model card datasheet fairness",
        "toxicity stereotype language model", "RLHF alignment fairness",
    ]
    base = "https://api.openalex.org/works"
    all_rows = []
    for q in queries:
        page = 1
        while True:
            params = {
                "filter": f"title.search:{q},from_publication_date:{y1}-01-01,to_publication_date:{y2}-12-31",
                "per_page": 200, "page": page, "mailto": OPENALEX_EMAIL,
            }
            r = requests.get(base, params=params, headers=HEADERS_OA, timeout=60)
            if r.status_code in (429, 500, 503): time.sleep(2); continue
            r.raise_for_status()
            results = (r.json() or {}).get("results", []) or []
            if not results:
                break
            for w in results:
                all_rows.append({
                    "title": w.get("title"),
                    "authors": ", ".join(a["author"]["display_name"] for a in w.get("authorships", [])),
                    "year": int(w["publication_year"]) if w.get("publication_year") else None,
                    "venue": (w["host_venue"]["display_name"] if w.get("host_venue") else None),
                    "abstract": None,
                    "doi": (w.get("doi") or "").replace("https://doi.org/","") if w.get("doi") else None,
                    "url": w.get("id"), "doc_type": w.get("type"),
                })
            print(f"[OpenAlex fallback] '{q}' page {page} +{len(results)} (total {len(all_rows)})")
            page += 1; time.sleep(0.8)
    df = normalize(all_rows, "openalex")
    df = df[(df["year"].fillna(0).astype(int) >= y1) & (df["year"].fillna(0).astype(int) <= y2)]
    return apply_block_filter(df)



def search_crossref(query: str, y1: int, y2: int) -> pd.DataFrame:
    url = "https://api.crossref.org/works"
    rows, cursor = [], "*"
    params = {"query": query, "filter": f"from-pub-date:{y1}-01-01,until-pub-date:{y2}-12-31", "rows": 200, "cursor": cursor}
    while True:
        r = requests.get(url, params=params, timeout=60)
        if r.status_code in (429, 500, 503):
            time.sleep(2); continue
        r.raise_for_status()
        j = r.json()["message"]
        items = j.get("items", []) or []
        for i in items:
            rows.append({
                "title": (i["title"][0] if i.get("title") else None),
                "authors": ", ".join([f'{p.get("family","")}, {p.get("given","")}' for p in i.get("author", [])]) if i.get("author") else None,
                "year": (i.get("issued", {}).get("date-parts", [[None]])[0][0]),
                "venue": (i.get("container-title",[None])[0]),
                "abstract": None,
                "doi": i.get("DOI"),
                "url": i.get("URL"),
                "doc_type": i.get("type"),
            })
        print(f"[Crossref] +{len(items)} (total {len(rows)})")
        nxt = j.get("next-cursor")
        if not nxt or not items:
            break
        params["cursor"] = nxt
        time.sleep(0.2)
    df = normalize(rows, "crossref")
    df = df[(df["year"].fillna(0).astype(int) >= y1) & (df["year"].fillna(0).astype(int) <= y2)]
    return apply_block_filter(df)

def search_scholar(query: str, max_n: int = 100) -> pd.DataFrame:
    """
    Use scholarly to query Google Scholar (slow, often blocked).
    If blocked, skip gracefully.
    """
    rows = []
    print(f"Searching Google Scholar for: {query}")
    try:
        search_query = scholarly.search_pubs(query)
        for i, result in enumerate(search_query):
            if i >= max_n:
                break
            pub = scholarly.fill(result)
            rows.append({
                "source_db": "scholar",
                "title": pub.get("bib", {}).get("title"),
                "authors": ", ".join(pub.get("bib", {}).get("author", "").split(" and ")) if "author" in pub.get("bib", {}) else None,
                "year": pub.get("bib", {}).get("pub_year"),
                "venue": pub.get("bib", {}).get("venue"),
                "abstract": pub.get("bib", {}).get("abstract"),
                "doi": pub.get("pub_url", "").replace("https://doi.org/", "") if pub.get("pub_url") else None,
                "url": pub.get("pub_url"),
                "doc_type": None,
            })
            if i % 10 == 0:
                print(f"  {i} papers retrieved...")
    except Exception as e:
        print("⚠️ Google Scholar blocked the request or returned an error:", e)
        print("Skipping Scholar; results will be empty this run.")
        return pd.DataFrame(columns=CANON_COLS)

    df = pd.DataFrame(rows)
    for c in CANON_COLS:
        if c not in df.columns:
            df[c] = None
    return df[CANON_COLS]


def search_acm(query: str, max_n: int = 80) -> pd.DataFrame:
    base = "https://dl.acm.org/action/doSearch"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    short_queries = [
        "fairness large language model",
        "bias large language model",
        "model card language model",
        "toxicity language model",
    ]
    rows = []
    for q in short_queries:
        page = 0
        while len(rows) < max_n:
            params = {"AllField": q, "pageSize": 20, "startPage": page}
            r = requests.get(base, params=params, headers=headers, timeout=30)
            if r.status_code != 200:
                break
            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.select("li.search__item.issue-item-container")
            if not items:
                # may be captcha/bot page; bail for this query
                break
            for it in items:
                title_tag = it.select_one("h5.issue-item__title a")
                title = title_tag.text.strip() if title_tag else None
                url = "https://dl.acm.org" + title_tag["href"] if title_tag else None
                authors = ", ".join(a.text.strip() for a in it.select(".rlist--inline.loi__meta-authors a"))
                venue_tag = it.select_one(".issue-item__detail")
                venue = venue_tag.text.strip() if venue_tag else None
                rows.append({
                    "source_db": "acm",
                    "title": title, "authors": authors, "year": None,
                    "venue": venue, "abstract": None, "doi": None,
                    "url": url, "doc_type": None,
                })
            page += 1
            time.sleep(1.0)
    df = pd.DataFrame(rows)
    for c in CANON_COLS:
        if c not in df.columns: df[c] = None
    return df[CANON_COLS]

def search_ieee(query: str, api_key: Optional[str], max_n: int = 800) -> pd.DataFrame:
    if not api_key:
        print("IEEE API key not found; skipping.")
        return pd.DataFrame(columns=CANON_COLS)

    base = "https://ieeexploreapi.ieee.org/api/v1/search/articles"
    headers = {
        "Accept": "application/json",
        "User-Agent": f"FAIR-LEARN-SLR (mailto:{OPENALEX_EMAIL})"
    }

    # Keep the query short; IEEE dislikes very long boolean strings.
    short_query = '("large language model" OR LLM OR GPT) AND (fairness OR bias)'

    rows = []
    start = 1
    page_size = 200  # IEEE max per request

    while len(rows) < max_n:
        params = {
            "apikey": api_key,
            "querytext": short_query,
            "start_record": start,
            "max_records": page_size,
            "format": "json"
        }
        r = requests.get(base, params=params, headers=headers, timeout=60)

        if r.status_code == 403:
            print("❌ IEEE 403 Forbidden. Common causes:\n"
                  " - Using a QA key on the production endpoint\n"
                  " - Invalid / inactive key\n"
                  " - Request too large (reduce boolean / page size)\n"
                  "Response preview:", r.text[:400])
            return pd.DataFrame(columns=CANON_COLS)

        r.raise_for_status()
        data = r.json() or {}
        arts = data.get("articles", []) or []
        if not arts:
            break

        for item in arts:
            rows.append({
                "source_db": "ieee",
                "title": item.get("title"),
                "authors": ", ".join(a.get("full_name") for a in (item.get("authors", {}) or {}).get("authors", [])) if item.get("authors") else None,
                "year": item.get("publication_year"),
                "venue": item.get("publication_title"),
                "abstract": item.get("abstract"),
                "doi": item.get("doi"),
                "url": item.get("pdf_url") or item.get("html_url"),
                "doc_type": item.get("content_type"),
            })

        start += page_size
        time.sleep(0.6)  # be polite

    return normalize(rows, "ieee")


def search_semanticscholar_multi(y1: int, y2: int) -> pd.DataFrame:
    base = "https://api.semanticscholar.org/graph/v1/paper/search"
    fields = "title,authors,year,venue,abstract,externalIds,url"
    queries = [
        "fairness bias large language model",
        "fairness explainability language model",
        "model card datasheet language model",
        "toxicity stereotype language model",
        "RLHF alignment fairness language model",
    ]
    headers = {"User-Agent": f"FAIR-LEARN-SLR (mailto:{OPENALEX_EMAIL})"}
    rows = []
    for q in queries:
        offset = 0
        while True:
            params = {"query": q, "offset": offset, "limit": 100, "fields": fields}
            # backoff loop
            for attempt in range(6):
                r = requests.get(base, params=params, headers=headers, timeout=60)
                if r.status_code == 200:
                    break
                if r.status_code == 429:
                    wait = 6 * (attempt + 1)
                    print(f"[S2] 429 on '{q}' offset {offset}. Sleeping {wait}s...")
                    time.sleep(wait); continue
                print(f"[S2] HTTP {r.status_code} on '{q}' offset {offset}. Retrying in 2s...")
                time.sleep(2)
            else:
                print(f"[S2] Giving up on '{q}' offset {offset} after repeated failures.")
                break
            data = r.json()
            batch = data.get("data", []) or []
            if not batch:
                break
            for p in batch:
                ext = p.get("externalIds") or {}
                rows.append({
                    "source_db": "semanticscholar",
                    "title": p.get("title"),
                    "authors": ", ".join(a.get("name","") for a in p.get("authors", [])),
                    "year": p.get("year"),
                    "venue": p.get("venue"),
                    "abstract": p.get("abstract"),
                    "doi": ext.get("DOI"),
                    "url": p.get("url"),
                    "doc_type": None,
                })
            offset += 100
            print(f"[S2] '{q}' +{len(batch)} (total {len(rows)}) next offset {offset}")
            time.sleep(1.2)
    df = normalize(rows, "semanticscholar")
    df = df[(df["year"].fillna(0).astype(int) >= y1) & (df["year"].fillna(0).astype(int) <= y2)]
    df["k"] = (df["doi"].str.lower().fillna("") + "||" + df["title"].str.lower().fillna(""))
    df = df.drop_duplicates("k").drop(columns="k")
    return apply_block_filter(df)




# Placeholders for paid APIs (only run if keys exist)
def search_scopus_placeholder(query: str, y1: int, y2: int, api_key: Optional[str]) -> pd.DataFrame:
    if not api_key: return pd.DataFrame(columns=CANON_COLS)
    # Implement via pybliometrics (Elsevier); omitted for brevity.
    return pd.DataFrame(columns=CANON_COLS)

def search_wos_placeholder(query: str, y1: int, y2: int, api_key: Optional[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=CANON_COLS)

#def search_ieee(query: str, y1: int, y2: int, api_key: Optional[str]) -> pd.DataFrame:
#    return pd.DataFrame(columns=CANON_COLS)

# -----------------------------
# 4) Run searches + save raw CSVs
# -----------------------------
def run_searches():
    df_oa = search_openalex(*YEARS);                 df_oa.to_csv(RAW/"openalex.csv", index=False)
    df_cr = search_crossref(QUERY_PLAIN, *YEARS);    df_cr.to_csv(RAW/"crossref.csv", index=False)
    df_ss = search_semanticscholar_multi(*YEARS);    df_ss.to_csv(RAW/"semanticscholar.csv", index=False)

    # ieee_key = os.getenv("IEEE_API_KEY")
    # df_ieee = search_ieee(QUERY_PLAIN, ieee_key)
    # df_ieee.to_csv(RAW/"ieee_manual.csv", index=False)

    _save(df_oa, RAW/"openalex.csv", "OpenAlex")
    _save(df_cr, RAW/"crossref.csv", "Crossref")
    _save(df_ss, RAW/"semanticscholar.csv", "Semantic Scholar")
    print("Saved raw API results to data/raw/*.csv")





# -----------------------------
# 5) Merge + deduplicate
# -----------------------------
def merge_and_dedupe():
    frames = []
    for f in RAW.glob("*.csv"):
        try:
            df = pd.read_csv(f)
            if df.empty:
                continue  # <- skip empties to avoid the FutureWarning
            for c in CANON_COLS:
                if c not in df.columns: df[c] = None
            df = df[CANON_COLS]
            frames.append(df)
        except Exception as e:
            print("Skip", f, e)

    if not frames:
        print("No raw frames to merge.")
        return

    big = pd.concat(frames, ignore_index=True).drop_duplicates()
    # dedupe by DOI, then by (lower(title), year)
    big["doi_norm"] = big["doi"].str.lower().str.strip()
    big["title_norm"] = big["title"].str.lower().str.replace(r"\s+", " ", regex=True).str.strip()
    dedup = big.copy()
    # prefer DOI when present
    dedup = dedup.sort_values(["doi_norm","year"], na_position="last")
    dedup = dedup.drop_duplicates(subset=["doi_norm"], keep="first")
    # then drop title-year dupes for items without DOI
    no_doi = dedup[dedup["doi_norm"].isna()]
    has_doi = dedup[~dedup["doi_norm"].isna()]
    no_doi = no_doi.drop_duplicates(subset=["title_norm","year"], keep="first")
    merged = pd.concat([has_doi, no_doi], ignore_index=True).drop(columns=["doi_norm","title_norm"])
    INTERIM.mkdir(exist_ok=True, parents=True)
    merged.to_csv(INTERIM/"merged.csv", index=False)
    print(f"Merged + deduped: {len(merged)} records → data/interim/merged.csv")

# -----------------------------
# 6) Create screening template
# -----------------------------
# very light heuristics (you can ignore these in manual screening)
def _heur_peer_reviewed(row):
    t = _lower_safe(row.get("doc_type"))
    v = _lower_safe(row.get("venue"))
    return any(k in t for k in ["journal-article","proceedings-article","proceedings","journal"]) \
        or any(k in v for k in ["journal","transactions","proceedings","conference","acm","ieee","springer","elsevier"])

def _heur_llm_context(row):
    txt = f"{_lower_safe(row.get('title'))} {_lower_safe(row.get('abstract'))}"
    return any(k in txt for k in ["llm","large language model","gpt","transformer"])

def _heur_fairness(row):
    txt = f"{_lower_safe(row.get('title'))} {_lower_safe(row.get('abstract'))}"
    return any(k in txt for k in ["fairness","bias","equalized odds","demographic parity","representational harm","toxicity","stereotyp"])

def _heur_xai(row):
    txt = f"{_lower_safe(row.get('title'))} {_lower_safe(row.get('abstract'))}"
    return any(k in txt for k in ["explainab","interpretab","attribution","counterfactual","example-based","prototype",
                                  "tcav","model card","datasheet","concept activation","influence"])

def make_screening_template():
    df = pd.read_csv(INTERIM/"merged.csv")
    templ = df.copy()

    # Manual screening columns (blank)
    templ.insert(0, "include_title", "")
    templ.insert(1, "include_abstract", "")
    templ.insert(2, "reason_code", "")   # for your E-codes

    # Heuristic columns (you can hide these if you want)
    templ["h_peer_reviewed"] = templ.apply(_heur_peer_reviewed, axis=1)
    templ["h_llm_context"]   = templ.apply(_heur_llm_context, axis=1)
    templ["h_fairness"]      = templ.apply(_heur_fairness, axis=1)
    templ["h_xai"]           = templ.apply(_heur_xai, axis=1)
    templ["h_all"]           = templ[["h_peer_reviewed","h_llm_context","h_fairness","h_xai"]].all(axis=1)

    templ.to_csv(SCREENED/"title_abs_screened.csv", index=False)
    print("Screening template → data/screened/title_abs_screened.csv")

def init_prisma_counts():
    # compute counts from what we have now
    # 1) identified_total = raw rows before de-dup (sum of individual CSVs)
    raw_files = [RAW/"openalex.csv", RAW/"crossref.csv", RAW/"semanticscholar.csv"]
    identified_total = sum(len(pd.read_csv(f)) for f in raw_files if f.exists())

    merged = pd.read_csv(INTERIM/"merged.csv")
    after_duplicates_removed = len(merged)

    # auto screen pass (h_all) - just informative; manual screening will overwrite
    screened = pd.read_csv(SCREENED/"title_abs_screened.csv")
    auto_pass = int(screened["h_all"].sum())

    counts = pd.DataFrame({
        "stage": [
            "identified_total",
            "after_duplicates_removed",
            "auto_screen_pass",          # informative
            "excluded_on_title",
            "excluded_on_abstract",
            "full_text_assessed",
            "excluded_full_text",
            "included_final",
        ],
        "n": [
            identified_total,
            after_duplicates_removed,
            auto_pass,
            0, 0, 0, 0, 0,              # to be filled as you screen
        ],
        "notes": [
            "OpenAlex+Crossref+SemanticScholar",
            "", "heuristic prefilter (A∧B∧C & simple heuristics)",
            "set during title screening",
            "set during abstract screening",
            "set during FT eligibility",
            "set during FT eligibility",
            "final"
        ]
    })
    counts.to_csv(DATA/"prisma_counts.csv", index=False)
    print("PRISMA counts → data/prisma_counts.csv")


# -----------------------------
# 7) PRISMA helper (fill as you go)
# -----------------------------
def init_prisma_counts():
    counts = pd.DataFrame({
        "stage": [
            "identified_total",
            "after_duplicates_removed",
            "excluded_on_title",
            "excluded_on_abstract",
            "full_text_assessed",
            "excluded_full_text",
            "included_final",
        ],
        "n": [0,0,0,0,0,0,0]
    })
    counts.to_csv(DATA/"prisma_counts.csv", index=False)
if __name__ == "__main__":
    smoke_test_openalex()   # <— add this line
    run_searches()
    merge_and_dedupe()
    make_screening_template()
    init_prisma_counts()
