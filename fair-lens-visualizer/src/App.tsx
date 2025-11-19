// src/App.tsx
import React, { useEffect, useMemo, useState } from "react";
import { Routes, Route, NavLink } from "react-router-dom";
import {
  Activity,
  BarChart3,
  CalendarRange,
  ExternalLink,
  Filter,
  LineChart,
  PieChart as PieIcon,
  RefreshCw,
  Sparkles,
} from "lucide-react";
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
  papers: Paper[];
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
  highlightedPaper?: Paper;
  filtersActive: boolean;
  listTitle: string;
  coverageText: string;
};

type InsightsProps = {
  papers: Paper[];
  questionMeta: typeof questionMeta;
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
  papers,
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
  highlightedPaper,
  filtersActive,
  listTitle,
  coverageText,
}) => {
  return (
    <div className="app-root">
      <div className="aurora" aria-hidden="true" />
      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Systematic review companion</p>
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

        {highlightedPaper && (
          <div className="quote-card">
            <Sparkles size={18} />
            <div>
              <p>{highlightedPaper.directional_claim}</p>
              <span>{highlightedPaper.title}</span>
            </div>
          </div>
        )}
      </header>

      <main className="content-grid">
        <section className="left-column">
          <article className="panel triangle-panel">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Relationship map</p>
                <h2>Bias · Explainability · LLMs</h2>
              </div>
              <Sparkles size={18} />
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
        FAIR–LENS visualization prototype · Powered by lens.py, exclude_final.py, and questions.py
      </footer>
    </div>
  );
};

