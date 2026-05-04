// src/App.tsx
import React, { useEffect, useMemo, useState } from "react";
import { Routes, Route, NavLink } from "react-router-dom";
import {
  Activity,
  BarChart3,
  CalendarRange,
  Download,
  ExternalLink,
  Filter,
  LineChart,
  PieChart as PieIcon,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { toCanvas } from "html-to-image";
import { jsPDF } from "jspdf";
import Triangle from "./components/Triangle";
import {
  Area,
  AreaChart,
  Bar,
  BarChart as ReBarChart,
  Cell,
  CartesianGrid,
  Legend,
  Pie,
  PieChart as RePieChart,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";

export type QuestionId = "Q1" | "Q2" | "Q3" | "Q4" | "Q5" | "Q6";

export interface Paper {
  question_id: QuestionId | string;
  cluster: string;
  subcluster: string;
  title: string;
  year: number | null;
  venue: string;
  url: string;
  directional_claim: string;
  mentions_fairness: boolean;
  mentions_xai: boolean;
  mentions_llm: boolean;
}

const questionMeta: Record<QuestionId, { label: string; description: string }> = {
  Q1: {
    label: "Q1: Fairness → Explainability",
    description: "Fairness/bias concerns motivate or shape explainability/XAI methods.",
  },
  Q2: {
    label: "Q2: Explainability → Fairness",
    description: "XAI methods are used to detect, measure, or mitigate bias/unfairness.",
  },
  Q3: {
    label: "Q3: Fairness → LLMs",
    description: "Fairness/bias is defined or operationalized specifically for LLMs.",
  },
  Q4: {
    label: "Q4: LLMs → Fairness",
    description: "LLMs affect, amplify, or address fairness/discrimination.",
  },
  Q5: {
    label: "Q5: Explainability → LLMs",
    description: "XAI methods are applied to analyze or interpret LLM behaviour.",
  },
  Q6: {
    label: "Q6: LLMs → Explainability",
    description: "LLMs advance or challenge explainability (e.g., self-explanations, CoT).",
  },
};

const questionOrder = Object.keys(questionMeta) as QuestionId[];

type YearFilter = {
  min: number | null;
  max: number | null;
};

type ExplorerProps = {
  filteredPapers: Paper[];
  questionMeta: typeof questionMeta;
  questionOrder: QuestionId[];
  activeQuestions: QuestionId[];
  toggleQuestion: (qid: QuestionId) => void;
  clearQuestions: () => void;
  showPaperDetails: (paper: Paper) => void;
  yearFilter: YearFilter;
  setYearFilter: React.Dispatch<React.SetStateAction<YearFilter>>;
  years: YearFilter;
  totalsByQuestion: Record<QuestionId, number>;
  uniqueVenues: number;
  uniquePapers: number;
  uniqueFilteredPapers: number;
  handleReset: () => void;
  handleSelectAllQuestions: () => void;
  filtersActive: boolean;
  listTitle: string;
};

const downloadChart = (elementId: string, filename: string) => {
  const el = document.getElementById(elementId);
  if (!el) return;

  // 1. Create a hidden container for isolated capture
  const container = document.createElement("div");
  container.style.position = "absolute";
  container.style.top = "-9999px";
  container.style.left = "-9999px";
  container.style.width = el.offsetWidth + "px";
  document.body.appendChild(container);

  // 2. Clone the element and clean it for export
  const clone = el.cloneNode(true) as HTMLElement;
  clone.style.height = "auto";
  clone.style.minHeight = "0";
  clone.style.display = "block";
  clone.style.background = "#ffffff";
  clone.style.color = "#000000";
  clone.style.padding = "20px";
  clone.style.borderRadius = "0";
  clone.style.boxShadow = "none";
  container.appendChild(clone);

  // 3. Force clean styles in the clone for export
  // Hide UI chrome
  const toHide = clone.querySelectorAll(".panel-head, .triangle-hint, .hide-on-export, .taxonomy-controls, .venue-control");
  toHide.forEach((node) => {
    (node as HTMLElement).style.display = "none";
  });

  // Strip dark-mode backgrounds from inner wrappers
  const bgTargets = clone.querySelectorAll(".triangle-wrapper, .chart-shell, .insight-card");
  bgTargets.forEach((node) => {
    const htmlNode = node as HTMLElement;
    htmlNode.style.background = "transparent";
    htmlNode.style.backgroundColor = "transparent";
    htmlNode.style.border = "none";
    htmlNode.style.boxShadow = "none";
    htmlNode.style.backdropFilter = "none";
  });

  // Force dark colors for text and lines
  const darkColorTargets = clone.querySelectorAll<HTMLElement | SVGElement>(
    ".insight-list, .insight-list *, .recharts-legend-wrapper *, .recharts-default-legend *, " +
    "text, tspan, .vertex-label, " +
    ".recharts-cartesian-axis-line, .recharts-cartesian-axis-tick-line, " +
    ".recharts-cartesian-grid line"
  );
  
  darkColorTargets.forEach((node) => {
    const isLine = node.tagName.toLowerCase() === "line" || node.tagName.toLowerCase() === "path";
    if (isLine) {
      node.style.setProperty("stroke", "#222222", "important");
      if (node.closest('.recharts-cartesian-grid')) {
        node.style.setProperty("opacity", "0.2", "important");
      } else {
        node.style.setProperty("opacity", "0.6", "important");
      }
    } else {
      node.style.setProperty("color", "#222222", "important");
      node.style.setProperty("fill", "#222222", "important");
      node.style.setProperty("stroke", "none", "important");
    }
  });

  // Ensure text elements that are not part of legends are dark
  const allElements = clone.querySelectorAll("*");
  allElements.forEach((node) => {
    const htmlNode = node as HTMLElement;
    const tag = htmlNode.tagName.toLowerCase();
    const isLegendItem = htmlNode.closest(".recharts-legend-item") || htmlNode.closest(".insight-list li div");
    const isText = tag === "span" || tag === "p" || tag === "h2" || tag === "h3" || tag === "strong";
    const isSvgText = tag === "text";
    
    if ((isText || isSvgText) && !isLegendItem) {
      htmlNode.style.setProperty("color", "#111111", "important");
      htmlNode.style.setProperty("fill", "#111111", "important");
    }
  });

  toCanvas(clone, {
    backgroundColor: "#ffffff",
    pixelRatio: 3,
  })
    .then((canvas) => {
      const imgData = canvas.toDataURL("image/png");
      const pdf = new jsPDF({
        orientation: canvas.width > canvas.height ? "landscape" : "portrait",
        unit: "px",
        format: [canvas.width, canvas.height]
      });
      
      pdf.addImage(imgData, "PNG", 0, 0, canvas.width, canvas.height);
      pdf.save(filename.replace(".png", ".pdf"));
    })
    .catch((err) => {
      console.error("PDF Export Failed:", err);
    })
    .finally(() => {
      document.body.removeChild(container);
    });
};

type InsightsProps = {
  papers: Paper[];
  questionMeta: typeof questionMeta;
  insights: any; // Dynamic insights data
};

const ChartTooltip: React.FC<{
  active?: boolean;
  payload?: Array<{ value: number; name: string }>;
  label?: number | string;
}> = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-label">{label}</p>
      {payload.map((row) => (
        <span key={row.name}>
          {row.name}: <strong>{row.value}</strong>
        </span>
      ))}
    </div>
  );
};

const PaperDetailModal: React.FC<{ paper: Paper; onClose: () => void }> = ({ paper, onClose }) => {
  const hasExternalLink = Boolean(paper.url && paper.url !== "nan" && /^https?:\/\//i.test(paper.url));

  React.useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div className="detail-overlay" onClick={onClose}>
      <div className="detail-panel" onClick={(e) => e.stopPropagation()}>
        <button className="ghost-button detail-close" onClick={onClose}>
          Close
        </button>
        <p className="eyebrow">{paper.cluster || "Directional insight"}</p>
        <h2>{paper.title}</h2>
        <div className="detail-meta">
          {paper.year && <span>{paper.year}</span>}
          {paper.venue && <span>{paper.venue}</span>}
          <span>Question · {paper.question_id}</span>
        </div>
        {paper.directional_claim && (
          <div className="detail-section">
            <h4>Directional claim</h4>
            <p>{paper.directional_claim}</p>
          </div>
        )}
        <div className="detail-tags">
          {paper.mentions_fairness && <span className="tag tag-fairness">Fairness/Bias</span>}
          {paper.mentions_xai && <span className="tag tag-xai">Explainability</span>}
          {paper.mentions_llm && <span className="tag tag-llm">LLMs</span>}
        </div>
        {hasExternalLink && (
          <button
            className="ghost-button visit-link"
            onClick={() => window.open(paper.url!, "_blank", "noopener,noreferrer")}
          >
            Visit source
            <ExternalLink size={16} />
          </button>
        )}
      </div>
    </div>
  );
};

