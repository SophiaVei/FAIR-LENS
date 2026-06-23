import React from "react";
import type { QuestionId } from "../App";

interface TriangleProps {
  activeQuestions: QuestionId[];
  onToggleQuestion: (qid: QuestionId) => void;
}

type PairGroup = "FE" | "FL" | "EL";

type Wedge = {
  id: QuestionId;
  points: string;
  pair: PairGroup;
};

const wedges: Wedge[] = [
  { id: "Q1", points: "100,120 100,20 60,100", pair: "FE" },
  { id: "Q2", points: "100,120 60,100 20,180", pair: "FE" },
  { id: "Q5", points: "100,120 20,180 100,180", pair: "EL" },
  { id: "Q6", points: "100,120 100,180 180,180", pair: "EL" },
  { id: "Q3", points: "100,120 180,180 140,100", pair: "FL" },
  { id: "Q4", points: "100,120 140,100 100,20", pair: "FL" },
];

type VertexKey = "fairness" | "explainability" | "llms";

const vertices: Record<VertexKey, { x: number; y: number }> = {
  fairness: { x: 100, y: 20 },
  explainability: { x: 20, y: 180 },
  llms: { x: 180, y: 180 },
};

const arrowMap: Record<QuestionId, { from: VertexKey; to: VertexKey }> = {
  Q1: { from: "fairness", to: "explainability" },
  Q2: { from: "explainability", to: "fairness" },
  Q3: { from: "fairness", to: "llms" },
  Q4: { from: "llms", to: "fairness" },
  Q5: { from: "explainability", to: "llms" },
  Q6: { from: "llms", to: "explainability" },
};

const pathwayMeta: Record<QuestionId, { name: string; code: string; direction: string }> = {
  Q1: { name: "Enable Credibility", code: "EN·CRD", direction: "Fairness -> Explainability" },
  Q2: { name: "Audit Fairness", code: "AU·FAIR", direction: "Explainability -> Fairness" },
  Q3: { name: "Enable Alignment", code: "EN·ALN", direction: "Fairness -> LLMs" },
  Q4: { name: "Audit Outcomes", code: "AU·OUT", direction: "LLMs -> Fairness" },
  Q5: { name: "Audit Behavior", code: "AU·BEH", direction: "Explainability -> LLMs" },
  Q6: { name: "Enable Explanations", code: "EN·EXP", direction: "LLMs -> Explainability" },
};

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

const pairFillColors: Record<PairGroup, string> = {
  FE: "rgba(157, 234, 201, 0.35)",
  EL: "rgba(255, 212, 176, 0.35)",
  FL: "rgba(255, 255, 185, 0.3)",
};

const ACTIVE_STROKE = "#f0ab3d";
const WEDGE_STROKE = "rgba(255, 255, 255, 0.15)";
const ARROW_STROKE = "#ffae42";
const LABEL_FILL = "rgba(255, 255, 255, 0.7)";
const displayQuestionId = (qid: string) => qid.replace(/^Q(?=[1-6]$)/, "RP");

const Triangle: React.FC<TriangleProps> = ({
  activeQuestions,
  onToggleQuestion,
}) => {
  const arrowLines = activeQuestions.map((qid) => {
    const mapping = arrowMap[qid];
    const start = vertices[mapping.from];
    const end = vertices[mapping.to];
    const { from, to } = shortenSegment(start, end, 10);

    return (
      <line
        key={qid}
        className="triangle-arrow"
        x1={from.x}
        y1={from.y}
        x2={to.x}
        y2={to.y}
        stroke={ARROW_STROKE}
        strokeWidth={2.2}
        markerEnd="url(#triangleArrowhead)"
      />
    );
  });

  return (
    <div className="triangle-wrapper">
      <svg
        viewBox="-15 -2 230 215"
        className="triangle-svg"
        aria-labelledby="triangleTitle triangleDesc"
      >
        <title id="triangleTitle">FAIR-LENS Triangle</title>
        <desc id="triangleDesc">
          Triangle with vertices Fairness/Bias, Explainability, and LLMs,
          subdivided into six research pathways (RP1-RP6). You can select one
          or more regions at the same time; arrows indicate the chosen
          pathways.
        </desc>

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

        <polygon
          points="100,20 20,180 180,180"
          fill="none"
          stroke="#4b5563"
          strokeWidth={1.2}
        />

        {wedges.map((w) => {
          const isActive = activeQuestions.includes(w.id);
          const pairClass = `triangle-pair-${w.pair.toLowerCase()}`;
          const meta = pathwayMeta[w.id];
          return (
            <polygon
              key={w.id}
              points={w.points}
              className={
                "triangle-wedge " +
                pairClass +
                (isActive ? " triangle-wedge-active" : "")
              }
              style={{ fill: pairFillColors[w.pair] }}
              stroke={isActive ? ACTIVE_STROKE : WEDGE_STROKE}
              strokeWidth={isActive ? 1.2 : 0.6}
              onClick={() => onToggleQuestion(w.id)}
            >
              <title>
                {displayQuestionId(w.id)} · {meta.code}: {meta.name} ({meta.direction})
              </title>
            </polygon>
          );
        })}

        {arrowLines}

        <text x="100" y="12" textAnchor="middle" className="vertex-label" fill={LABEL_FILL} style={{ fontSize: "0.72rem" }}>
          Fairness / Bias
        </text>
        <text x="35" y="198" textAnchor="middle" className="vertex-label" fill={LABEL_FILL} style={{ fontSize: "0.72rem" }}>
          Explainability
        </text>
        <text x="178" y="198" textAnchor="middle" className="vertex-label" fill={LABEL_FILL} style={{ fontSize: "0.72rem" }}>
          LLMs
        </text>
      </svg>

      <p className="triangle-hint hide-on-export">
        Click one or more regions (RP1-RP6) or legend items to highlight those
        research pathways and filter the paper list. Click again to unselect.
      </p>
    </div>
  );
};

export default Triangle;
