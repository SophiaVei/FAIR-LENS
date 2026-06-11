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
  Line,
  LineChart as ReLineChart,
  Pie,
  PieChart as RePieChart,
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
  ZAxis,
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
    label: "RP1: Fairness → Explainability",
    description: "Fairness/bias concerns motivate or shape explainability/XAI methods.",
  },
  Q2: {
    label: "RP2: Explainability → Fairness",
    description: "XAI methods are used to detect, measure, or mitigate bias/unfairness.",
  },
  Q3: {
    label: "RP3: Fairness → LLMs",
    description: "Fairness/bias is defined or operationalized specifically for LLMs.",
  },
  Q4: {
    label: "RP4: LLMs → Fairness",
    description: "LLMs affect, amplify, or address fairness/discrimination.",
  },
  Q5: {
    label: "RP5: Explainability → LLMs",
    description: "XAI methods are applied to analyze or interpret LLM behaviour.",
  },
  Q6: {
    label: "RP6: LLMs → Explainability",
    description: "LLMs advance or challenge explainability (e.g., self-explanations, CoT).",
  },
};

const questionOrder = Object.keys(questionMeta) as QuestionId[];
const displayQuestionId = (qid: string) => qid.replace(/^Q(?=[1-6]$)/, "RP");
const displayQuestionIds = (qids: string[]) => qids.map(displayQuestionId).join(", ");

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

interface InsightsData {
  venue_distribution?: Array<{ name: string; value: number }>;
  focus_evolution?: Array<any>;
  research_clusters?: Array<any>;
  intersection_dist?: Array<any>;
  discipline_split?: Array<any>;
  global_trends?: Record<string, any>;
  question_topics?: Record<string, Record<string, Array<{ name: string; value: number }>>>;
  model_evolution?: Array<any>;
}