const ExplorerView: React.FC<ExplorerProps> = ({
  filteredPapers,
  questionMeta,
  questionOrder,
  activeQuestions,
  toggleQuestion,
  clearQuestions,
  showPaperDetails,
  yearFilter,
  setYearFilter,
  years,
  totalsByQuestion,
  uniqueVenues,
  uniquePapers,
  uniqueFilteredPapers,
  handleReset,
  handleSelectAllQuestions,
  filtersActive,
  listTitle,
}) => {
  return (
    <div className="app-root">
      <div className="aurora" aria-hidden="true" />
      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Systematic review categorization</p>
          <h1>FAIR–LENS</h1>
          <p className="subtitle">
            Interactive view of how included papers connect <strong>Fairness/Bias</strong>, <strong>Explainability</strong>, and{" "}
            <strong>LLMs</strong> via six directional questions (Q1–Q6).
          </p>
          <div className="hero-actions">
            <button className="ghost-button" onClick={handleReset}>
              <RefreshCw size={16} />
              Reset view
            </button>
            <span className="hero-hint">
              {filtersActive ? "Filters active — showcasing a curated slice" : "Tap wedges or chips to focus"}
            </span>
          </div>
        </div>

        <div className="stat-grid">
          <div className="stat-card">
            <span className="stat-label">Unique relevant papers</span>
            <strong className="stat-value">{uniquePapers || "—"}</strong>
            <span className="stat-meta">Distinct papers answering Q1–Q6</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Visible rows</span>
            <strong className="stat-value">{filteredPapers.length}</strong>
            <span className="stat-meta">
              {activeQuestions.length
                ? `${activeQuestions.length} focus areas`
                : "All questions. Relevant papers to all Qs presenting the overlaps when no focus area is selected."}
            </span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Unique visible papers</span>
            <strong className="stat-value">{uniqueFilteredPapers || "—"}</strong>
            <span className="stat-meta">Distinct papers in current view</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Distinct venues</span>
            <strong className="stat-value">{uniqueVenues || "—"}</strong>
            <span className="stat-meta">Conferences & journals</span>
          </div>
        </div>
      </header>

      <main className="content-grid">
        <section className="left-column">
          <article className="panel triangle-panel" id="chart-triangle">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Relationship map</p>
                <h2>Bias · Explainability · LLMs</h2>
              </div>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <button
                  className="ghost-button hide-on-export"
                  onClick={() => downloadChart("chart-triangle", "relationship_map.png")}
                  title="Download Plot"
                  style={{ padding: "0.4rem", borderRadius: "50%" }}
                >
                  <Download size={18} />
                </button>
                <Sparkles size={18} />
              </div>
            </div>
            <Triangle activeQuestions={activeQuestions} onToggleQuestion={toggleQuestion} />
          </article>

          <article className="panel legend-panel">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Directional questions</p>
                <h3>Pick your focus</h3>
              </div>
              <div className="legend-actions">
                <button className="ghost-button" onClick={handleSelectAllQuestions}>
                  Select all
                </button>
                <button className="ghost-button" onClick={clearQuestions} disabled={!activeQuestions.length}>
                  Clear
                </button>
              </div>
            </div>
            <div className="legend-grid">
              {questionOrder.map((qid) => {
                const isActive = activeQuestions.includes(qid);
                return (
                  <button key={qid} className={`legend-chip ${isActive ? "is-active" : ""}`} onClick={() => toggleQuestion(qid)}>
                    <div className="chip-heading">
                      <span className="chip-id">{qid}</span>
                      <span className="chip-count">{totalsByQuestion[qid]} papers</span>
                    </div>
                    <p className="chip-title">{questionMeta[qid].label}</p>
                    <span className="chip-desc">{questionMeta[qid].description}</span>
                  </button>
                );
              })}
            </div>
          </article>
        </section>

        <section className="panel list-panel">
          <div className="panel-head list-head">
            <div>
              <p className="eyebrow">{filtersActive ? "Curated selection" : "Full compendium"}</p>
              <h2>{listTitle}</h2>
            </div>
            <div className={`filter-pill ${filtersActive ? "is-active" : ""}`}>
              <Filter size={16} />
              {filtersActive ? "Filters on" : "No filters"}
            </div>
          </div>

          {years.min !== null && years.max !== null && (
            <div className="year-card">
              <div className="year-card-head">
                <CalendarRange size={16} />
                <span>Year range</span>
              </div>
              <label>
                From
                <input
                  type="number"
                  value={yearFilter.min ?? ""}
                  min={years.min}
                  max={years.max}
                  onChange={(e) =>
                    setYearFilter((prev) => ({
                      ...prev,
                      min: e.target.value ? parseInt(e.target.value, 10) : years.min,
                    }))
                  }
                />
              </label>
              <label>
                to
                <input
                  type="number"
                  value={yearFilter.max ?? ""}
                  min={years.min}
                  max={years.max}
                  onChange={(e) =>
                    setYearFilter((prev) => ({
                      ...prev,
                      max: e.target.value ? parseInt(e.target.value, 10) : years.max,
                    }))
                  }
                />
              </label>
            </div>
          )}

          <div className="active-chips">
            {questionOrder.map((qid) => (
              <span
                key={`pill-${qid}`}
                className={`question-pill ${activeQuestions.includes(qid) ? "is-active" : ""}`}
                onClick={() => toggleQuestion(qid)}
                role="button"
                tabIndex={0}
                onKeyDown={(evt) => {
                  if (evt.key === "Enter" || evt.key === " ") {
                    evt.preventDefault();
                    toggleQuestion(qid);
                  }
                }}
              >
                {qid}
              </span>
            ))}
          </div>

          <p className="count-text">
            Showing <strong>{filteredPapers.length}</strong> papers. Duplicates arise when a paper belongs to more than one directional
            question.
          </p>

          <div className="paper-scroll">
            {filteredPapers.length === 0 && (
              <div className="empty-state">
                <Sparkles size={20} />
                <p>No papers match the current filters. Try expanding the year range or selecting more directions.</p>
              </div>
            )}

            {filteredPapers.map((p, idx) => (
              <article key={`${p.title}-${idx}`} className="paper-card">
                <div className="paper-card-head">
                  <div>
                    {p.cluster && <span className="paper-cluster">{p.cluster}</span>}
                    <h3>{p.title}</h3>
                  </div>
                  <div className="paper-meta">
                    {p.year && <span>{p.year}</span>}
                    {p.venue && <span>{p.venue}</span>}
                    <button className="paper-open" onClick={() => showPaperDetails(p)}>
                      Open
                      <ExternalLink size={14} />
                    </button>
                  </div>
                </div>
                {p.directional_claim && <p className="paper-claim">{p.directional_claim}</p>}
                <div className="paper-tags">
                  {p.mentions_fairness && <span className="tag tag-fairness">Fairness/Bias</span>}
                  {p.mentions_xai && <span className="tag tag-xai">Explainability</span>}
                  {p.mentions_llm && <span className="tag tag-llm">LLMs</span>}
                  <span className="tag tag-qid">{p.question_id}</span>
                </div>
              </article>
            ))}
          </div>
        </section>
      </main>

      <footer className="app-footer">
        FAIR–LENS visualization prototype · Result of PRISMA, taking an extra step.
      </footer>
    </div>
  );
};

