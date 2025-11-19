// src/App.tsx
import React, { useEffect, useMemo, useState } from "react";
import Triangle from "./components/Triangle";

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

const questionMeta: Record<
  QuestionId,
  { label: string; description: string }
> = {
  Q1: {
    label: "Q1: Fairness → Explainability",
    description:
      "Fairness/bias concerns motivate or shape explainability/XAI methods.",
  },
  Q2: {
    label: "Q2: Explainability → Fairness",
    description:
      "XAI methods are used to detect, measure, or mitigate bias/unfairness.",
  },
  Q3: {
    label: "Q3: Fairness → LLMs",
    description:
      "Fairness/bias is defined or operationalized specifically for LLMs.",
  },
  Q4: {
    label: "Q4: LLMs → Fairness",
    description:
      "LLMs affect, amplify, or address fairness/discrimination.",
  },
  Q5: {
    label: "Q5: Explainability → LLMs",
    description: "XAI methods are applied to analyze or interpret LLM behaviour.",
  },
  Q6: {
    label: "Q6: LLMs → Explainability",
    description:
      "LLMs advance or challenge explainability (e.g., self-explanations, CoT).",
  },
};

const App: React.FC = () => {
  const [papers, setPapers] = useState<Paper[]>([]);
  // ⬇⬇⬇ MULTI-SELECTION STATE
  const [activeQuestions, setActiveQuestions] = useState<QuestionId[]>([]);
  const [yearFilter, setYearFilter] = useState<{
    min: number | null;
    max: number | null;
  }>({
    min: null,
    max: null,
  });

  useEffect(() => {
    fetch("/fairlens_papers.json")
      .then((r) => r.json())
      .then((data) => setPapers(data))
      .catch((err) => console.error("Error loading data:", err));
  }, []);

  const years = useMemo(() => {
    const ys = papers
      .map((p) => p.year)
      .filter((y): y is number => typeof y === "number");
    if (!ys.length) return { min: null, max: null };
    return {
      min: Math.min(...ys),
      max: Math.max(...ys),
    };
  }, [papers]);

  // Initialize year filter once we know ranges
  useEffect(() => {
    if (
      years.min !== null &&
      years.max !== null &&
      yearFilter.min === null &&
      yearFilter.max === null
    ) {
      setYearFilter({ min: years.min, max: years.max });
    }
  }, [years, yearFilter.min, yearFilter.max]);

  // ⬇⬇⬇ helper to toggle one question on/off
  const toggleQuestion = (qid: QuestionId) => {
    setActiveQuestions((prev) =>
      prev.includes(qid) ? prev.filter((q) => q !== qid) : [...prev, qid]
    );
  };

  const filteredPapers = useMemo(() => {
    let subset = papers;

    // filter by one or more selected questions
    if (activeQuestions.length > 0) {
      subset = subset.filter((p) =>
        activeQuestions.includes(p.question_id as QuestionId)
      );
    }

    // filter by year range
    if (yearFilter.min !== null) {
      subset = subset.filter(
        (p) => p.year === null || p.year >= yearFilter.min!
      );
    }
    if (yearFilter.max !== null) {
      subset = subset.filter(
        (p) => p.year === null || p.year <= yearFilter.max!
      );
    }

    // Sort newest first
    subset = [...subset].sort((a, b) => (b.year ?? 0) - (a.year ?? 0));

    return subset;
  }, [papers, activeQuestions, yearFilter]);

  const handleReset = () => {
    setActiveQuestions([]);
    if (years.min !== null && years.max !== null) {
      setYearFilter({ min: years.min, max: years.max });
    }
  };

  // Title depending on how many filters are active
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
    <div className="app-root">
      <header className="app-header">
        <h1>FAIR–LENS</h1>
        <p className="subtitle">
          Interactive view of how included papers connect{" "}
          <strong>Fairness/Bias</strong>, <strong>Explainability</strong>, and{" "}
          <strong>LLMs</strong> via six directional questions (Q1–Q6).
        </p>
      </header>

      <main className="app-main">
        <section className="triangle-section">
          <Triangle
            activeQuestions={activeQuestions}
            onToggleQuestion={toggleQuestion}
          />
          <div className="legend-card">
            <h2>Directional questions (Q1–Q6)</h2>
            <ul>
              {(Object.keys(questionMeta) as QuestionId[]).map((qid) => (
                <li
                  key={qid}
                  className={
                    "legend-item" +
                    (activeQuestions.includes(qid)
                      ? " legend-item-active"
                      : "")
                  }
                  onClick={() => toggleQuestion(qid)}
                >
                  <span className="legend-qid">{qid}</span>
                  <span className="legend-text">
                    <strong>{questionMeta[qid].label}</strong>
                    <br />
                    <span className="legend-desc">
                      {questionMeta[qid].description}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
            <button className="btn-reset" onClick={handleReset}>
              Reset filters
            </button>
          </div>
        </section>

        <section className="list-section">
          <div className="list-header">
            <h2>{listTitle}</h2>
            <p className="count-text">
              Showing <strong>{filteredPapers.length}</strong> papers. Duplicates
              arise when a paper belongs to more than one directional question.
            </p>

            {years.min !== null && years.max !== null && (
              <div className="year-filter">
                <label>
                  From{" "}
                  <input
                    type="number"
                    value={yearFilter.min ?? ""}
                    min={years.min}
                    max={years.max}
                    onChange={(e) =>
                      setYearFilter((prev) => ({
                        ...prev,
                        min: e.target.value
                          ? parseInt(e.target.value, 10)
                          : years.min,
                      }))
                    }
                  />
                </label>
                <label>
                  to{" "}
                  <input
                    type="number"
                    value={yearFilter.max ?? ""}
                    min={years.min}
                    max={years.max}
                    onChange={(e) =>
                      setYearFilter((prev) => ({
                        ...prev,
                        max: e.target.value
                          ? parseInt(e.target.value, 10)
                          : years.max,
                      }))
                    }
                  />
                </label>
              </div>
            )}
          </div>

          <ul className="paper-list">
            {filteredPapers.map((p, idx) => (
              <li key={idx} className="paper-item">
                <div className="paper-main">
                  <h3 className="paper-title">{p.title}</h3>
                  <div className="paper-meta">
                    {p.year && <span>{p.year}</span>}
                    {p.venue && <span>{p.venue}</span>}
                    {p.url && (
                      <a href={p.url} target="_blank" rel="noreferrer">
                        Open
                      </a>
                    )}
                  </div>
                </div>
                {p.directional_claim && (
                  <p className="paper-claim">{p.directional_claim}</p>
                )}
                <div className="paper-tags">
                  {p.mentions_fairness && (
                    <span className="tag tag-fairness">Fairness/Bias</span>
                  )}
                  {p.mentions_xai && (
                    <span className="tag tag-xai">Explainability</span>
                  )}
                  {p.mentions_llm && (
                    <span className="tag tag-llm">LLMs</span>
                  )}
                  <span className="tag tag-qid">{p.question_id}</span>
                </div>
              </li>
            ))}
          </ul>
        </section>
      </main>

      <footer className="app-footer">
        FAIR–LENS visualization prototype · Built from the systematic review
      </footer>
    </div>
  );
};

export default App;
