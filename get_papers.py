# slr_pipeline.py
import os, time, csv, json, re
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests
import pandas as pd
from scholarly import scholarly
from bs4 import BeautifulSoup


DATA = Path("data")
RAW = DATA / "raw"
INTERIM = DATA / "interim"
SCREENED = DATA / "screened"
INCLUDED = DATA / "included"
EXTRACTION = DATA / "extraction"
for p in [RAW, INTERIM, SCREENED, INCLUDED, EXTRACTION]: p.mkdir(parents=True, exist_ok=True)


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
BLOCK_A = 'fairness OR bias OR "non-discrimination" OR "demographic parity" OR "equalized odds" OR "equal opportunity" OR "representational harm" OR toxicity OR stereotype*'
BLOCK_B = 'explainab* OR interpretab* OR attribution OR "feature attribution" OR counterfactual* OR "example-based" OR prototype* OR "concept activation" OR TCAV OR "model card" OR datasheet'
BLOCK_C = '"large language model*" OR LLM OR transformer* OR GPT OR "instruction tuning" OR RLHF OR "safety policy" OR jailbreak OR "red team*"'

# OpenAlex supports Lucene-like queries; we’ll keep it broad and AND the blocks.
QUERY_PLAIN = f"({BLOCK_A}) AND ({BLOCK_B}) AND ({BLOCK_C})"
YEARS = (2016, 2025)  # inclusive

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