const InsightsView: React.FC<InsightsProps> = ({ papers, questionMeta, insights }) => {
  const [venueLimit, setVenueLimit] = useState(6);

  const questionOrder = Object.keys(questionMeta) as QuestionId[];

  const yearSeries = useMemo(() => {
    const buckets: Record<number, number> = {};
    papers.forEach((paper) => {
      if (!paper.year) return;
      buckets[paper.year] = (buckets[paper.year] || 0) + 1;
    });
    return Object.entries(buckets)
      .map(([year, value]) => ({ year: Number(year), value }))
      .sort((a, b) => a.year - b.year);
  }, [papers]);

  const questionSeries = useMemo(
    () =>
      questionOrder.map((qid) => ({
        name: questionMeta[qid].label,
        value: papers.filter((p) => (p.question_id as QuestionId) === qid).length,
        qid,
      })),
    [papers, questionMeta, questionOrder]
  );

  const venueSeries = useMemo(() => {
    const counts: Record<string, number> = {};
    papers.forEach((paper) => {
      const key = paper.venue?.trim();
      if (!key) return;
      counts[key] = (counts[key] || 0) + 1;
    });
    const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    const visible = sorted.slice(0, venueLimit);
    return visible.map(([name, value]) => ({ name, value }));
  }, [papers, venueLimit]);

  const mentionStats = useMemo(() => {
    const base = {
      fairness: 0,
      xai: 0,
      llm: 0,
      fairnessXai: 0,
      fairnessLlm: 0,
      xaiLlm: 0,
    };
    papers.forEach((paper) => {
      if (paper.mentions_fairness) base.fairness += 1;
      if (paper.mentions_xai) base.xai += 1;
      if (paper.mentions_llm) base.llm += 1;
      if (paper.mentions_fairness && paper.mentions_xai) base.fairnessXai += 1;
      if (paper.mentions_fairness && paper.mentions_llm) base.fairnessLlm += 1;
      if (paper.mentions_xai && paper.mentions_llm) base.xaiLlm += 1;
    });
    return base;
  }, [papers]);

  const mentionSeries = [
    { name: "Fairness mentions", value: mentionStats.fairness, fill: "#f4a261" },
    { name: "Explainability mentions", value: mentionStats.xai, fill: "#a3b18a" },
    { name: "LLM mentions", value: mentionStats.llm, fill: "#8ecae6" },
  ];

  const comboSeries = [
    { name: "Fairness ↔ Explainability", value: mentionStats.fairnessXai, fill: "#f9c74f" },
    { name: "Fairness ↔ LLMs", value: mentionStats.fairnessLlm, fill: "#f9844a" },
    { name: "Explainability ↔ LLMs", value: mentionStats.xaiLlm, fill: "#90be6d" },
  ];

  // Question trends over time
  const questionTrends = useMemo(() => {
    const trends: Record<number, Record<QuestionId, number>> = {};
    papers.forEach((paper) => {
      if (!paper.year) return;
      const qid = paper.question_id as QuestionId;
      if (!questionOrder.includes(qid)) return;
      if (!trends[paper.year]) {
        trends[paper.year] = { Q1: 0, Q2: 0, Q3: 0, Q4: 0, Q5: 0, Q6: 0 };
      }
      trends[paper.year][qid] = (trends[paper.year][qid] || 0) + 1;
    });
    const years = Object.keys(trends)
      .map(Number)
      .sort((a, b) => a - b);
    return years.map((year) => ({
      year,
      ...trends[year],
    }));
  }, [papers, questionOrder]);

  // Cluster distribution
  const clusterSeries = useMemo(() => {
    const counts: Record<string, number> = {};
    papers.forEach((paper) => {
      const cluster = paper.cluster?.trim();
      if (!cluster) return;
      counts[cluster] = (counts[cluster] || 0) + 1;
    });
    return Object.entries(counts).map(([name, value]) => ({
      name: name.replace("↔", " ↔ "),
      value,
    }));
  }, [papers]);

  // Word frequency from titles (stop words filtered)
  const wordFrequency = useMemo(() => {
    const stopWords = new Set([
      'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
      'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
      'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
      'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
      'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who',
      'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few',
      'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
      'own', 'same', 'so', 'than', 'too', 'very', 'via', 'using', 'based'
    ]);

    const wordCounts: Record<string, number> = {};

    papers.forEach((paper) => {
      const title = paper.title?.toLowerCase() || '';
      // Split by non-word characters and filter
      const words = title.split(/\W+/).filter(word =>
        word.length > 3 && !stopWords.has(word) && !/^\d+$/.test(word)
      );

      words.forEach(word => {
        wordCounts[word] = (wordCounts[word] || 0) + 1;
      });
    });

    return Object.entries(wordCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20)
      .map(([word, count]) => ({
        name: word.charAt(0).toUpperCase() + word.slice(1),
        value: count
      }));
  }, [papers]);

  const [taxonomyCategory, setTaxonomyCategory] = useState<string>("Domains");
  const [activeTaxonomyQid, setActiveTaxonomyQid] = useState<QuestionId>("Q5");

  const totalPapers = papers.length;
  const activeYears = yearSeries.length ? `${yearSeries[0].year}–${yearSeries[yearSeries.length - 1].year}` : "—";
  const avgPerYear = yearSeries.length ? Math.round((totalPapers / yearSeries.length) * 10) / 10 : 0;
  const withLinks = papers.filter((p) => p.url && p.url !== "nan").length;

  // Safeguard: if insights data is not yet available, show a loader
  if (!insights || !insights.intersection_dist) {
    return (
      <div className="app-root insights-root">
        <div className="aurora" aria-hidden="true" />
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "60vh", flexDirection: "column", gap: "1rem" }}>
          <RefreshCw className="spin" size={48} style={{ color: "var(--brand)" }} />
          <p>Assembling systematic review insights...</p>
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Checking for finalized corpus analysis...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-root insights-root">
      <div className="aurora" aria-hidden="true" />
      <header className="insights-hero">
        <div>
          <p className="eyebrow">Category Insights</p>
          <h1>FAIR–LENS Observatory</h1>
          <p className="subtitle">
            High-level insights for the review: yearly cadence, venue concentration, and how fairness, explainability, and LLMs co-occur.
          </p>
        </div>
        <div className="insight-stats-row">
          <div className="mini-stat">
            <Activity size={18} />
            <div>
              <span>{totalPapers}</span>
              <p>Papers tracked</p>
            </div>
          </div>
          <div className="mini-stat">
            <LineChart size={18} />
            <div>
              <span>{activeYears}</span>
              <p>Temporal coverage</p>
            </div>
          </div>
          <div className="mini-stat">
            <PieIcon size={18} />
            <div>
              <span>{avgPerYear}</span>
              <p>Avg. per year</p>
            </div>
          </div>
          <div className="mini-stat">
            <BarChart3 size={18} />
            <div>
              <span>{withLinks}</span>
              <p>With accessible links</p>
            </div>
          </div>
        </div>
      </header>

      <main className="insights-content">
        <section className="insight-grid">
          <article className="insight-card wide" id="chart-cadence">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Cadence</p>
                <h2>Publication tempo</h2>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>Number of papers published each year</p>
              </div>
              <button
                className="ghost-button hide-on-export"
                onClick={() => downloadChart("chart-cadence", "publication_tempo.png")}
                title="Download Plot"
                style={{ padding: "0.4rem", borderRadius: "50%", alignSelf: "flex-start" }}
              >
                <Download size={18} />
              </button>
            </div>
            <div className="chart-shell">
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={yearSeries} margin={{ top: 10, right: 10, left: 50, bottom: 0 }}>
                  <defs>
                    <linearGradient id="yearGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8ecae6" stopOpacity={0.9} />
                      <stop offset="95%" stopColor="#8ecae6" stopOpacity={0.05} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                  <XAxis dataKey="year" stroke="rgba(255,255,255,0.5)" />
                  <YAxis allowDecimals={false} stroke="rgba(255,255,255,0.5)" />
                  <RechartsTooltip content={<ChartTooltip />} />
                  <Area type="monotone" dataKey="value" stroke="#8ecae6" strokeWidth={2} fill="url(#yearGradient)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="insight-card" id="chart-directional">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Questions</p>
                <h3>Directional balance</h3>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>Distribution of papers across the six research questions</p>
              </div>
              <button
                className="ghost-button hide-on-export"
                onClick={() => downloadChart("chart-directional", "directional_balance.png")}
                title="Download Plot"
                style={{ padding: "0.4rem", borderRadius: "50%", alignSelf: "flex-start" }}
              >
                <Download size={18} />
              </button>
            </div>
            <div className="chart-shell">
              <ResponsiveContainer width="100%" height={260}>
                <RePieChart>
                  <RechartsTooltip content={<ChartTooltip />} />
                  <Pie data={questionSeries} dataKey="value" nameKey="name" innerRadius={60} outerRadius={90} paddingAngle={2}>
                    {questionSeries.map((entry, index) => (
                      <Cell key={`slice-${entry.qid}`} fill={["#f4a261", "#f9844a", "#f9c74f", "#90be6d", "#43aa8b", "#577590"][index]} />
                    ))}
                  </Pie>
                </RePieChart>
              </ResponsiveContainer>
            </div>
            <ul className="insight-list" style={{ marginTop: "-0.5rem" }}>
              {questionSeries.map((row, index) => {
                const colors = ["#f4a261", "#f9844a", "#f9c74f", "#90be6d", "#43aa8b", "#577590"];
                return (
                  <li key={row.qid}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <span style={{ width: "12px", height: "12px", backgroundColor: colors[index], borderRadius: "2px" }} />
                      <span>{row.name}</span>
                    </div>
                    <strong>{row.value}</strong>
                  </li>
                );
              })}
            </ul>
          </article>

          <article className="insight-card" id="chart-discipline">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Diversity</p>
                <h3>Discipline distribution</h3>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>Research spread across different academic fields</p>
              </div>
              <button
                className="ghost-button hide-on-export"
                onClick={() => downloadChart("chart-discipline", "discipline_spread.png")}
                title="Download Plot"
                style={{ padding: "0.4rem", borderRadius: "50%", alignSelf: "flex-start" }}
              >
                <Download size={18} />
              </button>
            </div>
            <div className="chart-shell">
              <ResponsiveContainer width="100%" height={260}>
                <RePieChart>
                  <RechartsTooltip content={<ChartTooltip />} />
                  <Pie
                    data={insights?.venue_distribution || []}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={4}
                  >
                    {(insights?.venue_distribution || []).map((_, index) => {
                      const colors = ["#8ecae6", "#219ebc", "#023047", "#ffb703", "#fb8500", "#90be6d", "#43aa8b"];
                      return <Cell key={`discipline-${index}`} fill={colors[index % colors.length]} />;
                    })}
                  </Pie>
                </RePieChart>
              </ResponsiveContainer>
            </div>
            <ul className="insight-list" style={{ marginTop: "-0.5rem" }}>
              {(insights?.venue_distribution || []).map((row, index) => {
                const colors = ["#8ecae6", "#219ebc", "#023047", "#ffb703", "#fb8500", "#90be6d", "#43aa8b"];
                return (
                  <li key={row.name}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <span style={{ width: "12px", height: "12px", backgroundColor: colors[index % 7], borderRadius: "2px" }} />
                      <span>{row.name}</span>
                    </div>
                    <strong>{row.value}</strong>
                  </li>
                );
              })}
            </ul>
          </article>

          <article className="insight-card wide" id="chart-venues">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Venues</p>
                <h3>Where conversations cluster</h3>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>Most frequent conferences and journals publishing this research</p>
              </div>
              <div className="venue-control" style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
                <label className="hide-on-export">
                  Top venues ({venueLimit})
                  <input
                    type="range"
                    min={3}
                    max={10}
                    value={venueLimit}
                    onChange={(e) => setVenueLimit(parseInt(e.target.value, 10))}
                  />
                </label>
                <button
                  className="ghost-button hide-on-export"
                  onClick={() => downloadChart("chart-venues", "venue_clusters.png")}
                  title="Download Plot"
                  style={{ padding: "0.4rem", borderRadius: "50%" }}
                >
                  <Download size={18} />
                </button>
              </div>
            </div>
            <div className="chart-shell">
              <ResponsiveContainer width="100%" height={venueLimit * 45 + 60}>
                <ReBarChart
                  layout="vertical"
                  data={venueSeries}
                  margin={{ top: 5, right: 30, left: 10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                  <XAxis type="number" allowDecimals={false} stroke="rgba(255,255,255,0.5)" />
                  <YAxis dataKey="name" type="category" width={180} stroke="rgba(255,255,255,0.7)" />
                  <RechartsTooltip content={<ChartTooltip />} />
                  <Bar dataKey="value" fill="#f4a261" radius={[4, 4, 4, 4]} />
                </ReBarChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="insight-card" id="chart-mentions">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Mentions</p>
                <h3>Topical coverage</h3>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>How many papers mention each of the three topics</p>
              </div>
              <button
                className="ghost-button hide-on-export"
                onClick={() => downloadChart("chart-mentions", "topical_coverage.png")}
                title="Download Plot"
                style={{ padding: "0.4rem", borderRadius: "50%", alignSelf: "flex-start" }}
              >
                <Download size={18} />
              </button>
            </div>
            <div className="chart-shell">
              <ResponsiveContainer width="100%" height={240}>
                <RadialBarChart innerRadius="30%" outerRadius="100%" data={mentionSeries} startAngle={90} endAngle={-270} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                  <RadialBar dataKey="value" />
                  <RechartsTooltip content={<ChartTooltip />} />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
            <ul className="insight-list" style={{ marginTop: "-0.5rem" }}>
              {mentionSeries.map((row) => (
                <li key={row.name}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span style={{ width: "12px", height: "12px", backgroundColor: row.fill, borderRadius: "2px" }} />
                    <span>{row.name}</span>
                  </div>
                  <strong>{row.value}</strong>
                </li>
              ))}
            </ul>
          </article>

          <article className="insight-card" id="chart-intersections">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Intersections</p>
                <h3>Co-mention intensity</h3>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>Papers that combine two or more topics together</p>
              </div>
              <button
                className="ghost-button hide-on-export"
                onClick={() => downloadChart("chart-intersections", "comention_intensity.png")}
                title="Download Plot"
                style={{ padding: "0.4rem", borderRadius: "50%", alignSelf: "flex-start" }}
              >
                <Download size={18} />
              </button>
            </div>
            <div className="chart-shell">
              <ResponsiveContainer width="100%" height={240}>
                <RadialBarChart innerRadius="30%" outerRadius="100%" data={comboSeries} startAngle={90} endAngle={-270} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                  <RadialBar dataKey="value" />
                  <RechartsTooltip content={<ChartTooltip />} />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
            <ul className="insight-list" style={{ marginTop: "-0.5rem" }}>
              {comboSeries.map((row) => (
                <li key={row.name}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span style={{ width: "12px", height: "12px", backgroundColor: row.fill, borderRadius: "2px" }} />
                    <span>{row.name}</span>
                  </div>
                  <strong>{row.value}</strong>
                </li>
              ))}
            </ul>
          </article>

          <article className="insight-card wide" id="chart-intersectionality">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Integration</p>
                <h3>Evidence intersectionality</h3>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>Number of papers covering multiple FAIR-LENS directions simultaneously</p>
              </div>
              <button
                className="ghost-button hide-on-export"
                onClick={() => downloadChart("chart-intersectionality", "intersectionality_depth.png")}
                title="Download Plot"
                style={{ padding: "0.4rem", borderRadius: "50%", alignSelf: "flex-start" }}
              >
                <Download size={18} />
              </button>
            </div>
            <div className="chart-shell">
              <ResponsiveContainer width="100%" height={260}>
                <ReBarChart data={insights?.intersection_dist || []} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.2} vertical={false} />
                  <XAxis dataKey="count" label={{ value: 'Directions Covered', position: 'insideBottom', offset: -5 }} stroke="rgba(255,255,255,0.5)" />
                  <YAxis stroke="rgba(255,255,255,0.5)" />
                  <RechartsTooltip content={<ChartTooltip />} />
                  <Bar dataKey="value" fill="#8ecae6" radius={[4, 4, 0, 0]}>
                    {(insights?.intersection_dist || []).map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={parseInt(entry.count) > 3 ? "#f4a261" : "#8ecae6"} />
                    ))}
                  </Bar>
                </ReBarChart>
              </ResponsiveContainer>
            </div>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "1rem", textAlign: "center" }}>
              Papers covering <strong>4+ directions</strong> (shown in orange) represent the most integrated research in the corpus.
            </p>
          </article>

          <article className="insight-card wide" id="chart-taxonomy">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Taxonomy Explorer</p>
                <h3>Thematic focus by direction</h3>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>Top terms extracted from paper abstracts for each direction</p>
              </div>
              <div className="taxonomy-controls hide-on-export" style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                 <select 
                    value={taxonomyCategory} 
                    onChange={(e) => setTaxonomyCategory(e.target.value)}
                    className="select-input"
                 >
                    {Object.keys(insights.global_trends).map(cat => <option key={cat} value={cat}>{cat}</option>)}
                 </select>
                 <select 
                    value={activeTaxonomyQid} 
                    onChange={(e) => setActiveTaxonomyQid(e.target.value as QuestionId)}
                    className="select-input"
                 >
                    {Object.keys(questionMeta).map(qid => <option key={qid} value={qid}>{qid}</option>)}
                 </select>
                 <button
                  className="ghost-button"
                  onClick={() => downloadChart("chart-taxonomy", "taxonomy_explorer.png")}
                  title="Download Plot"
                  style={{ padding: "0.4rem", borderRadius: "50%" }}
                >
                  <Download size={18} />
                </button>
              </div>
            </div>
            <div className="chart-shell">
              <ResponsiveContainer width="100%" height={300}>
                <ReBarChart
                  layout="vertical"
                  data={insights.question_topics?.[activeTaxonomyQid]?.[taxonomyCategory] || []}
                  margin={{ top: 10, right: 30, left: 40, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" opacity={0.1} horizontal={false} />
                  <XAxis type="number" hide />
                  <YAxis dataKey="name" type="category" width={120} stroke="rgba(255,255,255,0.8)" fontSize={12} />
                  <RechartsTooltip content={<ChartTooltip />} />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                    {(insights.question_topics?.[activeTaxonomyQid]?.[taxonomyCategory] || []).map((_, index) => {
                       const colors = ["#f4a261", "#f9844a", "#f9c74f", "#90be6d", "#43aa8b", "#577590", "#8ecae6"];
                       return <Cell key={`tax-${index}`} fill={colors[index % colors.length]} />;
                    })}
                  </Bar>
                </ReBarChart>
              </ResponsiveContainer>
            </div>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "0.5rem", textAlign: "right", fontStyle: "italic" }}>
              Currently showing <strong>{taxonomyCategory}</strong> for <strong>{activeTaxonomyQid}</strong>
            </p>
          </article>

          <article className="insight-card wide" id="chart-trends">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Evolution</p>
                <h2>Question trends over time</h2>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>How focus on each research question has changed year by year</p>
              </div>
              <button
                className="ghost-button hide-on-export"
                onClick={() => downloadChart("chart-trends", "question_trends.png")}
                title="Download Plot"
                style={{ padding: "0.4rem", borderRadius: "50%", alignSelf: "flex-start" }}
              >
                <Download size={18} />
              </button>
            </div>
            <div className="chart-shell">
              <ResponsiveContainer width="100%" height={320}>
                <AreaChart data={questionTrends} margin={{ top: 10, right: 10, left: 50, bottom: 0 }}>
                  <defs>
                    <linearGradient id="q1Gradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f4a261" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#f4a261" stopOpacity={0.1} />
                    </linearGradient>
                    <linearGradient id="q2Gradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f9844a" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#f9844a" stopOpacity={0.1} />
                    </linearGradient>
                    <linearGradient id="q3Gradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f9c74f" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#f9c74f" stopOpacity={0.1} />
                    </linearGradient>
                    <linearGradient id="q4Gradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#90be6d" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#90be6d" stopOpacity={0.1} />
                    </linearGradient>
                    <linearGradient id="q5Gradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#43aa8b" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#43aa8b" stopOpacity={0.1} />
                    </linearGradient>
                    <linearGradient id="q6Gradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#577590" stopOpacity={0.8} />
                      <stop offset="95%" stopColor="#577590" stopOpacity={0.1} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                  <XAxis dataKey="year" stroke="rgba(255,255,255,0.5)" />
                  <YAxis allowDecimals={false} stroke="rgba(255,255,255,0.5)" />
                  <RechartsTooltip content={<ChartTooltip />} />
                  <Legend iconType="circle" />
                  <Area type="monotone" dataKey="Q1" stroke="#f4a261" strokeWidth={3} fill="url(#q1Gradient)" />
                  <Area type="monotone" dataKey="Q2" stroke="#f9844a" strokeWidth={3} fill="url(#q2Gradient)" />
                  <Area type="monotone" dataKey="Q3" stroke="#f9c74f" strokeWidth={3} fill="url(#q3Gradient)" />
                  <Area type="monotone" dataKey="Q4" stroke="#90be6d" strokeWidth={3} fill="url(#q4Gradient)" />
                  <Area type="monotone" dataKey="Q5" stroke="#43aa8b" strokeWidth={3} fill="url(#q5Gradient)" />
                  <Area type="monotone" dataKey="Q6" stroke="#577590" strokeWidth={3} fill="url(#q6Gradient)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="insight-card wide" id="chart-lineage">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Lineage</p>
                <h2>Model family evolution</h2>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>Frequency of model family mentions in titles and abstracts over time</p>
              </div>
              <button
                className="ghost-button hide-on-export"
                onClick={() => downloadChart("chart-lineage", "model_lineage.png")}
                title="Download Plot"
                style={{ padding: "0.4rem", borderRadius: "50%", alignSelf: "flex-start" }}
              >
                <Download size={18} />
              </button>
            </div>
            <div className="chart-shell">
              <ResponsiveContainer width="100%" height={320}>
                <AreaChart data={insights?.model_evolution || []} margin={{ top: 10, right: 30, left: 20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorGpt" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#8ecae6" stopOpacity={0.8}/><stop offset="95%" stopColor="#8ecae6" stopOpacity={0}/></linearGradient>
                    <linearGradient id="colorLlama" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#ffb703" stopOpacity={0.8}/><stop offset="95%" stopColor="#ffb703" stopOpacity={0}/></linearGradient>
                    <linearGradient id="colorBert" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#fb8500" stopOpacity={0.8}/><stop offset="95%" stopColor="#fb8500" stopOpacity={0}/></linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                  <XAxis dataKey="year" stroke="rgba(255,255,255,0.5)" />
                  <YAxis stroke="rgba(255,255,255,0.5)" />
                  <RechartsTooltip content={<ChartTooltip />} />
                  <Legend iconType="circle" />
                  <Area type="monotone" dataKey="gpt" name="GPT Family" stroke="#8ecae6" strokeWidth={3} fillOpacity={1} fill="url(#colorGpt)" />
                  <Area type="monotone" dataKey="llama" name="LLaMA Family" stroke="#ffb703" strokeWidth={3} fillOpacity={1} fill="url(#colorLlama)" />
                  <Area type="monotone" dataKey="bert" name="BERT Family" stroke="#fb8500" strokeWidth={3} fillOpacity={1} fill="url(#colorBert)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="insight-card wide" id="chart-focus">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Intent</p>
                <h2>Diagnostic vs Proactive split</h2>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>Comparing papers that audit/diagnose harms vs those that propose design requirements</p>
              </div>
              <button
                className="ghost-button hide-on-export"
                onClick={() => downloadChart("chart-focus", "intent_evolution.png")}
                title="Download Plot"
                style={{ padding: "0.4rem", borderRadius: "50%", alignSelf: "flex-start" }}
              >
                <Download size={18} />
              </button>
            </div>
            <div className="chart-shell">
              <ResponsiveContainer width="100%" height={320}>
                <ReBarChart data={insights?.focus_evolution || []} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.1} vertical={false} />
                  <XAxis dataKey="year" stroke="rgba(255,255,255,0.5)" />
                  <YAxis stroke="rgba(255,255,255,0.5)" />
                  <RechartsTooltip content={<ChartTooltip />} />
                  <Legend />
                  <Bar dataKey="Diagnostic (Audit)" fill="#577590" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Proactive (Design)" fill="#f4a261" radius={[4, 4, 0, 0]} />
                </ReBarChart>
              </ResponsiveContainer>
            </div>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "1rem", textAlign: "center" }}>
              <strong>Note:</strong> Proactive design (Q1, Q3) consistently lags behind diagnostic auditing across all years.
            </p>
          </article>

          <article className="insight-card" id="chart-clusters">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Clusters</p>
                <h3>Research clusters</h3>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>Major research themes combining multiple topics</p>
              </div>
              <button
                className="ghost-button hide-on-export"
                onClick={() => downloadChart("chart-clusters", "research_clusters.png")}
                title="Download Plot"
                style={{ padding: "0.4rem", borderRadius: "50%", alignSelf: "flex-start" }}
              >
                <Download size={18} />
              </button>
            </div>
            <div className="chart-shell">
              <ResponsiveContainer width="100%" height={260}>
                <RePieChart>
                  <RechartsTooltip content={<ChartTooltip />} />
                  <Pie
                    data={clusterSeries}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={2}
                  >
                    {clusterSeries.map((_, index) => {
                      const colors = ["#8ecae6", "#219ebc", "#023047", "#ffb703", "#fb8500", "#90be6d", "#43aa8b"];
                      return (
                        <Cell
                          key={`cluster-${index}`}
                          fill={colors[index % colors.length]}
                        />
                      );
                    })}
                  </Pie>
                </RePieChart>
              </ResponsiveContainer>
            </div>
            <ul className="insight-list" style={{ marginTop: "-0.5rem" }}>
              {clusterSeries.map((row, index) => {
                const colors = ["#8ecae6", "#219ebc", "#023047", "#ffb703", "#fb8500", "#90be6d", "#43aa8b"];
                return (
                  <li key={row.name}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <span style={{ width: "12px", height: "12px", backgroundColor: colors[index % 7], borderRadius: "2px", flexShrink: 0 }} />
                      <span>{row.name}</span>
                    </div>
                    <strong>{row.value}</strong>
                  </li>
                );
              })}
            </ul>
          </article>

          <article className="insight-card wide" id="chart-keywords">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Keywords</p>
                <h2>Most frequent terms</h2>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>Common meaningful words appearing in paper titles</p>
              </div>
              <button
                className="ghost-button hide-on-export"
                onClick={() => downloadChart("chart-keywords", "frequent_terms.png")}
                title="Download Plot"
                style={{ padding: "0.4rem", borderRadius: "50%", alignSelf: "flex-start" }}
              >
                <Download size={18} />
              </button>
            </div>
            <div className="chart-shell" style={{ padding: "2rem 1rem", minHeight: "300px" }}>
              <div style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "1rem",
                alignItems: "center",
                justifyContent: "center",
                textAlign: "center"
              }}>
                {wordFrequency.map((word, index) => {
                  const maxValue = wordFrequency[0].value;
                  const minValue = wordFrequency[wordFrequency.length - 1].value;
                  const range = maxValue - minValue;
                  const scale = range > 0 ? (word.value - minValue) / range : 0.5;
                  const fontSize = 0.9 + scale * 2.5; // 0.9rem to 3.4rem
                  const colors = ["#f4a261", "#f9844a", "#f9c74f", "#90be6d", "#43aa8b", "#577590", "#8ecae6"];
                  const color = colors[index % colors.length];

                  return (
                    <span
                      key={word.name}
                      style={{
                        fontSize: `${fontSize}rem`,
                        fontWeight: 600,
                        color: color,
                        opacity: 0.7 + scale * 0.3,
                        cursor: "default",
                        lineHeight: 1.2,
                        transition: "all 0.2s ease",
                      }}
                      title={`${word.name}: ${word.value} occurrences`}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.opacity = "1";
                        e.currentTarget.style.transform = "scale(1.1)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.opacity = String(0.7 + scale * 0.3);
                        e.currentTarget.style.transform = "scale(1)";
                      }}
                    >
                      {word.name}
                    </span>
                  );
                })}
              </div>
            </div>
          </article>
        </section>

      </main>

      <footer className="app-footer">Insights will auto-refresh as soon as new outputs feed the visualizer.</footer>
    </div>
  );
};

