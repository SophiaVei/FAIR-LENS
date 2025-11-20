// src/components/Triangle.tsx
import React from "react";
import type { QuestionId } from "../App";

interface TriangleProps {
  activeQuestions: QuestionId[];
  onToggleQuestion: (qid: QuestionId) => void;
}

type PairGroup = "FE" | "FL" | "EL"; // Fairness–Explainability, Fairness–LLMs, Explainability–LLMs

type Wedge = {
  id: QuestionId;
  label: string;
  points: string; // SVG polygon points
  pair: PairGroup;
};

/**
 * Triangle vertices:
 *  A (Fairness)        = (100, 20)
 *  B (Explainability)  = (20, 180)
 *  C (LLMs)            = (180, 180)
 *  Center O            = (100, 120)
 *  midAB               = (60, 100)
 *  midBC               = (100, 180)
 *  midCA               = (140, 100)
 */
const wedges: Wedge[] = [
  //
  // FAIRNESS ↔ EXPLAINABILITY (LEFT EDGE)  → pair FE
  //
  {
    id: "Q1",
    label: "Fairness → Explainability",
    points: "100,120 100,20 60,100", // O, A, midAB
    pair: "FE",
  },
  {
    id: "Q2",
    label: "Explainability → Fairness",
    points: "100,120 60,100 20,180", // O, midAB, B
    pair: "FE",
  },

  //
  // EXPLAINABILITY ↔ LLMS (BOTTOM EDGE)  → pair EL
  //
  {
    id: "Q5",
    label: "Explainability → LLMs",
    points: "100,120 20,180 100,180", // O, B, midBC
    pair: "EL",
  },
  {
    id: "Q6",
    label: "LLMs → Explainability",
    points: "100,120 100,180 180,180", // O, midBC, C
    pair: "EL",
  },

  //
  // LLMS ↔ FAIRNESS (RIGHT EDGE)  → pair FL
  //
  {
    id: "Q3",
    label: "Fairness → LLMs",
    points: "100,120 180,180 140,100", // O, C, midCA
    pair: "FL",
  },
  {
    id: "Q4",
    label: "LLMs → Fairness",
    points: "100,120 140,100 100,20", // O, midCA, A
    pair: "FL",
  },
];

// Vertex identifiers for arrow mapping
type VertexKey = "fairness" | "explainability" | "llms";

const vertices: Record<VertexKey, { x: number; y: number }> = {
  fairness: { x: 100, y: 20 },
  explainability: { x: 20, y: 180 },
  llms: { x: 180, y: 180 },
};

// From–to mapping for each directional question
const arrowMap: Record<QuestionId, { from: VertexKey; to: VertexKey }> = {
  Q1: { from: "fairness", to: "explainability" },
  Q2: { from: "explainability", to: "fairness" },
  Q3: { from: "fairness", to: "llms" },
  Q4: { from: "llms", to: "fairness" },
  Q5: { from: "explainability", to: "llms" },
  Q6: { from: "llms", to: "explainability" },
};

// Utility: shorten a segment at both ends by `offset` so the arrow
// does not overlap the vertex points too strongly.
function shortenSegment(
  p1: { x: number; y: number },
  p2: { x: number; y: number },
  offset: number
) {
  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;
  const len = Math.sqrt(dx * dx + dy * dy);
  if (!len) {
    return { from: p1, to: p2 };
  }
  const ratio = offset / len;
  return {
    from: {
      x: p1.x + dx * ratio,
      y: p1.y + dy * ratio,
    },
    to: {
      x: p2.x - dx * ratio,
      y: p2.y - dy * ratio,
    },
  };
}

const Triangle: React.FC<TriangleProps> = ({
  activeQuestions,
  onToggleQuestion,
}) => {
  // Build an arrow line per active question
  const arrowLines = activeQuestions.map((qid) => {
    const mapping = arrowMap[qid];
    const start = vertices[mapping.from];
    const end = vertices[mapping.to];
    const { from, to } = shortenSegment(start, end, 10); // 10px inset from vertices

    return (
      <line
        key={qid}
        className="triangle-arrow"
        x1={from.x}
        y1={from.y}
        x2={to.x}
        y2={to.y}
        markerEnd="url(#triangleArrowhead)"
      />
    );
  });

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
          subdivided into six directional regions (Q1–Q6). You can select one
          or more regions at the same time; arrows indicate the chosen
          directions.
        </desc>

        {/* Arrowhead definition */}
        <defs>
          <marker
            id="triangleArrowhead"
            markerWidth="8"
            markerHeight="8"
            refX="6"
            refY="3"
            orient="auto"
            markerUnits="strokeWidth"
          >
            <path d="M0,0 L6,3 L0,6 z" fill="#b45326" />
          </marker>
        </defs>

        {/* Outer triangle border */}
        <polygon
          points="100,20 20,180 180,180"
          fill="none"
          stroke="#4b5563"
          strokeWidth={1.2}
        />

        {/* Wedges */}
        {wedges.map((w) => {
          const isActive = activeQuestions.includes(w.id);
          const pairClass = `triangle-pair-${w.pair.toLowerCase()}`; // FE/FL/EL → fe/fl/el
          return (
            <polygon
              key={w.id}
              points={w.points}
              className={
                "triangle-wedge " +
                pairClass +
                (isActive ? " triangle-wedge-active" : "")
              }
              onClick={() => onToggleQuestion(w.id)}
            >
              <title>
                {w.id}: {w.label}
              </title>
            </polygon>
          );
        })}

        {/* One arrow per active question */}
        {arrowLines}

        {/* Vertex labels */}
        <text x="100" y="12" textAnchor="middle" className="vertex-label">
          Fairness / Bias
        </text>
        <text x="35" y="198" textAnchor="middle" className="vertex-label">
          Explainability
        </text>
        <text x="178" y="198" textAnchor="middle" className="vertex-label">
          LLMs
        </text>
      </svg>

      <p className="triangle-hint">
        Click one or more regions (Q1–Q6) or legend items to highlight those
        directions and filter the paper list. Click again to unselect.
      </p>
    </div>
  );
};

export default Triangle;