def search_openalex(y1: int, y2: int, max_n: int = 5000) -> pd.DataFrame:
    """
    Strategy:
      A) Try a quick 'search=' smoke-page to confirm it's accepted.
      B) Then do the full run with 'filter=title.search:' (more WAF-friendly),
         combining several short queries and year filters.
    """
    base = "https://api.openalex.org/works"

    # A) one-page probe with search= (like your browser)
    probe_params = {
        "search": "fairness large language model",
        "per_page": 5,
        "page": 1,
        "mailto": OPENALEX_EMAIL,
    }
    probe = requests.get(base, params=probe_params, headers=HEADERS_OA, timeout=60)
    print("OpenAlex probe:", probe.status_code)
    if probe.status_code != 200:
        print("Probe body:", probe.text[:400])

    # B) main run using title.search filters; overlap is expected
    queries = [
        "fairness large language model",
        "fairness bias explainability",
        "attribution counterfactual fairness",
        "model card datasheet fairness",
        "toxicity stereotype language model",
        "RLHF alignment fairness",
    ]

    all_rows = []
    for q in queries:
        page = 1
        while True:
            params = {
                # use filter=title.search: for reliability with some networks/WAFs
                "filter": f"title.search:{q},from_publication_date:{y1}-01-01,to_publication_date:{y2}-12-31",
                "per_page": 200,
                "page": page,
                "mailto": OPENALEX_EMAIL,
            }
            r = requests.get(base, params=params, headers=HEADERS_OA, timeout=60)
            if r.status_code in (429, 500, 503):
                # polite backoff
                time.sleep(2)
                r = requests.get(base, params=params, headers=HEADERS_OA, timeout=60)
            if r.status_code == 403:
                # last resort: try abstract.search instead of title.search
                params["filter"] = f"abstract.search:{q},from_publication_date:{y1}-01-01,to_publication_date:{y2}-12-31"
                r = requests.get(base, params=params, headers=HEADERS_OA, timeout=60)
            r.raise_for_status()
            data = r.json()

            results = data.get("results", [])
            for w in results:
                all_rows.append({
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
            got = page * 200
            print(f"[OpenAlex] {q!r} page {page} • {len(results)} results • total≈{total}")
            if not results or got >= total or len(all_rows) >= max_n:
                break
            page += 1
            time.sleep(1.0)

        if len(all_rows) >= max_n:
            break

    df = normalize(all_rows, "openalex")
    # enforce year range again
    df = df[(df["year"].fillna(0).astype(int) >= y1) & (df["year"].fillna(0).astype(int) <= y2)]
    # in-provider dedupe
    df["doi_norm"] = df["doi"].str.lower().str.strip()
    df["title_norm"] = df["title"].str.lower().str.replace(r"\s+", " ", regex=True).str.strip()
    df = (df.sort_values(["doi_norm","year"], na_position="last")
            .drop_duplicates(subset=["doi_norm"], keep="first"))
    no_doi = df[df["doi_norm"].isna()].drop_duplicates(subset=["title_norm","year"], keep="first")
    with_doi = df[~df["doi_norm"].isna()]
    df = pd.concat([with_doi, no_doi], ignore_index=True).drop(columns=["doi_norm","title_norm"])
    return df


def search_crossref(query: str, y1: int, y2: int, max_n: int = 2000) -> pd.DataFrame:
    # Docs: https://api.crossref.org/
    url = "https://api.crossref.org/works"
    rows, cursor = [], "*"
    params = {"query": query, "filter": f"from-pub-date:{y1}-01-01,until-pub-date:{y2}-12-31", "rows": 200, "cursor": cursor}
    for _ in range(0, max_n//200 + 1):
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        j = r.json()["message"]
        for i in j.get("items", []):
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
        nxt = j.get("next-cursor")
        if not nxt: break
        params["cursor"] = nxt
        time.sleep(0.2)
    return normalize(rows, "crossref")

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

def search_ieee(query: str, api_key: Optional[str], max_n: int = 1000) -> pd.DataFrame:
    if not api_key:
        print("IEEE API key not found; skipping.")
        return pd.DataFrame(columns=CANON_COLS)
    base = "https://ieeexploreapi.ieee.org/api/v1/search/articles"
    params = {"apikey": api_key, "querytext": query, "max_records": max_n, "format": "json"}
    r = requests.get(base, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    rows = []
    for item in data.get("articles", []):
        rows.append({
            "source_db": "ieee",
            "title": item.get("title"),
            "authors": ", ".join(a.get("full_name") for a in item.get("authors", {}).get("authors", [])) if item.get("authors") else None,
            "year": item.get("publication_year"),
            "venue": item.get("publication_title"),
            "abstract": item.get("abstract"),
            "doi": item.get("doi"),
            "url": item.get("pdf_url"),
            "doc_type": item.get("content_type"),
        })
    return normalize(rows, "ieee")


def search_semanticscholar_multi(y1: int, y2: int, max_n: int = 800) -> pd.DataFrame:
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
    rows, fetched = [], 0
    for q in queries:
        offset = 0
        while offset < 300 and fetched < max_n:  # keep per-query modest
            params = {"query": q, "offset": offset, "limit": 100, "fields": fields}
            # gentle backoff loop
            for attempt in range(5):
                r = requests.get(base, params=params, headers=headers, timeout=60)
                if r.status_code == 200:
                    break
                if r.status_code == 429:
                    wait = 6 * (attempt + 1)
                    print(f"[S2] 429 on '{q}' offset {offset}. Sleeping {wait}s...")
                    time.sleep(wait)
                    continue
                print(f"[S2] HTTP {r.status_code} on '{q}' offset {offset}. Retrying...")
                time.sleep(2)
            else:
                print(f"[S2] Giving up on '{q}' offset {offset} after repeated failures.")
                break
            data = r.json()
            batch = data.get("data", []) or []
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
            fetched += len(batch)
            print(f"[S2] '{q}' +{len(batch)} (total {fetched})")
            if not batch:
                break
            offset += 100
            time.sleep(1.2)  # be nice
        if fetched >= max_n:
            break
    df = normalize(rows, "semanticscholar")
    df = df[(df["year"].fillna(0).astype(int) >= y1) & (df["year"].fillna(0).astype(int) <= y2)]
    # light in-provider dedupe
    df["k"] = (df["doi"].str.lower().fillna("") + "||" + df["title"].str.lower().fillna(""))
    df = df.drop_duplicates("k").drop(columns="k")
    return df



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
    df_oa = search_openalex(*YEARS)
    df_oa.to_csv(RAW/"openalex.csv", index=False)

    df_cr = search_crossref(QUERY_PLAIN, *YEARS); df_cr.to_csv(RAW/"crossref.csv", index=False)
    df_ss = search_semanticscholar_multi(*YEARS);
    df_ss.to_csv(RAW / "semanticscholar.csv", index=False)

    df_sch = search_scholar(QUERY_PLAIN, max_n=50); df_sch.to_csv(RAW/"scholar.csv", index=False)
    df_acm = search_acm(QUERY_PLAIN, max_n=50); df_acm.to_csv(RAW/"acm.csv", index=False)

    # IEEE, Scopus, WoS – optional (requires API keys)
    ieee_key = os.getenv("IEEE_API_KEY")
    scopus_key = os.getenv("SCOPUS_API_KEY")
    wos_key = os.getenv("WOS_API_KEY")

    df_ieee = search_ieee(QUERY_PLAIN, ieee_key); df_ieee.to_csv(RAW/"ieee_manual.csv", index=False)
    df_scopus = search_scopus_placeholder(QUERY_PLAIN, *YEARS, scopus_key); df_scopus.to_csv(RAW/"scopus_manual.csv", index=False)
    df_wos = search_wos_placeholder(QUERY_PLAIN, *YEARS, wos_key); df_wos.to_csv(RAW/"wos_manual.csv", index=False)

    _save(df_oa, RAW / "openalex.csv", "OpenAlex")
    _save(df_cr, RAW / "crossref.csv", "Crossref")
    _save(df_ss, RAW / "semanticscholar.csv", "Semantic Scholar")
    _save(df_sch, RAW / "scholar.csv", "Google Scholar")
    _save(df_acm, RAW / "acm.csv", "ACM DL")
    _save(df_ieee, RAW / "ieee_manual.csv", "IEEE Xplore")
    _save(df_scopus, RAW / "scopus_manual.csv", "Scopus")
    _save(df_wos, RAW / "wos_manual.csv", "Web of Science")

    print("Saved raw API results to data/raw/*.csv")




# -----------------------------
# 5) Merge + deduplicate
# -----------------------------
def merge_and_dedupe():
    frames = []
    for f in RAW.glob("*.csv"):
        try:
            df = pd.read_csv(f)
            # ensure canon cols exist
            for c in CANON_COLS:
                if c not in df.columns: df[c] = None
            df = df[CANON_COLS]
            frames.append(df)
        except Exception as e:
            print("Skip", f, e)
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
def make_screening_template():
    df = pd.read_csv(INTERIM/"merged.csv")
    templ = df.copy()
    templ.insert(0, "include_title", "")
    templ.insert(1, "include_abstract", "")
    templ.insert(2, "reason_code", "")  # E-codes from your protocol
    templ.to_csv(SCREENED/"title_abs_screened.csv", index=False)
    print("Screening template → data/screened/title_abs_screened.csv")

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