const InsightsView: React.FC<InsightsProps> = ({ papers, questionMeta }) => {
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
    const remainder = sorted.slice(venueLimit);
    if (remainder.length) {
      visible.push(["Others", remainder.reduce((acc, [, count]) => acc + count, 0)]);
    }
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

  const totalPapers = papers.length;
  const activeYears = yearSeries.length ? `${yearSeries[0].year}–${yearSeries[yearSeries.length - 1].year}` : "—";
  const avgPerYear = yearSeries.length ? Math.round((totalPapers / yearSeries.length) * 10) / 10 : 0;
  const withLinks = papers.filter((p) => p.url && p.url !== "nan").length;

  return (
    <div className="app-root insights-root">
      <div className="aurora" aria-hidden="true" />
      <header className="insights-hero">
        <div>
          <p className="eyebrow">Insight studio</p>
          <h1>FAIR–LENS Observatory</h1>
          <p className="subtitle">
            High-level telemetry for the review: yearly cadence, venue concentration, and how fairness, explainability, and LLMs co-occur.
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
          <article className="insight-card wide">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Cadence</p>
                <h2>Publication tempo</h2>
              </div>
            </div>
            <div className="chart-shell">
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={yearSeries}>
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

          <article className="insight-card">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Questions</p>
                <h3>Directional balance</h3>
              </div>
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
            <ul className="insight-list">
              {questionSeries.map((row) => (
                <li key={row.qid}>
                  <span>{row.name}</span>
                  <strong>{row.value}</strong>
                </li>
              ))}
            </ul>
          </article>

          <article className="insight-card tall">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Venues</p>
                <h3>Where conversations cluster</h3>
              </div>
              <div className="venue-control">
                <label>
                  Top venues ({venueLimit})
                  <input
                    type="range"
                    min={3}
                    max={10}
                    value={venueLimit}
                    onChange={(e) => setVenueLimit(parseInt(e.target.value, 10))}
                  />
                </label>
              </div>
            </div>
            <div className="chart-shell">
              <ResponsiveContainer width="100%" height={300}>
                <ReBarChart data={venueSeries} layout="vertical" margin={{ left: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                  <XAxis type="number" allowDecimals={false} stroke="rgba(255,255,255,0.5)" />
                  <YAxis dataKey="name" type="category" width={180} stroke="rgba(255,255,255,0.7)" />
                  <RechartsTooltip content={<ChartTooltip />} />
                  <Bar dataKey="value" fill="#f4a261" radius={[4, 4, 4, 4]} />
                </ReBarChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="insight-card">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Mentions</p>
                <h3>Topical coverage</h3>
              </div>
            </div>
            <div className="chart-shell">
              <ResponsiveContainer width="100%" height={260}>
                <RadialBarChart innerRadius="20%" outerRadius="90%" data={mentionSeries} startAngle={90} endAngle={-270}>
                  <RadialBar dataKey="value" />
                  <RechartsTooltip content={<ChartTooltip />} />
                  <Legend />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="insight-card">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Intersections</p>
                <h3>Co-mention intensity</h3>
              </div>
            </div>
            <div className="chart-shell">
              <ResponsiveContainer width="100%" height={260}>
                <RadialBarChart innerRadius="40%" outerRadius="100%" data={comboSeries} startAngle={90} endAngle={-270}>
                  <RadialBar dataKey="value" />
                  <RechartsTooltip content={<ChartTooltip />} />
                  <Legend />
                </RadialBarChart>
              </ResponsiveContainer>
            </div>
            <ul className="insight-list">
              {comboSeries.map((row) => (
                <li key={row.name}>
                  <span>{row.name}</span>
                  <strong>{row.value}</strong>
                </li>
              ))}
            </ul>
          </article>

          <article className="insight-card wide">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Evolution</p>
                <h2>Question trends over time</h2>
              </div>
            </div>
            <div className="chart-shell">
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={questionTrends}>
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
                  <Legend />
                  <Area type="monotone" dataKey="Q1" stackId="1" stroke="#f4a261" fill="url(#q1Gradient)" />
                  <Area type="monotone" dataKey="Q2" stackId="1" stroke="#f9844a" fill="url(#q2Gradient)" />
                  <Area type="monotone" dataKey="Q3" stackId="1" stroke="#f9c74f" fill="url(#q3Gradient)" />
                  <Area type="monotone" dataKey="Q4" stackId="1" stroke="#90be6d" fill="url(#q4Gradient)" />
                  <Area type="monotone" dataKey="Q5" stackId="1" stroke="#43aa8b" fill="url(#q5Gradient)" />
                  <Area type="monotone" dataKey="Q6" stackId="1" stroke="#577590" fill="url(#q6Gradient)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="insight-card">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Clusters</p>
                <h3>Research clusters</h3>
              </div>
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
                    {clusterSeries.map((entry, index) => (
                      <Cell
                        key={`cluster-${index}`}
                        fill={["#f4a261", "#90be6d", "#43aa8b"][index % 3]}
                      />
                    ))}
                  </Pie>
                </RePieChart>
              </ResponsiveContainer>
            </div>
            <ul className="insight-list">
              {clusterSeries.map((row) => (
                <li key={row.name}>
                  <span>{row.name}</span>
                  <strong>{row.value}</strong>
                </li>
              ))}
            </ul>
          </article>
        </section>
      </main>

      <footer className="app-footer">Insights auto-refresh as soon as new outputs from lens.py feed the visualizer.</footer>
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
  const [activeQuestions, setActiveQuestions] = useState<QuestionId[]>([]);
  const [yearFilter, setYearFilter] = useState<YearFilter>({ min: null, max: null });
  const [detailPaper, setDetailPaper] = useState<Paper | null>(null);

  useEffect(() => {
    fetch("/fairlens_papers.json")
      .then((r) => r.json())
      .then((data: Paper[]) => {
        // Normalize question_id values (extract Q1-Q6 from malformed IDs like "Q4|Fairness↔LLMs")
        // Keep ALL papers that have a valid Q1-Q6 question_id (even if malformed)
        const normalizedPapers: Paper[] = [];
        for (const paper of data) {
          const normalizedQid = normalizeQuestionId(paper.question_id);
          if (normalizedQid) {
            normalizedPapers.push({ ...paper, question_id: normalizedQid });
          }
        }
        
        // Deduplicate: keep only one entry per (title, question_id) combination
        // This prevents the same paper from appearing multiple times for the same question
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
      })
      .catch((err) => console.error("Error loading data:", err));
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

  const highlightedPaper = useMemo(
    () => filteredPapers.find((paper) => Boolean(paper.directional_claim)),
    [filteredPapers]
  );

  const coverageText = years.min !== null && years.max !== null ? `${years.min}–${years.max}` : "—";
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
          <span className="brand-tag">beta</span>
        </div>
        <div className="nav-links">
          <NavLink to="/" end className={({ isActive }) => `nav-link${isActive ? " is-active" : ""}`}>
            Explorer
          </NavLink>
          <NavLink to="/insights" className={({ isActive }) => `nav-link${isActive ? " is-active" : ""}`}>
            Insights
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
              papers={papers}
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
              highlightedPaper={highlightedPaper}
              filtersActive={filtersActive}
              listTitle={listTitle}
              coverageText={coverageText}
            />
          }
        />
        <Route path="/insights" element={<InsightsView papers={papers} questionMeta={questionMeta} />} />
      </Routes>
      {detailPaper && <PaperDetailModal paper={detailPaper} onClose={() => setDetailPaper(null)} />}
    </div>
  );
};

export default App;