const FrameworkView: React.FC = () => {
  return (
    <div className="app-root insights-root">
      <div className="aurora" aria-hidden="true" />
      <header className="insights-hero" style={{ paddingBottom: "2rem" }}>
        <div>
          <p className="eyebrow" style={{ color: "var(--xai-color)" }}>Conceptual Framework</p>
          <h1>The FAIR–LENS Triad</h1>
          <p className="subtitle">
            Beyond isolated findings, this interactive model structures the results visually onto the core triangle of the review. The tensions, relationships, and volumes form the ultimate conclusion structure for the research.
          </p>
        </div>
      </header>

      <main className="insights-content" style={{ marginTop: 0 }}>

        {/* The Geometric Triangle Visual Header */}
        <section style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: "3rem",
          background: "rgba(255, 255, 255, 0.02)",
          borderRadius: "24px",
          border: "1px solid rgba(255, 255, 255, 0.05)",
          padding: "4rem 1rem 2rem",
          position: "relative",
          overflow: "hidden",
          width: "100%"
        }}>

          <style>{`
            .void-container {
              cursor: help;
              transition: all 0.3s ease;
            }
            .void-container:hover .void-circle {
              fill: rgba(255, 100, 100, 0.15) !important;
              stroke: rgba(255, 100, 100, 0.6) !important;
            }
            .void-container:hover .void-text {
              fill: rgba(255, 255, 255, 1) !important;
              font-weight: bold;
            }
            .void-tooltip {
              opacity: 0;
              transition: opacity 0.3s ease;
              pointer-events: none;
            }
            .void-container:hover .void-tooltip {
              opacity: 1;
            }
            .flow-container {
              display: flex;
              flex-direction: row;
              align-items: center;
              justify-content: center;
              gap: 2rem;
              width: 100%;
              margin-top: 1rem;
            }
            @media (max-width: 900px) {
              .flow-container {
                flex-direction: column;
                gap: 2rem;
              }
            }
          `}</style>

          <div style={{ textAlign: "center", marginBottom: "2rem", zIndex: 2 }}>
            <h2 style={{ fontSize: "2.5rem", letterSpacing: "-0.02em", color: "white", marginBottom: "0.5rem" }}>Synthesis Trajectory</h2>
            <p style={{ color: "var(--text-muted)", maxWidth: "800px", margin: "0 auto", lineHeight: 1.6 }}>
              The unweighted conceptual model serves merely as a theoretical starting point. By comprehensively mapping all 111 studies to the framework, the actual empirical imbalance defining current research priorities natively illuminates.
            </p>
          </div>

          <div className="flow-container" style={{ display: "grid", gridTemplateColumns: "1fr auto 550px", gap: "2rem", alignItems: "center", width: "100%", maxWidth: "1100px", margin: "2rem auto 0 auto" }}>
            {/* Step 1: The Theoretical Model */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", opacity: 0.9, background: "rgba(0,0,0,0.3)", padding: "2rem", borderRadius: "16px", border: "1px dashed rgba(255,255,255,0.1)" }}>
              <h3 style={{ color: "white", fontSize: "1.2rem", marginBottom: "1rem", letterSpacing: "1px", textTransform: "uppercase" }}>Conceptual Hypothesis</h3>
              <svg viewBox="0 0 200 200" style={{ width: "180px", height: "180px", overflow: "visible" }}>
                <defs>
                  <marker id="arrow-fair" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#f4a261" />
                  </marker>
                  <marker id="arrow-xai" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#a3b18a" />
                  </marker>
                  <marker id="arrow-llm" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#8ecae6" />
                  </marker>
                </defs>
                <polygon points="100,20 20,180 180,180" fill="none" stroke="#4b5563" strokeWidth="2" strokeDasharray="4 4" />
                <circle cx="100" cy="20" r="4" fill="#6b7280" />
                <circle cx="20" cy="180" r="4" fill="#6b7280" />
                <circle cx="180" cy="180" r="4" fill="#6b7280" />

                <text x="100" y="10" fill="#9ca3af" textAnchor="middle" fontSize="10">Fairness/Bias</text>
                <text x="0" y="195" fill="#9ca3af" textAnchor="middle" fontSize="10">Explainability</text>
                <text x="195" y="195" fill="#9ca3af" textAnchor="middle" fontSize="10" fontWeight="bold">LLMs</text>

                {/* Conceptual Flow Indicators */}
                <path d="M 90,40 L 40,150" stroke="#4b5563" strokeWidth="1" strokeDasharray="2 2" marker-end="url(#arrow-xai)" opacity="0.4" />
                <path d="M 110,40 L 160,150" stroke="#4b5563" strokeWidth="1" strokeDasharray="2 2" marker-end="url(#arrow-llm)" opacity="0.4" />
                <path d="M 40,185 L 160,185" stroke="#4b5563" strokeWidth="1" strokeDasharray="2 2" marker-end="url(#arrow-llm)" opacity="0.4" />
              </svg>
              <div style={{ marginTop: "1rem", color: "#9ca3af", fontSize: "0.9rem", textAlign: "center", lineHeight: 1.5 }}>
                <strong style={{ color: "white" }}>Expected Balance:</strong>
                <p style={{ marginTop: "0.5rem" }}>Prior to the review, theoretical frameworks implied holistic, roughly equal research addressing all three nodes simultaneously to build trustworthy generative AI.</p>
              </div>
            </div>

            {/* Transition Arrow */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", color: "#8ecae6", opacity: 0.8, padding: "0 1rem" }}>
              <Sparkles size={24} style={{ marginBottom: "0.5rem" }} />
              <div style={{ height: "2px", width: "80px", background: "linear-gradient(90deg, transparent, #8ecae6, transparent)", marginBottom: "0.5rem" }} />
              <span style={{ fontSize: "0.8rem", fontWeight: "bold", letterSpacing: "1px", textTransform: "uppercase" }}>Mapping</span>
              <span style={{ fontSize: "0.8rem", color: "white" }}>111 Final Papers</span>
              <div style={{ height: "2px", width: "80px", background: "linear-gradient(90deg, transparent, #8ecae6, transparent)", marginTop: "0.5rem" }} />
            </div>

            {/* Custom Visualization (The Empirical Triad) */}
            <div style={{ width: "100%", margin: "0 auto", position: "relative" }}>
              <svg viewBox="0 0 500 400" style={{ width: "100%", height: "auto", overflow: "visible" }}>
                <defs>
                  <filter id="glow" filterUnits="userSpaceOnUse" x="-100" y="-100" width="700" height="600">
                    <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                    <feMerge>
                      <feMergeNode in="coloredBlur" />
                      <feMergeNode in="SourceGraphic" />
                    </feMerge>
                  </filter>
                  <linearGradient id="edgeBaseGrad" gradientUnits="userSpaceOnUse" x1="100" y1="300" x2="400" y2="300">
                    <stop offset="0%" stopColor="#a3b18a" />
                    <stop offset="100%" stopColor="#8ecae6" />
                  </linearGradient>
                  <linearGradient id="edgeLeftGrad" gradientUnits="userSpaceOnUse" x1="250" y1="40" x2="100" y2="300">
                    <stop offset="0%" stopColor="#f4a261" />
                    <stop offset="100%" stopColor="#a3b18a" />
                  </linearGradient>
                  <linearGradient id="edgeRightGrad" gradientUnits="userSpaceOnUse" x1="250" y1="40" x2="400" y2="300">
                    <stop offset="0%" stopColor="#f4a261" />
                    <stop offset="100%" stopColor="#8ecae6" />
                  </linearGradient>
                </defs>

                {/* Edges (Volumes determine thickness) */}

                {/* E <-> LLMs (n=136 - Thickest - Base) */}
                <line x1="100" y1="300" x2="400" y2="300" stroke="url(#edgeBaseGrad)" strokeWidth="24" strokeLinecap="round" filter="url(#glow)" opacity="1" />

                {/* F <-> E (n=69 - Medium - Left Edge) */}
                <line x1="250" y1="40" x2="100" y2="300" stroke="url(#edgeLeftGrad)" strokeWidth="12" strokeLinecap="round" filter="url(#glow)" opacity="0.9" />

                {/* F <-> LLMs (n=65 - Thinnest - Right Edge) */}
                <line x1="250" y1="40" x2="400" y2="300" stroke="url(#edgeRightGrad)" strokeWidth="10" strokeLinecap="round" filter="url(#glow)" opacity="0.8" />

                {/* Directional Indicators (Q1-Q6) */}
                {/* Q1: F -> E */}
                <path d="M 210,105 L 165,190" stroke="#f4a261" strokeWidth="2" marker-end="url(#arrow-xai)" opacity="0.8" />
                <text x="175" y="135" fill="#f4a261" fontSize="10" fontWeight="bold">Q1</text>

                {/* Q2: E -> F */}
                <path d="M 145,215 L 195,130" stroke="#a3b18a" strokeWidth="2" marker-end="url(#arrow-fair)" opacity="0.8" />
                <text x="185" y="195" fill="#a3b18a" fontSize="10" fontWeight="bold">Q2</text>

                {/* Q3: F -> L */}
                <path d="M 290,105 L 335,190" stroke="#f4a261" strokeWidth="2" marker-end="url(#arrow-llm)" opacity="0.8" />
                <text x="325" y="135" fill="#f4a261" fontSize="10" fontWeight="bold">Q3</text>

                {/* Q4: L -> F */}
                <path d="M 355,215 L 305,130" stroke="#8ecae6" strokeWidth="2" marker-end="url(#arrow-fair)" opacity="0.8" />
                <text x="315" y="195" fill="#8ecae6" fontSize="10" fontWeight="bold">Q4</text>

                {/* Q5: E -> L */}
                <path d="M 180,285 L 320,285" stroke="#a3b18a" strokeWidth="2" marker-end="url(#arrow-llm)" opacity="0.8" />
                <text x="250" y="278" fill="#a3b18a" fontSize="10" fontWeight="bold">Q5</text>

                {/* Q6: L -> E */}
                <path d="M 320,315 L 180,315" stroke="#8ecae6" strokeWidth="2" marker-end="url(#arrow-xai)" opacity="0.8" />
                <text x="250" y="328" fill="#8ecae6" fontSize="10" fontWeight="bold">Q6</text>

                {/* Central Void (Interactive) */}
                <g className="void-container">
                  <circle cx="250" cy="200" r="40" className="void-circle" fill="rgba(255,255,255,0.03)" stroke="rgba(255,255,255,0.1)" strokeWidth="1" strokeDasharray="4 4" />
                  <text x="250" y="205" className="void-text" fill="rgba(255, 255, 255, 0.5)" textAnchor="middle" fontSize="12" letterSpacing="1px">THE VOID</text>

                  {/* Tooltip Content */}
                  <g className="void-tooltip" transform="translate(250, 140)">
                    <rect x="-110" y="-40" width="220" height="65" rx="6" fill="rgba(0,0,0,0.9)" stroke="#f4a261" strokeWidth="1" />
                    <text x="0" y="-22" fill="#f4a261" textAnchor="middle" fontSize="10" fontWeight="bold">The Alignment Deficit</text>
                    <text x="0" y="-8" fill="white" textAnchor="middle" fontSize="9">Missing holistic research simultaneously</text>
                    <text x="0" y="3" fill="white" textAnchor="middle" fontSize="9">bridging Fairness, Explainability & LLMs.</text>
                    <text x="0" y="14" fill="rgba(255,255,255,0.6)" textAnchor="middle" fontSize="8" fontStyle="italic">Zero papers represent perfectly overlapping focus.</text>
                  </g>
                </g>

                {/* Edge Annotations */}
                <g transform="translate(250, 335)">
                  <rect x="-60" y="-15" width="160" height="30" rx="15" fill="rgba(163, 177, 138, 0.15)" stroke="var(--xai-color)" strokeWidth="1" />
                  <text x="20" y="4" fill="white" textAnchor="middle" fontSize="12" fontWeight="bold">Visibility (n=136)</text>
                </g>

                <g transform="translate(100, 160)">
                  <rect x="-80" y="-15" width="160" height="30" rx="15" fill="rgba(244, 162, 97, 0.15)" stroke="var(--fairness-color)" strokeWidth="1" />
                  <text x="0" y="4" fill="white" textAnchor="middle" fontSize="12" fontWeight="bold">Accountability (n=69)</text>
                </g>

                <g transform="translate(400, 160)">
                  <rect x="-80" y="-15" width="140" height="30" rx="15" fill="rgba(142, 202, 230, 0.15)" stroke="var(--llm-color)" strokeWidth="1" />
                  <text x="-10" y="4" fill="white" textAnchor="middle" fontSize="12" fontWeight="bold">Alignment (n=65)</text>
                </g>

                {/* Nodes */}
                {/* Top - Fairness */}
                <circle cx="250" cy="40" r="8" fill="#f4a261" filter="url(#glow)" />
                <text x="250" y="20" fill="white" textAnchor="middle" fontSize="16" fontWeight="bold" letterSpacing="1px">Fairness / Bias</text>

                {/* Bottom Left - Explainability */}
                <circle cx="100" cy="300" r="8" fill="#a3b18a" filter="url(#glow)" />
                <text x="50" y="325" fill="white" textAnchor="middle" fontSize="16" fontWeight="bold" letterSpacing="1px">Explainability</text>

                {/* Bottom Right - LLMs */}
                <circle cx="400" cy="300" r="8" fill="#8ecae6" filter="url(#glow)" />
                <text x="450" y="325" fill="white" textAnchor="middle" fontSize="16" fontWeight="bold" letterSpacing="1px">Large Language Models</text>
              </svg>
              <div style={{ textAlign: "center", marginTop: "1rem" }}>
                <span style={{ color: "white", fontStyle: "italic", fontSize: "0.9rem" }}>Empirical Tensions Driven by Volume</span>
              </div>
            </div>
          </div>

        </section>

        <section className="insight-grid" style={{ gridTemplateColumns: "1fr" }}>

          <article className="insight-card wide" style={{ borderLeft: "8px solid #a3b18a", padding: "2rem" }}>
            <div className="panel-head" style={{ paddingBottom: "1.5rem", borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
              <div>
                <p className="eyebrow" style={{ color: "#a3b18a", fontSize: "1rem" }}>EDGE 1 • EXPLAINABILITY ↔ LLMS (N=136)</p>
                <h2 style={{ fontSize: "2.2rem", margin: "0.5rem 0" }}>The "Visibility" Axis</h2>
                <p style={{ fontSize: "1.1rem", color: "var(--text-muted)", lineHeight: 1.6, maxWidth: "900px" }}>
                  <strong>The thickest edge of the triangle.</strong> Current research is aggressively prioritizing structural transparency, splitting between using XAI to dissect the LLM computationally, and deploying LLMs as colloquial explanation agents.
                </p>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem", marginTop: "2rem" }}>
              <div style={{ background: "rgba(163, 177, 138, 0.08)", padding: "2rem", borderRadius: "16px", border: "1px solid rgba(163, 177, 138, 0.2)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h3 style={{ color: "white", fontSize: "1.4rem" }}>Q5: Explainability → LLMs</h3>
                  <span style={{ background: "#a3b18a", color: "black", padding: "4px 12px", borderRadius: "100px", fontWeight: "bold" }}>84 papers</span>
                </div>
                <h4 style={{ color: "#a3b18a", marginTop: "1rem", marginBottom: "0.5rem", fontSize: "1.1rem" }}>Demystifying the Black Box</h4>
                <p style={{ color: "var(--text-muted)", fontSize: "1rem", lineHeight: 1.6 }}>
                  The most populated node in the review. Research concentrates heavily on post-hoc interpretation (mechanistic interpretability, attention map analysis) to uncover <em>how</em> foundational models generate specific outputs.
                  <br /><br /><strong>Implication:</strong> The field is in an exploratory "diagnostic" phase, prioritizing the architectural understanding of LLMs over alignment.
                </p>
              </div>

              <div style={{ background: "rgba(163, 177, 138, 0.08)", padding: "2rem", borderRadius: "16px", border: "1px solid rgba(163, 177, 138, 0.2)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h3 style={{ color: "white", fontSize: "1.4rem" }}>Q6: LLMs → Explainability</h3>
                  <span style={{ background: "#a3b18a", color: "black", padding: "4px 12px", borderRadius: "100px", fontWeight: "bold" }}>52 papers</span>
                </div>
                <h4 style={{ color: "#a3b18a", marginTop: "1rem", marginBottom: "0.5rem", fontSize: "1.1rem" }}>The Explanatory Agent</h4>
                <p style={{ color: "var(--text-muted)", fontSize: "1rem", lineHeight: 1.6 }}>
                  LLMs are increasingly treated not as models to be explained, but as <em>agents</em> that generate human-readable explanations for other opaque AI models (e.g., healthcare diagnostics or financial scoring).
                  <br /><br /><strong>Implication:</strong> While generative explanations are highly accessible, they risk "hallucinated interpretability" where the explanation does not accurately reflect the underlying logic.
                </p>
              </div>
            </div>
          </article>

          <article className="insight-card wide" style={{ borderLeft: "8px solid #f4a261", padding: "2rem" }}>
            <div className="panel-head" style={{ paddingBottom: "1.5rem", borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
              <div>
                <p className="eyebrow" style={{ color: "#f4a261", fontSize: "1rem" }}>EDGE 2 • FAIRNESS ↔ EXPLAINABILITY (N=69)</p>
                <h2 style={{ fontSize: "2.2rem", margin: "0.5rem 0" }}>The "Accountability" Axis</h2>
                <p style={{ fontSize: "1.1rem", color: "var(--text-muted)", lineHeight: 1.6, maxWidth: "900px" }}>
                  <strong>The balanced edge.</strong> This axis establishes that Fairness and Explainability are not parallel goals, but sequential ones. You cannot fix algorithmic bias until you can map it.
                </p>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem", marginTop: "2rem" }}>
              <div style={{ background: "rgba(244, 162, 97, 0.08)", padding: "2rem", borderRadius: "16px", border: "1px solid rgba(244, 162, 97, 0.2)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h3 style={{ color: "white", fontSize: "1.4rem" }}>Q2: Explainability → Fairness</h3>
                  <span style={{ background: "#f4a261", color: "black", padding: "4px 12px", borderRadius: "100px", fontWeight: "bold" }}>39 papers</span>
                </div>
                <h4 style={{ color: "#f4a261", marginTop: "1rem", marginBottom: "0.5rem", fontSize: "1.1rem" }}>Transparency as a Prerequisite</h4>
                <p style={{ color: "var(--text-muted)", fontSize: "1rem", lineHeight: 1.6 }}>
                  A strongly established paradigm where XAI frameworks (like SHAP or LIME) are explicitly utilized to expose the root causes of biased predictions. "You cannot fix what you cannot explain."
                  <br /><br /><strong>Implication:</strong> XAI tools are becoming mandatory compliance and auditing mechanisms for achieving measurable fairness.
                </p>
              </div>

              <div style={{ background: "rgba(244, 162, 97, 0.08)", padding: "2rem", borderRadius: "16px", border: "1px solid rgba(244, 162, 97, 0.2)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h3 style={{ color: "white", fontSize: "1.4rem" }}>Q1: Fairness → Explainability</h3>
                  <span style={{ background: "#f4a261", color: "black", padding: "4px 12px", borderRadius: "100px", fontWeight: "bold" }}>30 papers</span>
                </div>
                <h4 style={{ color: "#f4a261", marginTop: "1rem", marginBottom: "0.5rem", fontSize: "1.1rem" }}>The Bias of Explanations</h4>
                <p style={{ color: "var(--text-muted)", fontSize: "1rem", lineHeight: 1.6 }}>
                  A critical subfield actively investigating whether XAI methods are themselves equitable. Studies indicate that explanations may systematically fail or mislead minority demographic groups.
                  <br /><br /><strong>Implication:</strong> Explanations are not inherently neutral. XAI systems must be audited for structural equity to ensure they serve all users optimally.
                </p>
              </div>
            </div>
          </article>

          <article className="insight-card wide" style={{ borderLeft: "8px solid #8ecae6", padding: "2rem" }}>
            <div className="panel-head" style={{ paddingBottom: "1.5rem", borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
              <div>
                <p className="eyebrow" style={{ color: "#8ecae6", fontSize: "1rem" }}>EDGE 3 • FAIRNESS ↔ LLMS (N=65)</p>
                <h2 style={{ fontSize: "2.2rem", margin: "0.5rem 0" }}>The "Alignment" Axis</h2>
                <p style={{ fontSize: "1.1rem", color: "var(--text-muted)", lineHeight: 1.6, maxWidth: "900px" }}>
                  <strong>The alignment deficit.</strong> The field is highly efficient at identifying LLM harms dynamically, but lacks maturity in enforcing proactive fairness constraints organically within model generation.
                </p>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem", marginTop: "2rem" }}>
              <div style={{ background: "rgba(142, 202, 230, 0.08)", padding: "2rem", borderRadius: "16px", border: "1px solid rgba(142, 202, 230, 0.2)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h3 style={{ color: "white", fontSize: "1.4rem" }}>Q4: LLMs → Fairness</h3>
                  <span style={{ background: "#8ecae6", color: "black", padding: "4px 12px", borderRadius: "100px", fontWeight: "bold" }}>41 papers</span>
                </div>
                <h4 style={{ color: "#8ecae6", marginTop: "1rem", marginBottom: "0.5rem", fontSize: "1.1rem" }}>Diagnosing Amplified Harm</h4>
                <p style={{ color: "var(--text-muted)", fontSize: "1rem", lineHeight: 1.6 }}>
                  Research exposing how foundational models amplify structural biases, generating toxic or stereotyped content due to the unsupervised nature of massive web corpora.
                  <br /><br /><strong>Implication:</strong> Rapid deployment of unaligned LLMs poses immediate risks to representational equity. Post-deployment auditing dominates this sector.
                </p>
              </div>

              <div style={{ background: "rgba(142, 202, 230, 0.08)", padding: "2rem", borderRadius: "16px", border: "1px solid rgba(142, 202, 230, 0.2)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h3 style={{ color: "white", fontSize: "1.4rem" }}>Q3: Fairness → LLMs</h3>
                  <span style={{ background: "#8ecae6", color: "black", padding: "4px 12px", borderRadius: "100px", fontWeight: "bold" }}>24 papers</span>
                </div>
                <h4 style={{ color: "#8ecae6", marginTop: "1rem", marginBottom: "0.5rem", fontSize: "1.1rem" }}>The Proactive Struggle</h4>
                <p style={{ color: "var(--text-muted)", fontSize: "1rem", lineHeight: 1.6 }}>
                  The least populated node. Methodologies attempting to strictly enforce demographic parity and mathematical fairness constraints within open-ended generative contexts.
                  <br /><br /><strong>Implication:</strong> A critical gap remains regarding proactive debiasing. Enforcing constraints during generation is computationally intensive and mathematically complex.
                </p>
              </div>
            </div>
          </article>

        </section>

        {/* Final Executive Conclusion Block */}
        <section style={{
          marginTop: "4rem",
          padding: "4rem",
          background: "linear-gradient(135deg, rgba(244, 162, 97, 0.1) 0%, rgba(142, 202, 230, 0.1) 100%)",
          borderRadius: "32px",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          textAlign: "center",
          position: "relative",
          overflow: "hidden",
          marginBottom: "4rem"
        }}>
          <div style={{ position: "relative", zIndex: 2 }}>
            <h2 style={{ fontSize: "2.8rem", color: "white", marginBottom: "1.5rem", letterSpacing: "-0.03em" }}>Executive Synthesis</h2>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "2rem", textAlign: "left", marginTop: "3rem" }}>
              <div>
                <h3 style={{ color: "#f4a261", marginBottom: "1rem" }}>1. The Visibility Paradox</h3>
                <p style={{ color: "var(--text-muted)", lineHeight: 1.6 }}>
                  Research is heavily skewed towards <strong>Explainability ↔ LLMs</strong>. While we are mastering how to look "inside" the box, we are failing to ensure the box is built on a fair foundation. Transparency is being prioritized over equity.
                </p>
              </div>
              <div>
                <h3 style={{ color: "#a3b18a", marginBottom: "1rem" }}>2. Structural Decoupling</h3>
                <p style={{ color: "var(--text-muted)", lineHeight: 1.6 }}>
                  Fairness research remains largely isolated from the generative engine. Most studies treat bias as a post-hoc filtering problem rather than an architectural alignment challenge, creating a significant technical debt in AI safety.
                </p>
              </div>
              <div>
                <h3 style={{ color: "#8ecae6", marginBottom: "1rem" }}>3. The Final Verdict</h3>
                <p style={{ color: "var(--text-muted)", lineHeight: 1.6 }}>
                  The <strong>"Void"</strong> at the center of our triad is the blueprint for future work. A truly trustworthy LLM requires a <em>simultaneous</em> integration of ethical constraints (Fairness) and functional transparency (XAI).
                </p>
              </div>
            </div>

            <div style={{ marginTop: "4rem", padding: "2rem", background: "rgba(255,255,255,0.03)", borderRadius: "16px" }}>
              <p style={{ fontSize: "1.2rem", color: "white", fontStyle: "italic", fontWeight: "300" }}>
                "The current landscape reveals an AI that is becoming more visible to the human eye, but remains structurally unaligned with human representational fairness."
              </p>
              <div style={{ marginTop: "1rem", height: "1px", width: "100px", background: "#f4a261", margin: "0 auto" }} />
              <p style={{ marginTop: "1rem", color: "#f4a261", fontWeight: "bold", textTransform: "uppercase", letterSpacing: "2px", fontSize: "0.9rem" }}>Conclusion of Systematic Review</p>
            </div>
          </div>
        </section>
      </main>
      <footer className="app-footer">Designed for direct inclusion in systematic review conclusion and limitations.</footer>
    </div >
  );
};

// Helper function to normalize question_id to Q1-Q6 format
// Extracts Q1-Q6 from strings like "Q4|Fairness↔LLMs" or "Q1|F→E"
const normalizeQuestionId = (questionId: string): QuestionId | null => {
  const match = questionId.match(/^(Q[1-6])/);
  if (match && (match[1] === "Q1" || match[1] === "Q2" || match[1] === "Q3" || match[1] === "Q4" || match[1] === "Q5" || match[1] === "Q6")) {
    return match[1] as QuestionId;
  }
  return null;
};

const App: React.FC = () => {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [insights, setInsights] = useState<any>(null);
  const [activeQuestions, setActiveQuestions] = useState<QuestionId[]>([]);
  const [yearFilter, setYearFilter] = useState<YearFilter>({ min: null, max: null });
  const [detailPaper, setDetailPaper] = useState<Paper | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch papers
    fetch("/fairlens_papers.json")
      .then((r) => r.json())
      .then((data: Paper[]) => {
        // Normalize question_id values
        const normalizedPapers: Paper[] = [];
        for (const paper of data) {
          const normalizedQid = normalizeQuestionId(paper.question_id);
          if (normalizedQid) {
            normalizedPapers.push({ ...paper, question_id: normalizedQid });
          }
        }

        // Deduplicate
        const seen = new Set<string>();
        const deduplicated: Paper[] = [];
        for (const paper of normalizedPapers) {
          const key = `${paper.title?.trim()}|${paper.question_id}`;
          if (!seen.has(key)) {
            seen.add(key);
            deduplicated.push(paper);
          }
        }

        setPapers(deduplicated);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error loading papers:", err);
        setLoading(false);
      });

    // Fetch dashboard insights
    fetch("/dashboard_insights.json")
      .then((r) => r.json())
      .then((data) => setInsights(data))
      .catch((err) => console.error("Error loading insights:", err));
  }, []);

  const years = useMemo(() => {
    const ys = papers.map((p) => p.year).filter((y): y is number => typeof y === "number");
    if (!ys.length) return { min: null, max: null };
    return { min: Math.min(...ys), max: Math.max(...ys) };
  }, [papers]);

  useEffect(() => {
    if (years.min !== null && years.max !== null && yearFilter.min === null && yearFilter.max === null) {
      setYearFilter({ min: years.min, max: years.max });
    }
  }, [years, yearFilter.min, yearFilter.max]);

  const toggleQuestion = (qid: QuestionId) => {
    setActiveQuestions((prev) => (prev.includes(qid) ? prev.filter((q) => q !== qid) : [...prev, qid]));
  };

  const filteredPapers = useMemo(() => {
    let subset = papers;

    if (activeQuestions.length > 0) {
      subset = subset.filter((p) => activeQuestions.includes(p.question_id as QuestionId));
    }
    if (yearFilter.min !== null) {
      subset = subset.filter((p) => p.year === null || p.year >= yearFilter.min!);
    }
    if (yearFilter.max !== null) {
      subset = subset.filter((p) => p.year === null || p.year <= yearFilter.max!);
    }

    return [...subset].sort((a, b) => (b.year ?? 0) - (a.year ?? 0));
  }, [papers, activeQuestions, yearFilter]);

  const totalsByQuestion = useMemo(() => {
    const base: Record<QuestionId, number> = { Q1: 0, Q2: 0, Q3: 0, Q4: 0, Q5: 0, Q6: 0 };
    papers.forEach((paper) => {
      // question_id is already normalized, so we can safely use it
      if (paper.question_id in base) {
        base[paper.question_id as QuestionId] += 1;
      }
    });
    return base;
  }, [papers]);

  const uniqueVenues = useMemo(() => {
    const venueSet = new Set(
      papers
        .map((paper) => paper.venue?.trim())
        .filter((venue): venue is string => Boolean(venue) && venue !== "nan")
    );
    return venueSet.size;
  }, [papers]);

  const uniquePapers = useMemo(() => {
    const titleSet = new Set(
      papers.map((paper) => paper.title?.trim()).filter((title): title is string => Boolean(title))
    );
    return titleSet.size;
  }, [papers]);

  const uniqueFilteredPapers = useMemo(() => {
    const titleSet = new Set(
      filteredPapers.map((paper) => paper.title?.trim()).filter((title): title is string => Boolean(title))
    );
    return titleSet.size;
  }, [filteredPapers]);

  const handleReset = () => {
    setActiveQuestions([]);
    if (years.min !== null && years.max !== null) {
      setYearFilter({ min: years.min, max: years.max });
    }
  };

  // coverageText removed (unused)
  const isYearDefault =
    years.min !== null && years.max !== null && yearFilter.min === years.min && yearFilter.max === years.max;
  const filtersActive = activeQuestions.length > 0 || !isYearDefault;

  let listTitle: string;
  if (activeQuestions.length === 0) {
    listTitle = "All directional papers";
  } else if (activeQuestions.length === 1) {
    listTitle = questionMeta[activeQuestions[0]].label;
  } else {
    const ids = activeQuestions.join(", ");
    listTitle = `Selected questions: ${ids}`;
  }

  return (
    <div className="app-shell">
      <nav className="primary-nav">
        <div className="brand">
          <span>FAIR–LENS</span>
        </div>
        <div className="nav-links">
          <NavLink to="/" end className={({ isActive }) => `nav-link${isActive ? " is-active" : ""}`}>
            Explorer
          </NavLink>
          <NavLink to="/insights" className={({ isActive }) => `nav-link${isActive ? " is-active" : ""}`}>
            Insights
          </NavLink>
          <NavLink to="/framework" className={({ isActive }) => `nav-link${isActive ? " is-active" : ""}`}>
            Framework
          </NavLink>
        </div>
        <div className="nav-meta">
          <span>{papers.length} rows</span>
          <span>{uniquePapers} papers</span>
          <span>{uniqueVenues} venues</span>
        </div>
      </nav>

      <Routes>
        <Route
          path="/"
          element={
            <ExplorerView
              filteredPapers={filteredPapers}
              questionMeta={questionMeta}
              questionOrder={questionOrder}
              activeQuestions={activeQuestions}
              toggleQuestion={toggleQuestion}
              clearQuestions={() => setActiveQuestions([])}
              showPaperDetails={(paper) => setDetailPaper(paper)}
              yearFilter={yearFilter}
              setYearFilter={setYearFilter}
              years={years}
              totalsByQuestion={totalsByQuestion}
              uniqueVenues={uniqueVenues}
              uniquePapers={uniquePapers}
              uniqueFilteredPapers={uniqueFilteredPapers}
              handleReset={handleReset}
              handleSelectAllQuestions={() => setActiveQuestions(questionOrder)}
              filtersActive={filtersActive}
              listTitle={listTitle}
            />
          }
        />
        <Route path="/insights" element={<InsightsView papers={papers} questionMeta={questionMeta} insights={insights} />} />
        <Route path="/framework" element={<FrameworkView />} />
      </Routes>
      {detailPaper && <PaperDetailModal paper={detailPaper} onClose={() => setDetailPaper(null)} />}
    </div>
  );
};

export default App;
