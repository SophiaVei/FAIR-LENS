// src/components/Triangle.tsx
import React from "react";
import type { QuestionId } from "../App";

interface TriangleProps {
  activeQuestion: QuestionId | null;
  onSelectQuestion: (qid: QuestionId | null) => void;
}

type Wedge = {
  id: QuestionId;
  label: string;
  points: string; // SVG points
};

const wedges: Wedge[] = [
  // Triangle vertices:
  // A (Fairness) = (100, 20)
  // B (Explainability) = (20, 180)
  // C (LLMs) = (180, 180)
  // Center O ≈ (100, 120)
  // Midpoints: ABm(60,100), BCm(100,180), CAm(140,100)

  // Edge Fairness–Explainability (F↔E)
  {
    id: "Q1",
    label: "Fairness → Explainability",
    points: "100,120 100,20 60,100", // O, A, ABm
  },
  {
    id: "Q2",
    label: "Explainability → Fairness",
    points: "100,120 60,100 20,180", // O, ABm, B
  },

  // Edge Explainability–LLMs (E↔L) – we map these to Q3/Q4
  {
    id: "Q3",
    label: "Fairness → LLMs",
    points: "100,120 20,180 100,180", // O, B, BCm
  },
  {
    id: "Q4",
    label: "LLMs → Fairness",
    points: "100,120 100,180 180,180", // O, BCm, C
  },

  // Edge LLMs–Fairness (L↔F) – Q5/Q6
  {
    id: "Q5",
    label: "Explainability → LLMs",
    points: "100,120 180,180 140,100", // O, C, CAm
  },
  {
    id: "Q6",
    label: "LLMs → Explainability",
    points: "100,120 140,100 100,20", // O, CAm, A
  },
];

const Triangle: React.FC<TriangleProps> = ({ activeQuestion, onSelectQuestion }) => {
  const handleClick = (id: QuestionId) => {
    if (activeQuestion === id) {
      onSelectQuestion(null);
    } else {
      onSelectQuestion(id);
    }
  };

  return (
    <div className="triangle-wrapper">
      <svg
        viewBox="0 0 200 200"
        className="triangle-svg"
        aria-labelledby="triangleTitle triangleDesc"
      >
        <title id="triangleTitle">FAIR–LENS Triangle</title>
        <desc id="triangleDesc">
          Triangle with vertices Fairness/Bias, Explainability, and LLMs,
          subdivided into six directional regions (Q1–Q6).
        </desc>

        {/* Outer triangle border */}
        <polygon
          points="100,20 20,180 180,180"
          fill="none"
          stroke="#333"
          strokeWidth={1.5}
        />

        {/* Wedges */}
        {wedges.map((w) => {
          const isActive = activeQuestion === w.id;
          return (
            <polygon
              key={w.id}
              points={w.points}
              className={
                "triangle-wedge" + (isActive ? " triangle-wedge-active" : "")
              }
              onClick={() => handleClick(w.id)}
            >
              <title>{w.id}: {w.label}</title>
            </polygon>
          );
        })}

        {/* Center point (optional) */}
        <circle cx="100" cy="120" r="2" fill="#333" />

        {/* Vertex labels */}
        <text x="100" y="12" textAnchor="middle" className="vertex-label">
          Fairness / Bias
        </text>
        <text x="18" y="190" textAnchor="start" className="vertex-label">
          Explainability
        </text>
        <text x="182" y="190" textAnchor="end" className="vertex-label">
          LLMs
        </text>
      </svg>
      <p className="triangle-hint">
        Click on a region (Q1–Q6) to filter papers by direction along each edge
        of the triangle.
      </p>
    </div>
  );
};

export default Triangle;
