# slr_lens.py
import os, time, json, re, csv
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import requests

# -------------------------
# Paths
# -------------------------
DATA       = Path("data")
LENS_DIR   = DATA / "lens"
RAW        = Path("data/raw")                # your existing raw dir
EXPORTS    = LENS_DIR / "exports"            # optional: CSVs exported via UI
LOGS_DIR   = LENS_DIR / "logs"
for p in [LENS_DIR, EXPORTS, LOGS_DIR, RAW]: p.mkdir(parents=True, exist_ok=True)


# -------------------------
# Query blocks (broad + generic)
# -------------------------
BLOCK_A_TERMS = [
    r"fairness", r"fair\b", r"bias", r"discriminat.*", r"ethic.*", r"harm.*", r"risk.*"
]

BLOCK_B_TERMS = [
    r"\bxai\b", r"explainab.*", r"\battribution\b", r"feature attribution", r"\btcav\b"
]

BLOCK_C_TERMS = [
    r"large language model.*", r"\bLLM\b", r"\bGPT\b", r"\bGPT-3\b", r"\bGPT-4\b",
    r"\bChatGPT\b", r"LLaMA.*", r"transformer.*", r"instruction tun.*",
    r"in-context learning", r"prompt.*", r"\bCopilot\b", r"\bClaude\b",
    r"\bGemini\b", r"\bMistral\b", r"command R"
]

# Boolean string fed to Lens (title/abstract/full_text)
QUERY_PLAIN = "(" + " OR ".join([
    "fairness", "fair", "bias", "discriminat*", "ethic*", "harm*", "risk*"
]) + ") AND (" + " OR ".join([
    "xai", "explainab*", "attribution", "\"feature attribution\"", "tcav"
]) + ") AND (" + " OR ".join([
    "\"large language model*\"", "LLM", "GPT", "\"GPT-3\"", "\"GPT-4\"", "ChatGPT",
    "LLaMA*", "transformer*", "\"instruction tun*\"", "\"in-context learning\"",
    "prompt*", "Copilot", "Claude", "Gemini", "Mistral", "\"command R\""
]) + ")"


YEARS = (2016, 2025)  # inclusive

# -------------------------
# Helpers
# -------------------------
def _s(x: Any) -> str:
    """safe lowercase string; NaN/None -> ''"""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x or "").lower()

CANON_COLS = ["source_db","title","authors","year","venue","abstract","doi","url","doc_type","language"]

def normalize(records: List[Dict[str, Any]], source: str) -> pd.DataFrame:
    rows = []
    for r in records:
        rows.append({
            "source_db": source,
            "title": r.get("title"),
            "authors": r.get("authors"),
            "year": r.get("year"),
            "venue": r.get("venue"),
            "abstract": r.get("abstract"),
            "doi": r.get("doi"),
            "url": r.get("url"),
            "doc_type": r.get("doc_type"),
            "language": r.get("language")
        })
    df = pd.DataFrame(rows)
    for c in CANON_COLS:
        if c not in df.columns: df[c] = None
    return df[CANON_COLS]

# --- regex blocks compiled once
import regex as re2
def _compile_block_regex(terms):
    pats = []
    for t in terms:
        if t.endswith(".*") or t.endswith("*"):
            base = t[:-2] if t.endswith(".*") else t[:-1]
            pats.append(r"\b" + re.escape(base) + r".*")
        else:
            pats.append(r"\b" + t.replace(" ", r"\s+") + r"\b" if not any(ch in t for ch in r".*") else t)
    return [re2.compile(p, re2.I) for p in pats]

RX_A = _compile_block_regex(BLOCK_A_TERMS)
RX_B = _compile_block_regex(BLOCK_B_TERMS)
RX_C = _compile_block_regex(BLOCK_C_TERMS)

def matches_blocks(title: str, abstract: str) -> bool:
    text = (_s(title) + " " + _s(abstract))
    def any_match(rx_list): return any(r.search(text) for r in rx_list)
    return any_match(RX_A) and any_match(RX_B) and any_match(RX_C)