type InsightsProps = {
  papers: Paper[];
  questionMeta: typeof questionMeta;
  insights: InsightsData | null;
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
          <span>Research pathway · {displayQuestionId(String(paper.question_id))}</span>
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
            <strong>LLMs</strong> via six directional research pathways (RP1-RP6).
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
            <span className="stat-meta">Distinct papers assigned to RP1-RP6</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Visible rows</span>
            <strong className="stat-value">{filteredPapers.length}</strong>
            <span className="stat-meta">
              {activeQuestions.length
                ? `${activeQuestions.length} focus areas`
                : "All research pathways. Relevant papers across all pathways are shown when no focus area is selected."}
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
                <p className="eyebrow">Research pathways</p>
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
                      <span className="chip-id">{displayQuestionId(qid)}</span>
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
                {displayQuestionId(qid)}
              </span>
            ))}
          </div>

          <p className="count-text">
            Showing <strong>{filteredPapers.length}</strong> papers. Duplicates arise when a paper belongs to more than one directional
            research pathway.
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
                  <span className="tag tag-qid">{displayQuestionId(String(p.question_id))}</span>
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

  // Research pathway trends over time
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

  const synergyRadarData = useMemo(() => {
    return questionOrder.map((qid) => {
      const count = papers.filter((p) => (p.question_id as QuestionId) === qid).length;
      return {
        subject: displayQuestionId(qid),
        fullName: questionMeta[qid].label.split(":")[1].trim(),
        value: count,
      };
    });
  }, [papers, questionMeta, questionOrder]);

  const thematicRadarData = useMemo(() => {
    return questionOrder.map((qid) => {
      const qPapers = papers.filter((p) => p.question_id === qid);
      const total = qPapers.length || 1;
      return {
        subject: displayQuestionId(qid),
        Fairness: (qPapers.filter(p => p.mentions_fairness).length / total) * 100,
        XAI: (qPapers.filter(p => p.mentions_xai).length / total) * 100,
        LLMs: (qPapers.filter(p => p.mentions_llm).length / total) * 100,
      };
    });
  }, [papers, questionOrder]);

  const maturityData = useMemo(() => {
    return questionOrder.map((qid) => {
      const qPapers = papers.filter((p) => p.question_id === qid);
      const total = qPapers.length || 1;
      const withUrl = qPapers.filter(p => p.url && p.url !== "nan").length;
      const multiTheme = qPapers.filter(p => 
        (p.mentions_fairness?1:0) + (p.mentions_xai?1:0) + (p.mentions_llm?1:0) >= 2
      ).length;
      
      return {
        name: displayQuestionId(qid),
        fullName: questionMeta[qid].label.split(":")[1].trim(),
        accessibility: (withUrl / total) * 100,
        depth: (multiTheme / total) * 100,
        count: total,
      };
    });
  }, [papers, questionMeta, questionOrder]);

  const methodologyData = useMemo(() => {
    const questionTopics = insights?.question_topics;
    if (!questionTopics) return [];
    
    const categories = ["framework", "dataset", "experiment", "mitigation", "audit", "benchmark", "survey"];
    
    return questionOrder.map((qid) => {
      const topics = questionTopics[qid]?.["Paper Type"] || [];
      const row: any = { name: qid };
      categories.forEach(cat => {
        const found = topics.find((t: any) => t.name === cat);
        row[cat] = found ? found.value : 0;
      });
      return row;
    });
  }, [insights, questionOrder]);

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

  const maturityTrends = useMemo(() => {
    const trends: Record<number, { total: number; acc: number; depth: number }> = {};
    
    papers.forEach((p) => {
      if (!p.year) return;
      if (!trends[p.year]) trends[p.year] = { total: 0, acc: 0, depth: 0 };
      
      trends[p.year].total += 1;
      if (p.url && p.url !== "nan") trends[p.year].acc += 1;
      if ((p.mentions_fairness?1:0) + (p.mentions_xai?1:0) + (p.mentions_llm?1:0) >= 2) {
        trends[p.year].depth += 1;
      }
    });

    return Object.entries(trends)
      .map(([year, stats]) => ({
        year: Number(year),
        accessibility: (stats.acc / stats.total) * 100,
        depth: (stats.depth / stats.total) * 100,
      }))
      .sort((a, b) => a.year - b.year);
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
    <div className="insights-tab-view">
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
                <p className="eyebrow">Research pathways</p>
                <h3>Directional balance</h3>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>Distribution of papers across the six research pathways</p>
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

          <article className="insight-card" id="chart-synergy-radar">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Structural Analysis</p>
                <h3>Research Synergy Profile</h3>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>Spatial distribution of papers across the 6-pathway framework</p>
              </div>
              <button
                className="ghost-button hide-on-export"
                onClick={() => downloadChart("chart-synergy-radar", "synergy_profile.png")}
                title="Download Plot"
                style={{ padding: "0.4rem", borderRadius: "50%", alignSelf: "flex-start" }}
              >
                <Download size={18} />
              </button>
            </div>
            <div className="chart-shell" style={{ height: "300px" }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="80%" data={synergyRadarData}>
                  <PolarGrid stroke="#334155" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: "#94a3b8", fontSize: 12, fontWeight: 600 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 'auto']} tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} />
                  <Radar name="Count" dataKey="value" stroke="#6366f1" fill="#6366f1" fillOpacity={0.5} />
                  <RechartsTooltip 
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload;
                        return (
                          <div className="chart-tooltip">
                            <p className="chart-tooltip-label">{data.subject}</p>
                            <span>{data.fullName}</span>
                            <br />
                            <span>Count: <strong>{data.value}</strong></span>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            <p className="insight-text" style={{ fontSize: "0.85rem", fontStyle: "italic" }}>
              Visualizes the field's gravitational pull—showing a strong structural skew toward <strong>Visibility</strong> (RP5/RP6) over <strong>Alignment</strong> (RP3/RP4).
            </p>
          </article>

          <article className="insight-card" id="chart-thematic-radar">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Thematic Purity</p>
                <h3>Thematic Distribution</h3>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>Percentage of papers mentioning each core theme by research pathway</p>
              </div>
              <button
                className="ghost-button hide-on-export"
                onClick={() => downloadChart("chart-thematic-radar", "thematic_profile.png")}
                title="Download Plot"
                style={{ padding: "0.4rem", borderRadius: "50%", alignSelf: "flex-start" }}
              >
                <Download size={18} />
              </button>
            </div>
            <div className="chart-shell" style={{ height: "300px" }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="80%" data={thematicRadarData}>
                  <PolarGrid stroke="#334155" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: "#94a3b8", fontSize: 12, fontWeight: 600 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} />
                  <Radar name="Fairness" dataKey="Fairness" stroke="#f4a261" fill="#f4a261" fillOpacity={0.3} />
                  <Radar name="XAI" dataKey="XAI" stroke="#a3b18a" fill="#a3b18a" fillOpacity={0.3} />
                  <Radar name="LLMs" dataKey="LLMs" stroke="#8ecae6" fill="#8ecae6" fillOpacity={0.3} />
                  <Legend iconType="circle" wrapperStyle={{ paddingTop: "10px" }} />
                  <RechartsTooltip 
                    formatter={(value: number) => [`${value.toFixed(1)}%`]}
                    contentStyle={{ backgroundColor: "#0f172a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            <p className="insight-text" style={{ fontSize: "0.85rem", fontStyle: "italic" }}>
              High-fidelity mapping: RP3/RP4 are <strong>Fairness-pure</strong>, while RP5/RP6 are <strong>XAI-dominated</strong> with minimal fairness intersection.
            </p>
          </article>

          <article className="insight-card wide" id="chart-maturity">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Meta-Analysis</p>
                <h3>Research Maturity Matrix</h3>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>Accessibility (Links) vs. Interdisciplinary Depth (Multi-theme mentions)</p>
              </div>
              <button
                className="ghost-button hide-on-export"
                onClick={() => downloadChart("chart-maturity", "maturity_matrix.png")}
                title="Download Plot"
                style={{ padding: "0.4rem", borderRadius: "50%", alignSelf: "flex-start" }}
              >
                <Download size={18} />
              </button>
            </div>
            <div className="chart-shell" style={{ height: "400px" }}>
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 20, right: 30, bottom: 40, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
                  <XAxis 
                    type="number" 
                    dataKey="accessibility" 
                    name="Accessibility" 
                    unit="%" 
                    label={{ value: 'Accessibility (% with links)', position: 'insideBottom', offset: -25, fill: '#94a3b8', fontSize: 12 }}
                    stroke="#64748b"
                    domain={[0, 100]}
                  />
                  <YAxis 
                    type="number" 
                    dataKey="depth" 
                    name="Depth" 
                    unit="%" 
                    label={{ value: 'Thematic Depth (% Multi-theme)', angle: -90, position: 'insideLeft', fill: '#94a3b8', fontSize: 12 }}
                    stroke="#64748b"
                    domain={[0, 100]}
                  />
                  <ZAxis type="number" dataKey="count" range={[100, 1000]} name="Volume" />
                  <RechartsTooltip 
                    cursor={{ strokeDasharray: '3 3' }}
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload;
                        return (
                          <div className="chart-tooltip" style={{ backgroundColor: "#0f172a", padding: "1rem", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.1)" }}>
                            <p style={{ margin: "0 0 0.5rem", fontWeight: "bold", color: "var(--brand)" }}>{data.name}: {data.fullName}</p>
                            <div style={{ fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                              <p>Papers: <strong>{data.count}</strong></p>
                              <p>Accessibility: <strong>{data.accessibility.toFixed(1)}%</strong></p>
                              <p>Thematic Depth: <strong>{data.depth.toFixed(1)}%</strong></p>
                            </div>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Scatter name="Research pathways" data={maturityData} fill="#6366f1">
                    {maturityData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={["#f4a261", "#f9844a", "#f9c74f", "#90be6d", "#43aa8b", "#577590"][index % 6]} />
                    ))}
                  </Scatter>
                </ScatterChart>
              </ResponsiveContainer>
            </div>
            <div style={{ display: "flex", gap: "1rem", justifyContent: "center", marginTop: "1rem" }}>
               {questionOrder.map((qid, idx) => (
                 <div key={qid} style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.75rem", color: "var(--text-muted)" }}>
                   <div style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: ["#f4a261", "#f9844a", "#f9c74f", "#90be6d", "#43aa8b", "#577590"][idx] }} />
                   <span>{displayQuestionId(qid)}</span>
                 </div>
               ))}
            </div>
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

          <article className="insight-card wide" id="chart-methodology">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Methodology</p>
                <h3>Research Approach Distribution</h3>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>Comparing the nature of contributions (Frameworks, Experiments, Audits, etc.) across research pathways</p>
              </div>
              <button
                className="ghost-button hide-on-export"
                onClick={() => downloadChart("chart-methodology", "methodology_distribution.png")}
                title="Download Plot"
                style={{ padding: "0.4rem", borderRadius: "50%", alignSelf: "flex-start" }}
              >
                <Download size={18} />
              </button>
            </div>
            <div className="chart-shell" style={{ height: "350px" }}>
              <ResponsiveContainer width="100%" height="100%">
                <ReBarChart data={methodologyData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.1} vertical={false} />
                  <XAxis dataKey="name" stroke="#64748b" />
                  <YAxis stroke="#64748b" />
                  <RechartsTooltip 
                    contentStyle={{ backgroundColor: "#0f172a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }}
                    itemStyle={{ fontSize: "0.8rem", textTransform: "capitalize" }}
                  />
                  <Legend iconType="circle" wrapperStyle={{ paddingTop: "10px", fontSize: "0.8rem", textTransform: "capitalize" }} />
                  <Bar dataKey="framework" name="Framework" stackId="a" fill="#f4a261" />
                  <Bar dataKey="dataset" name="Dataset" stackId="a" fill="#219ebc" />
                  <Bar dataKey="experiment" name="Experiment" stackId="a" fill="#8ecae6" />
                  <Bar dataKey="mitigation" name="Mitigation" stackId="a" fill="#ffb703" />
                  <Bar dataKey="audit" name="Audit" stackId="a" fill="#577590" />
                  <Bar dataKey="benchmark" name="Benchmark" stackId="a" fill="#43aa8b" />
                  <Bar dataKey="survey" name="Survey" stackId="a" fill="#90be6d" />
                </ReBarChart>
              </ResponsiveContainer>
            </div>
            <p className="insight-text" style={{ fontSize: "0.85rem", fontStyle: "italic", marginTop: "1rem" }}>
              Reveals that <strong>Visibility</strong> (RP5/RP6) is dominated by experiments and audits, while <strong>Accountability</strong> (RP1) sees a higher proportion of new frameworks and datasets.
            </p>
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
                    {Object.keys(insights?.global_trends || {}).map(cat => <option key={cat} value={cat}>{cat}</option>)}
                 </select>
                 <select 
                    value={activeTaxonomyQid} 
                    onChange={(e) => setActiveTaxonomyQid(e.target.value as QuestionId)}
                    className="select-input"
                 >
                    {Object.keys(questionMeta).map(qid => <option key={qid} value={qid}>{displayQuestionId(qid)}</option>)}
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
                  data={insights?.question_topics?.[activeTaxonomyQid]?.[taxonomyCategory] || []}
                  margin={{ top: 10, right: 30, left: 40, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" opacity={0.1} horizontal={false} />
                  <XAxis type="number" hide />
                  <YAxis dataKey="name" type="category" width={120} stroke="rgba(255,255,255,0.8)" fontSize={12} />
                  <RechartsTooltip content={<ChartTooltip />} />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                    {(insights?.question_topics?.[activeTaxonomyQid]?.[taxonomyCategory] || []).map((_, index) => {
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
                <h2>Research pathway trends over time</h2>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>How focus on each research pathway has changed year by year</p>
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
                  <Area type="monotone" dataKey="Q1" name="RP1" stroke="#f4a261" strokeWidth={3} fill="url(#q1Gradient)" />
                  <Area type="monotone" dataKey="Q2" name="RP2" stroke="#f9844a" strokeWidth={3} fill="url(#q2Gradient)" />
                  <Area type="monotone" dataKey="Q3" name="RP3" stroke="#f9c74f" strokeWidth={3} fill="url(#q3Gradient)" />
                  <Area type="monotone" dataKey="Q4" name="RP4" stroke="#90be6d" strokeWidth={3} fill="url(#q4Gradient)" />
                  <Area type="monotone" dataKey="Q5" name="RP5" stroke="#43aa8b" strokeWidth={3} fill="url(#q5Gradient)" />
                  <Area type="monotone" dataKey="Q6" name="RP6" stroke="#577590" strokeWidth={3} fill="url(#q6Gradient)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="insight-card wide" id="chart-maturity-trends">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Temporal Meta-Analysis</p>
                <h3>Field Maturity Trends</h3>
                <p style={{ margin: "0.5rem 0 0", fontSize: "0.9rem", color: "var(--text-muted)" }}>Evolution of Accessibility and Interdisciplinary Depth over time</p>
              </div>
              <button
                className="ghost-button hide-on-export"
                onClick={() => downloadChart("chart-maturity-trends", "maturity_trends.png")}
                title="Download Plot"
                style={{ padding: "0.4rem", borderRadius: "50%", alignSelf: "flex-start" }}
              >
                <Download size={18} />
              </button>
            </div>
            <div className="chart-shell" style={{ height: "320px" }}>
              <ResponsiveContainer width="100%" height="100%">
                <ReLineChart data={maturityTrends} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                  <XAxis dataKey="year" stroke="#64748b" />
                  <YAxis stroke="#64748b" unit="%" domain={[0, 100]} />
                  <RechartsTooltip contentStyle={{ backgroundColor: "#0f172a", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }} />
                  <Legend iconType="circle" />
                  <Line type="monotone" dataKey="accessibility" name="Accessibility (% URLs)" stroke="#8ecae6" strokeWidth={3} dot={{ r: 6, fill: "#8ecae6" }} />
                  <Line type="monotone" dataKey="depth" name="Thematic Depth (% Multi-theme)" stroke="#f4a261" strokeWidth={3} dot={{ r: 6, fill: "#f4a261" }} />
                </ReLineChart>
              </ResponsiveContainer>
            </div>
            <p className="insight-text" style={{ fontSize: "0.85rem", fontStyle: "italic", marginTop: "1rem" }}>
              While <strong>Thematic Depth</strong> remains high, <strong>Accessibility</strong> shows a concerning decline in very recent publications, highlighting a potential "transparency lag" in the rapid LLM expansion.
            </p>
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
            <p className="hide-on-export" style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "1rem", textAlign: "center" }}>
              <strong>Note:</strong> Proactive design (RP1, RP3) consistently lags behind diagnostic auditing across all years.
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
                {wordFrequency.length > 0 ? (
                  wordFrequency.map((word, index) => {
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
                  })
                ) : (
                  <p style={{ color: "var(--text-muted)" }}>Analyzing vocabulary...</p>
                )}
              </div>
            </div>
          </article>
        </section>

      </main>

      <footer className="app-footer">Insights will auto-refresh as soon as new outputs feed the visualizer.</footer>
    </div>
  );
};

type SynthesisProps = {
  papers: Paper[];
  totalsByQuestion: Record<QuestionId, number>;
  uniquePapers: number;
};

const SynthesisView: React.FC<SynthesisProps> = ({ papers, totalsByQuestion, uniquePapers }) => {
  const fairXai = totalsByQuestion.Q1 + totalsByQuestion.Q2;
  const fairLlm = totalsByQuestion.Q3 + totalsByQuestion.Q4;
  const xaiLlm = totalsByQuestion.Q5 + totalsByQuestion.Q6;
  const totalAssignments = papers.length;
  const maxEdge = Math.max(fairXai, fairLlm, xaiLlm);


  return (
    <div className="synthesis-tab-view">
      <div className="aurora" aria-hidden="true" />
      <header className="insights-hero" style={{ paddingBottom: "1.5rem" }}>
        <div>
          <p className="eyebrow" style={{ color: "#f4a261" }}>Concluding Synthesis</p>
          <h1>FAIR–LENS Pipeline</h1>
          <p className="subtitle">
            From systematic search to directional evidence — a complete methodological overview and its central finding.
          </p>
        </div>
      </header>

      <main className="insights-content" style={{ marginTop: 0 }}>

        {/* ── Pipeline Steps ── */}
        <section className="synth-pipeline" id="synth-pipeline">
          {[
            { n: 1, title: "Search", desc: "Lens search & exports" },
            { n: 2, title: "Screening", desc: "deduplication, English, peer-reviewed" },
            { n: 3, title: "Prefilter", desc: "exclude only clear E0–E2" },
            { n: 4, title: "Directional coding", desc: "RP1-RP6, multi-label" },
            { n: 5, title: "Synthesis", desc: "three evidence axes" },
          ].map((step, i) => (
            <React.Fragment key={step.n}>
              <div className="synth-step">
                <span className="synth-step-num">{step.n}</span>
                <div>
                  <strong>{step.title}</strong>
                  <span className="synth-step-desc">{step.desc}</span>
                </div>
              </div>
              {i < 4 && <span className="synth-arrow">→</span>}
            </React.Fragment>
          ))}
        </section>

        {/* ── Main 3-column body ── */}
        <section className="synth-body" id="synth-body">

          {/* LEFT — Review corpus */}
          <div className="synth-corpus">
            <h3 className="synth-heading">Review corpus</h3>
            <p className="synth-sub">PRISMA-informed, filtered, and coded</p>
            <div className="synth-big-nums">
              <div className="synth-big-num">
                <strong>{uniquePapers}</strong>
                <span>papers</span>
              </div>
              <div className="synth-big-num">
                <strong>{totalAssignments}</strong>
                <span>assignments</span>
              </div>
            </div>
            <div className="synth-badge">multi-label evidence</div>
            <p className="synth-fine">A paper may contribute to more than one research pathway.</p>
          </div>

          {/* CENTER — Triangle */}
          <div className="synth-triangle-wrap">
            <svg viewBox="0 0 400 370" className="synth-triangle-svg">
              <defs>
                <filter id="sg" filterUnits="userSpaceOnUse" x="-50" y="-50" width="500" height="470">
                  <feGaussianBlur stdDeviation="4" result="b" />
                  <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
              </defs>

              {/* Edges */}
              <line x1="200" y1="55" x2="60" y2="280" stroke="rgba(244,162,97,0.35)" strokeWidth="2" />
              <line x1="200" y1="55" x2="340" y2="280" stroke="rgba(142,202,230,0.35)" strokeWidth="2" />
              <line x1="60" y1="280" x2="340" y2="280" stroke="rgba(163,177,138,0.35)" strokeWidth="2" />

              {/* Q labels on edges */}
              <text x="118" y="145" fill="#f4a261" fontSize="13" fontWeight="bold">RP1</text>
              <text x="108" y="160" fill="rgba(255,255,255,0.45)" fontSize="10">F→E</text>
              <text x="138" y="215" fill="#a3b18a" fontSize="13" fontWeight="bold">RP2</text>
              <text x="128" y="230" fill="rgba(255,255,255,0.45)" fontSize="10">E→F</text>

              <text x="265" y="145" fill="#f4a261" fontSize="13" fontWeight="bold">RP3</text>
              <text x="265" y="160" fill="rgba(255,255,255,0.45)" fontSize="10">F→L</text>
              <text x="250" y="215" fill="#8ecae6" fontSize="13" fontWeight="bold">RP4</text>
              <text x="250" y="230" fill="rgba(255,255,255,0.45)" fontSize="10">L→F</text>

              <text x="148" y="302" fill="#a3b18a" fontSize="13" fontWeight="bold">RP5</text>
              <text x="143" y="317" fill="rgba(255,255,255,0.45)" fontSize="10">E→L</text>
              <text x="225" y="302" fill="#8ecae6" fontSize="13" fontWeight="bold">RP6</text>
              <text x="220" y="317" fill="rgba(255,255,255,0.45)" fontSize="10">L→E</text>

              {/* Center label */}
              <text x="200" y="195" fill="white" textAnchor="middle" fontSize="15" fontWeight="bold" letterSpacing="2">FAIR-LENS</text>
              <text x="200" y="213" fill="rgba(255,255,255,0.5)" textAnchor="middle" fontSize="10">directional</text>
              <text x="200" y="226" fill="rgba(255,255,255,0.5)" textAnchor="middle" fontSize="10">framework</text>

              {/* Nodes */}
              <circle cx="200" cy="55" r="9" fill="#f4a261" filter="url(#sg)" />
              <text x="200" y="35" fill="#f4a261" textAnchor="middle" fontSize="13" fontWeight="bold">Fairness / Bias</text>

              <circle cx="60" cy="280" r="9" fill="#a3b18a" filter="url(#sg)" />
              <text x="60" y="350" fill="#a3b18a" textAnchor="middle" fontSize="13" fontWeight="bold">Explainability</text>

              <circle cx="340" cy="280" r="9" fill="#8ecae6" filter="url(#sg)" />
              <text x="340" y="350" fill="#8ecae6" textAnchor="middle" fontSize="13" fontWeight="bold">LLMs</text>
            </svg>
          </div>

          {/* RIGHT — Evidence axes */}
          <div className="synth-axes">
            <h3 className="synth-heading">Evidence axes</h3>
            <p className="synth-sub">The corpus is unevenly distributed across the triangle.</p>

            <div className="synth-axis-list">
              <div className="synth-axis-item">
                <div className="synth-axis-count" style={{ background: "#f4a261", color: "#000" }}>{fairXai}</div>
                <div className="synth-axis-detail">
                  <strong style={{ color: "#f4a261" }}>Fairness ↔ Explainability</strong>
                  <span>accountability through explanation</span>
                </div>
              </div>
              <div className="synth-axis-item">
                <div className="synth-axis-count" style={{ background: "#1d4e89", color: "#fff" }}>{fairLlm}</div>
                <div className="synth-axis-detail">
                  <strong style={{ color: "#8ecae6" }}>Fairness ↔ LLMs</strong>
                  <span>smallest axis; proactive fairness remains limited</span>
                </div>
              </div>
              <div className="synth-axis-item">
                <div className="synth-axis-count" style={{ background: "#2a7f3f", color: "#fff" }}>{xaiLlm}</div>
                <div className="synth-axis-detail">
                  <strong style={{ color: "#a3b18a" }}>Explainability ↔ LLMs</strong>
                  <span>dominant visibility axis</span>
                </div>
              </div>
            </div>

            {/* Proportional bars */}
            <div className="synth-bars">
              <div className="synth-bar" style={{ width: `${(fairXai / maxEdge) * 100}%`, background: "#f4a261" }} />
              <div className="synth-bar" style={{ width: `${(fairLlm / maxEdge) * 100}%`, background: "linear-gradient(90deg, #1d4e89, #8ecae6)" }} />
              <div className="synth-bar" style={{ width: `${(xaiLlm / maxEdge) * 100}%`, background: "linear-gradient(90deg, #2a7f3f, #a3b18a)" }} />
            </div>
          </div>
        </section>

        {/* ── Bottom callout ── */}
        <section className="synth-callout">
          <div className="synth-callout-icon">🎯</div>
          <div className="synth-callout-text">
            <p className="synth-callout-main">
              Most work makes LLMs visible; much less connects that visibility to fairness-by-design.
            </p>
            <p className="synth-callout-sub">
              <em>This is the central gap highlighted by FAIR-LENS.</em>
            </p>
          </div>
        </section>

      </main>
      <footer className="app-footer">FAIR–LENS concluding synthesis · Systematic review pipeline overview.</footer>
    </div>
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
    listTitle = `Selected research pathways: ${displayQuestionIds(activeQuestions)}`;
  }

  if (loading) {
    return (
      <div className="app-shell" style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", background: "var(--bg-base)" }}>
        <RefreshCw className="spin" size={48} style={{ color: "var(--brand)" }} />
      </div>
    );
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
            Synthesis
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
        <Route path="/framework" element={<SynthesisView papers={papers} totalsByQuestion={totalsByQuestion} uniquePapers={uniquePapers} />} />
      </Routes>
      {detailPaper && <PaperDetailModal paper={detailPaper} onClose={() => setDetailPaper(null)} />}
    </div>
  );
};

export default App;
