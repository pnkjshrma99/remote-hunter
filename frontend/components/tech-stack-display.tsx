"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

interface TechStackDisplayProps {
  techs: string[];
  maxVisible?: number;
}

export function TechStackDisplay({ techs, maxVisible = 8 }: TechStackDisplayProps) {
  const [expanded, setExpanded] = useState(false);
  const visibleTechs = expanded ? techs : techs.slice(0, maxVisible);
  const hiddenCount = techs.length - maxVisible;
  const hasMore = techs.length > maxVisible;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {visibleTechs.map((tech) => (
          <span
            key={tech}
            className="inline-flex items-center rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold text-indigo-700"
          >
            {tech}
          </span>
        ))}
      </div>
      {hasMore && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-700"
        >
          {expanded ? "Show less" : `+${hiddenCount} more`}
          <ChevronDown size={14} className={`transition-transform ${expanded ? "rotate-180" : ""}`} />
        </button>
      )}
    </div>
  );
}