def apply_block_filter(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["__ok"] = df.apply(lambda r: matches_blocks(r.get("title"), r.get("abstract")), axis=1)
    return df[df["__ok"]].drop(columns=["__ok"], errors="ignore")

# ---------- Module-level helpers for PRISMA + screening ----------

def is_english_row(row) -> bool:
    langs = row.get("_languages_list")
    if isinstance(langs, list) and len(langs) > 0:
        return any(_s(x) == "en" for x in langs)
    lang = _s(row.get("language"))
    if not lang:    # default-to-English if missing
        return True
    return any(_s(p.strip()) == "en" for p in lang.split(","))

def is_arxiv_like(row) -> bool:
    v = _s(row.get("venue"))
    d = _s(row.get("doi"))
    u = _s(row.get("url"))
    return ("arxiv" in v) or d.startswith("10.48550") or ("arxiv.org" in u)

def is_non_peer_row(row) -> bool:
    # Your rule: non-peer if arXiv-like OR missing/empty venue
    return is_arxiv_like(row) or (len(_s(row.get("venue"))) == 0)

def dedupe_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["doi_norm"]   = df["doi"].str.lower().str.strip()
    df["title_norm"] = df["title"].str.lower().str.replace(r"\s+", " ", regex=True).str.strip()
    df = (df.sort_values(["doi_norm","year"], na_position="last")
            .drop_duplicates(subset=["doi_norm"], keep="first"))
    no_doi  = df[df["doi_norm"].isna()].drop_duplicates(subset=["title_norm","year"], keep="first")
    with_doi = df[~df["doi_norm"].isna()]
    out = pd.concat([with_doi, no_doi], ignore_index=True).drop(columns=["doi_norm","title_norm"])
    return out

# A∧B∧C matches – title-only vs abstract-only
def _any(rx_list, text):
    return any(r.search(text or "") for r in rx_list)

def match_title_A_and_B_and_C(row) -> bool:
    t = _s(row.get("title"))
    return _any(RX_A, t) and _any(RX_B, t) and _any(RX_C, t)

def match_abstract_A_and_B_and_C(row) -> bool:
    a = _s(row.get("abstract"))
    return _any(RX_A, a) and _any(RX_B, a) and _any(RX_C, a)


def lens_smoke():
    """Quick sanity check that your token & basic fields work."""
    url = "https://api.lens.org/scholarly/search"
    headers = {
        "Authorization": f"Bearer {LENS_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "FAIR-LEARN-SLR"
    }
    body = {
        "query": {
            "query_string": {
                "query": "gpt OR \"large language model\"",
                "default_operator": "and",
                "fields": ["title","abstract"]
            }
        },
        "include": ["lens_id","title","year_published","publication_type","languages","source","external_ids","source_urls"],
        "size": 5
    }
    r = requests.post(url, headers=headers, json=body, timeout=60)
    print("[SMOKE] status:", r.status_code)
    print("[SMOKE] body preview:", r.text[:500])


# -------------------------
# Inclusion / Exclusion heuristics (I1–I5 / E1–E5)
# These are heuristic tags to help you screen + to log counts.
# -------------------------
def tag_inclusions_exclusions(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    NON_PEER_TYPES = {
        "preprint", "working paper", "working-paper", "workshop paper",
        "technical report", "report", "white paper", "white-paper"
    }

    def I1(row):
        t = _s(row.get("doc_type"))
        v = _s(row.get("venue"))
        if t in NON_PEER_TYPES:
            return False
        if any(k in t for k in ["journal-article","proceedings-article","conference-article","article"]):
            return True
        if any(k in v for k in [
            "journal","transactions","proceedings","conference",
            "acm","ieee","springer","elsevier","aaai","neurips","icml","acl","emnlp","coling","naacl"
        ]):
            return True
        return False

    # Reuse module-level English/arXiv detectors
    df["I1_peer_reviewed"] = df.apply(I1, axis=1)
    df["I2_english"]       = df.apply(is_english_row, axis=1)

    def I3(row):
        txt = (_s(row.get("title")) + " " + _s(row.get("abstract")))
        return any(k in txt for k in ["llm","large language model","gpt","transformer"])

    def I4(row):
        txt = (_s(row.get("title")) + " " + _s(row.get("abstract")))
        return any(k in txt for k in [
            "fairness","bias","equalized odds","demographic parity","representational harm",
            "toxicity","stereotyp","non-discrimination"
        ])

    def I5(row):
        txt = (_s(row.get("title")) + " " + _s(row.get("abstract")))
        return any(k in txt for k in [
            "explainab","interpretab","attribution","counterfactual","example-based",
            "prototype","tcav","model card","datasheet","concept activation","influence","probe","probing"
        ])

    df["I3_llm"]      = df.apply(I3, axis=1)
    df["I4_fairness"] = df.apply(I4, axis=1)
    df["I5_xai"]      = df.apply(I5, axis=1)

    df["arxiv_like"] = df.apply(is_arxiv_like, axis=1)

    # Exclusions (any)
    def E1(row):  # non-archival only
        return (row["arxiv_like"] and not row["I1_peer_reviewed"])

    def E2(row):  # pure safety/jailbreak without fairness constructs
        txt = (_s(row.get("title")) + " " + _s(row.get("abstract")))
        safetyish = any(k in txt for k in ["safety policy","jailbreak","red team"])
        return safetyish and not row["I4_fairness"]

    def E3(row):  # pure interpretability/mechanistic without fairness goal
        txt = (_s(row.get("title")) + " " + _s(row.get("abstract")))
        interp = any(k in txt for k in ["mechanistic interpretability","mechanistic","circuit","feature visualization"])
        return interp and not row["I4_fairness"]

    def E4(row):  # wrong modality (no obvious LLM context)
        return not row["I3_llm"]

    def E5(row):  # opinion/tutorial/dataset-only without fairness/XAI eval
        txt = (_s(row.get("title")) + " " + _s(row.get("abstract")))
        looks_like = any(k in txt for k in ["survey","opinion","position","tutorial"]) and not (row["I4_fairness"] and row["I5_xai"])
        dataset_only = ("dataset" in txt and "evaluate" not in txt and "metric" not in txt and "bias" not in txt and "fairness" not in txt)
        return looks_like or dataset_only

    df["E1_non_archival_only"]   = df.apply(E1, axis=1)
    df["E2_pure_safety"]         = df.apply(E2, axis=1)
    df["E3_pure_interpret_only"] = df.apply(E3, axis=1)
    df["E4_non_llm_modality"]    = df.apply(E4, axis=1)
    df["E5_no_eval"]             = df.apply(E5, axis=1)

    df["I_all"] = df[["I1_peer_reviewed","I2_english","I3_llm","I4_fairness","I5_xai"]].all(axis=1)
    df["E_any"] = df[["E1_non_archival_only","E2_pure_safety","E3_pure_interpret_only","E4_non_llm_modality","E5_no_eval"]].any(axis=1)

    return df

# -------------------------
# Lens API fetch (uses token if present)
# -------------------------
LENS_API_TOKEN = os.getenv("LENS_API_TOKEN")  # set this if you want API mode



# === REPLACE _lens_query_body WITH THIS ===
def _lens_query_body(y1: int, y2: int) -> Dict[str, Any]:
    # Keep the big boolean, but only enforce the year at API level.
    must = [
        {
            "query_string": {
                "query": QUERY_PLAIN,
                "default_operator": "and",
                "fields": ["title","abstract","full_text"]
            }
        },
        {"range": {"year_published": {"gte": y1, "lte": y2}}}
    ]

    # Keep arXiv/preprint exclusions to avoid a flood of arXiv-only
    must_not = [
        {"terms": {"publication_type": [
            "preprint","working paper","report","news","editorial",
            "libguide","reference entry","dataset","book","book chapter",
            "journal","journal issue","journal volume","other","unknown","standard","dissertation",
            "clinical trial","clinical study","letter","review"
        ]}},
        {"query_string": {"query": "source.title:(arXiv) OR source_urls.url:(arxiv.org)"}}
    ]

    return {
        "query": {"bool": {"must": must, "must_not": must_not}},
        "include": [
            "lens_id","title","abstract","year_published","publication_type",
            "languages","source","authors","external_ids","source_urls"
        ],
        "size": 1000,
        "scroll": "2m"
    }


# === REPLACE _map_lens_record WITH THIS ===
def _map_lens_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    # authors -> join names
    authors = None
    if rec.get("authors"):
        names = []
        for a in rec["authors"]:
            nm = a.get("collective_name") or " ".join(
                [x for x in [a.get("first_name"), a.get("last_name")] if x]
            )
            if nm:
                names.append(nm)
        authors = ", ".join(names) if names else None

    # doi
    doi = None
    for eid in rec.get("external_ids", []) or []:
        if eid.get("type") == "doi":
            doi = eid.get("value")
            break

    # venue + url
    venue = None
    src = rec.get("source") or {}
    if isinstance(src, dict):
        venue = src.get("title")

    url = None
    for su in rec.get("source_urls") or []:
        if su.get("url"):
            url = su["url"]
            break

    # language(s)
    langs = rec.get("languages") or []
    language = ",".join(langs) if langs else None

    # arXiv-like
    is_arxiv = False
    if venue and re.search(r"\barxiv\b", venue, re.I): is_arxiv = True
    if any(("arxiv.org" in (su.get("url","").lower())) for su in (rec.get("source_urls") or [])): is_arxiv = True
    if doi and str(doi).lower().startswith("10.48550"): is_arxiv = True

    return {
        "title": rec.get("title"),
        "authors": authors,
        "year": rec.get("year_published"),
        "venue": venue,
        "abstract": rec.get("abstract"),
        "doi": doi,
        "url": url,
        "doc_type": rec.get("publication_type"),
        "language": language,
        "_languages_list": langs,
        "is_arxiv_like": is_arxiv
    }

# -------------------------
# CSV fallback (UI exports)
# -------------------------
def import_lens_exports() -> pd.DataFrame:
    files = sorted(EXPORTS.glob("*.csv"))
    if not files:
        print("No Lens CSVs found in data/lens/exports; returning empty frame.")
        return pd.DataFrame(columns=CANON_COLS)

    frames = []
    for f in files:
        df = pd.read_csv(f, dtype=str, keep_default_na=False)
        mapped = pd.DataFrame({
            "source_db": "lens",
            "title": df.get("Title") or df.get("title"),
            "authors": df.get("Authors") or df.get("authors"),
            "year": pd.to_numeric(df.get("Publication Year") or df.get("publication_year") or df.get("Year"), errors="coerce"),
            "venue": df.get("Source Title") or df.get("source.title") or df.get("Venue"),
            "abstract": df.get("Abstract") or df.get("abstract"),
            "doi": df.get("DOI") or df.get("doi"),
            "url": df.get("Link") or df.get("link") or df.get("URL"),
            "doc_type": df.get("Document Type") or df.get("doc_type"),
            "language": (df.get("Language") or df.get("language")),
        })
        for c in CANON_COLS:
            if c not in mapped.columns: mapped[c] = None
        frames.append(mapped[CANON_COLS])

    out = pd.concat(frames, ignore_index=True)
    # DO NOT block-filter or dedupe here; just return mapped rows.
    return out

# -------------------------
# Public entry: get Lens data + logs
# -------------------------

def _save_stage(df: pd.DataFrame, path: Path, name: str) -> int:
    out = path / f"{name}.csv"
    df.to_csv(out, index=False)
    print(f"[STAGE] {name}: saved {len(df)} rows -> {out}")
    return int(len(df))


def run_lens(y1: int = YEARS[0], y2: int = YEARS[1]) -> pd.DataFrame:
    """
    Stages we save for PRISMA:
      S0_raw_api            = all results returned by Lens API (pre-year enforcement rechecked)
      S1_year               = after year window (belt & suspenders)
      S2_blockfilter        = after A∧B∧C (title+abstract) screen (proxy for title/abstract screening)
      S4_tagged             = after inclusion/exclusion tagging (for descriptive reporting)
    """
    (LENS_DIR / "stages").mkdir(parents=True, exist_ok=True)

    if LENS_API_TOKEN:
        lens_smoke()
        print("Using Lens API…")


        # 1) Fetch again but WITHOUT local filters/dedupe to expose S0/S1
        #    (Reuse search but copy its fetch body.)
        url = "https://api.lens.org/scholarly/search"
        headers = {
            "Authorization": f"Bearer {LENS_API_TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "FAIR-LEARN-SLR"
        }
        body = _lens_query_body(y1, y2)
        rows_raw, fetched = [], 0

        r = requests.post(url, headers=headers, json=body, timeout=120)
        if r.status_code not in (200, 204):
            raise RuntimeError(f"[Lens] HTTP {r.status_code}: {r.text[:400]}")
        js = r.json() if r.status_code == 200 else {}
        scroll_id = js.get("scroll_id")
        data = js.get("data", []) or []
        rows_raw.extend(data)
        fetched += len(data)
        while scroll_id:
            r = requests.post(url, headers=headers, json={"scroll_id": scroll_id, "scroll": "2m"}, timeout=120)
            if r.status_code == 204:
                break
            if r.status_code != 200:
                raise RuntimeError(f"[Lens] Scroll HTTP {r.status_code}: {r.text[:400]}")
            js = r.json()
            scroll_id = js.get("scroll_id")
            data = js.get("data", []) or []
            if not data:
                break
            rows_raw.extend(data)
            fetched += len(data)
            time.sleep(0.2)

        # Map only, no filters:
        df_s0 = normalize([_map_lens_record(r) for r in rows_raw], "lens")
        S0 = _save_stage(df_s0, LENS_DIR / "stages", "S0_raw_api")

        # S1: year filter (belt & suspenders)
        df_s1 = df_s0[(df_s0["year"].fillna(0).astype(int) >= y1) & (df_s0["year"].fillna(0).astype(int) <= y2)]
        S1 = _save_stage(df_s1, LENS_DIR / "stages", "S1_year")

        # ===== PRISMA block you asked for (placed after S1) =====
        # 0) Total identified (2016–2025)
        total_identified = len(df_s1)

        # 1) Duplicates
        df_after_dedup = dedupe_df(df_s1)
        n_duplicates = total_identified - len(df_after_dedup)

        # 2) Non-English (per your rule)
        mask_en = df_after_dedup.apply(is_english_row, axis=1)
        n_non_english = int((~mask_en).sum())

        # 3) Non-peer-reviewed (arXiv OR missing venue)
        mask_peer = ~df_after_dedup.apply(is_non_peer_row, axis=1)
        n_non_peer = int((~mask_peer).sum())

        df_for_screen = df_after_dedup[mask_en & mask_peer].copy()

        print("[PRISMA] Total identified (2016–2025) =", total_identified)
        print("[PRISMA] Removed before screening:")
        print("         Duplicates =", n_duplicates)
        print("         Non-English =", n_non_english)
        print("         Non-peer-reviewed (arXiv or missing venue) =", n_non_peer)
        print("[PRISMA] Records to screen (after removals) =", len(df_for_screen))

        # ---- Title/Abstract screening ONCE (A∧B∧C) ----
        df_for_screen["match_title"] = df_for_screen.apply(match_title_A_and_B_and_C, axis=1)
        df_for_screen["match_abs"] = df_for_screen.apply(match_abstract_A_and_B_and_C, axis=1)

        n_title = int(df_for_screen["match_title"].sum())
        n_abs = int(df_for_screen["match_abs"].sum())
        n_both = int((df_for_screen["match_title"] & df_for_screen["match_abs"]).sum())
        screened_in = df_for_screen[df_for_screen["match_title"] | df_for_screen["match_abs"]].copy()
        n_union = len(screened_in)

        print("[PRISMA] Screening (title/abstract only):")
        print(f"         Title matches = {n_title}")
        print(f"         Abstract matches = {n_abs}")
        print(f"         Both = {n_both}")
        print(f"         Kept after screening (union) = {n_union}")
        print(f"         Excluded at screening = {len(df_for_screen) - n_union}")

        # S2: save the screened-in set
        df_s2 = screened_in
        S2 = _save_stage(df_s2, LENS_DIR / "stages", "S2_blockfilter")

        # S4: tag for descriptive reporting
        df_tagged = tag_inclusions_exclusions(df_s2)
        S4 = _save_stage(df_tagged, LENS_DIR / "stages", "S4_tagged")
        tagged = df_tagged
        src_mode = "api"

    else:
        print("Using Lens CSV imports (no token)…")
        df0 = import_lens_exports()  # raw import (no filtering here)

        # S1: apply the same year guard used in the API branch
        df_s1 = df0[(df0["year"].fillna(0).astype(int) >= y1) &
                    (df0["year"].fillna(0).astype(int) <= y2)]
        S1 = _save_stage(df_s1, LENS_DIR / "stages", "S1_year")

        # ---- PRISMA counts (same order as API branch) ----
        total_identified = len(df_s1)

        df_after_dedup = dedupe_df(df_s1)
        n_duplicates = total_identified - len(df_after_dedup)

        mask_en = df_after_dedup.apply(is_english_row, axis=1)
        n_non_english = int((~mask_en).sum())

        mask_peer = ~df_after_dedup.apply(is_non_peer_row, axis=1)
        n_non_peer = int((~mask_peer).sum())

        df_for_screen = df_after_dedup[mask_en & mask_peer].copy()

        print("[PRISMA] Total identified (2016–2025) =", total_identified)
        print("[PRISMA] Removed before screening:")
        print("         Duplicates =", n_duplicates)
        print("         Non-English =", n_non_english)
        print("         Non-peer-reviewed (arXiv or missing venue) =", n_non_peer)
        print("[PRISMA] Records to screen (after removals) =", len(df_for_screen))

        # Title/Abstract screening ONCE
        df_for_screen["match_title"] = df_for_screen.apply(match_title_A_and_B_and_C, axis=1)
        df_for_screen["match_abs"] = df_for_screen.apply(match_abstract_A_and_B_and_C, axis=1)

        n_title = int(df_for_screen["match_title"].sum())
        n_abs = int(df_for_screen["match_abs"].sum())
        n_both = int((df_for_screen["match_title"] & df_for_screen["match_abs"]).sum())
        screened_in = df_for_screen[df_for_screen["match_title"] | df_for_screen["match_abs"]].copy()
        n_union = len(screened_in)

        print("[PRISMA] Screening (title/abstract only):")
        print(f"         Title matches = {n_title}")
        print(f"         Abstract matches = {n_abs}")
        print(f"         Both = {n_both}")
        print(f"         Kept after screening (union) = {n_union}")
        print(f"         Excluded at screening = {len(df_for_screen) - n_union}")

        # S2: screened-in set
        df_s2 = screened_in
        S2 = _save_stage(df_s2, LENS_DIR / "stages", "S2_blockfilter")

        # S4: tag for descriptive reporting
        df_tagged = tag_inclusions_exclusions(df_s2)
        S4 = _save_stage(df_tagged, LENS_DIR / "stages", "S4_tagged")
        tagged = df_tagged
        src_mode = "csv"
        # If you want S0 symmetry in logs, you can skip or set None
        S0 = None

    # Save canonical CSV for merging with other sources
    out_path = RAW / "lens.csv"
    tagged.to_csv(out_path, index=False)
    print(f"Saved Lens results → {out_path} ({len(tagged)} rows)")

    # ---- PRISMA-friendly log ----
    log = {}
    log["source_mode"] = src_mode
    if src_mode == "api":
        log["S0_raw_api"] = S0
    log["S1_year"] = S1
    log["S2_blockfilter"] = S2
    log["S4_tagged_final"] = S4

    log["by_year"] = tagged["year"].value_counts(dropna=False).sort_index().to_dict()
    log["peer_reviewed_true"] = int(tagged["I1_peer_reviewed"].sum())
    log["english_true"] = int(tagged["I2_english"].sum())
    log["arxiv_like_only"] = int(((tagged["arxiv_like"]) & ~tagged["I1_peer_reviewed"]).sum())
    log["I_all_true"] = int(tagged["I_all"].sum())
    log["E_any_true"] = int(tagged["E_any"].sum())
    excl_cols = ["E1_non_archival_only", "E2_pure_safety", "E3_pure_interpret_only", "E4_non_llm_modality",
                 "E5_no_eval"]
    log["exclusions_breakdown"] = {c: int(tagged[c].sum()) for c in excl_cols}

    log["prisma"] = {
        "total_identified": int(total_identified),
        "removed_duplicates": int(n_duplicates),
        "removed_non_english": int(n_non_english),
        "removed_non_peer": int(n_non_peer),
        "records_screened": int(len(df_for_screen)),
        "screen_kept_union": int(n_union),
        "screen_excluded": int(len(df_for_screen) - n_union)
    }

    with open(LOGS_DIR / "lens_log.json", "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)

    print("Lens logs:")
    print(json.dumps(log, indent=2))
    return tagged


if __name__ == "__main__":
    run_lens(*YEARS)

#  $env:LENS_API_TOKEN = "your_lens_api_token"