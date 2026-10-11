"use client";
import { departments, type Snapshot, type State } from "@/lib/model";
const colors: Record<State, string> = {
  WORKING: "#8cddbb",
  IDLE: "#8b9cae",
  BLOCKED: "#edbd77",
  ERROR: "#f48b94",
  OFFLINE: "#637285",
};
const palette = [
  "#91b7ee",
  "#8cddbb",
  "#c4b2ec",
  "#efb6a0",
  "#a9c7f1",
  "#e4ce8c",
  "#a8b7ca",
];
function point(x: number, y: number, z = 0) {
  return [530 + (x - y) * 0.82, 70 + (x + y) * 0.4 - z];
}
function pts(coords: number[][]) {
  return coords
    .map(([x, y, z]) => point(x, y, z))
    .map((p) => p.join(","))
    .join(" ");
}
function Plant({ x, y }: { x: number; y: number }) {
  const [px, py] = point(x, y);
  return (
    <g aria-hidden="true">
      <ellipse cx={px} cy={py + 2} rx="13" ry="6" fill="#0d1520" />
      <path d={`M${px - 8},${py - 14}h16l-3,16h-10z`} fill="#758994" />
      <path
        d={`M${px},${py - 12}v-30m0,13q-24,-22 -17,-29q18,0 17,29m0,3q26,-24 18,-31q-18,4 -18,31`}
        stroke="#547e6c"
        strokeWidth="5"
        fill="#719c7c"
      />
    </g>
  );
}
export default function Office({
  agents,
  onSelect,
  selected,
  stale,
}: {
  agents: Snapshot["agents"];
  onSelect: (id: string) => void;
  selected?: string;
  stale: boolean;
}) {
  return (
    <div className="office-scene">
      <svg
        viewBox="0 0 1100 690"
        className="office-svg"
        fontFamily="sans-serif"
        aria-label="Isometric AXXIBOTS headquarters. Select an agent workstation for details."
        role="group"
      >
        <defs>
          <linearGradient id="floor" x2="0" y2="1">
            <stop stopColor="#273a4c" />
            <stop offset="1" stopColor="#1e2c3b" />
          </linearGradient>
          <linearGradient id="wall">
            <stop stopColor="#45586d" stopOpacity=".8" />
            <stop offset="1" stopColor="#314456" stopOpacity=".5" />
          </linearGradient>
          <filter id="shadow">
            <feGaussianBlur stdDeviation="15" />
          </filter>
          <pattern
            id="grid"
            width="48"
            height="24"
            patternUnits="userSpaceOnUse"
          >
            <path
              d="M24 0L48 12 24 24 0 12Z"
              fill="none"
              stroke="#90afc1"
              strokeOpacity=".045"
            />
          </pattern>
        </defs>
        <rect width="1100" height="690" fill="url(#grid)" />
        <ellipse
          cx="525"
          cy="468"
          rx="407"
          ry="159"
          fill="#000"
          opacity=".35"
          filter="url(#shadow)"
        />
        <polygon
          points={pts([
            [-18, -18, 0],
            [688, -18, 0],
            [688, 540, 0],
            [-18, 540, 0],
          ])}
          fill="#344658"
          stroke="#627488"
          strokeWidth="1"
        />
        <polygon
          points={pts([
            [688, -18, 0],
            [688, 540, 0],
            [688, 540, -15],
            [688, -18, -15],
          ])}
          fill="#192b3a"
        />
        <polygon
          points={pts([
            [-18, 540, 0],
            [688, 540, 0],
            [688, 540, -15],
            [-18, 540, -15],
          ])}
          fill="#152431"
        />
        {departments.map((dep, i) => {
          const x = (i % 3) * 225,
            y = Math.floor(i / 3) * 178,
            w = 210,
            d = 160,
            roomAgents = agents.filter((a) => a.department === dep);
          const [labelX, labelY] = point(x + 105, y + 150, 0);
          return (
            <g key={dep}>
              <polygon
                points={pts([
                  [x, y, 0],
                  [x + w, y, 0],
                  [x + w, y + d, 0],
                  [x, y + d, 0],
                ])}
                fill="url(#floor)"
                stroke="#6b8397"
                strokeOpacity=".35"
              />
              <polygon
                points={pts([
                  [x, y, 0],
                  [x + w, y, 0],
                  [x + w, y, 48],
                  [x, y, 48],
                ])}
                fill="url(#wall)"
                stroke="#8ea2b5"
                strokeOpacity=".2"
              />
              <polygon
                points={pts([
                  [x, y, 0],
                  [x, y + d, 0],
                  [x, y + d, 48],
                  [x, y, 48],
                ])}
                fill="#43576a"
                fillOpacity=".5"
                stroke="#8ea2b5"
                strokeOpacity=".2"
              />
              <polyline
                points={pts([
                  [x, y + d, 48],
                  [x, y, 48],
                  [x + w, y, 48],
                ])}
                stroke={palette[i]}
                strokeOpacity=".65"
                strokeWidth="2"
                fill="none"
              />
              {roomAgents.length === 0 && (
                <text
                  x={labelX}
                  y={labelY - 15}
                  textAnchor="middle"
                  fill="#8595a8"
                  fontSize="11"
                >
                  No registered agents
                </text>
              )}
              {roomAgents.map((a, j) => {
                const dx = x + 26 + (j % 2) * 92,
                  dy = y + 28 + Math.floor(j / 2) * 62;
                const [px, py] = point(dx + 34, dy + 30, 34);
                const working = a.state === "WORKING" && !stale;
                return (
                  <g
                    key={a.id}
                    tabIndex={0}
                    role="button"
                    aria-label={`${a.name}, ${stale ? "stale snapshot" : a.state}. Inspect workstation`}
                    onClick={() => onSelect(a.id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelect(a.id);
                      }
                    }}
                    className={`workstation ${working ? "working" : ""} ${selected === a.id ? "selected" : ""}`}
                  >
                    <ellipse
                      cx={px}
                      cy={py + 47}
                      rx="36"
                      ry="12"
                      fill={selected === a.id ? palette[i] : "#101c28"}
                      opacity={selected === a.id ? 0.25 : 0.7}
                    />
                    <polygon
                      points={pts([
                        [dx, dy, 26],
                        [dx + 65, dy, 26],
                        [dx + 65, dy + 33, 26],
                        [dx, dy + 33, 26],
                      ])}
                      fill={selected === a.id ? "#8ca4b7" : "#647a8d"}
                      stroke={selected === a.id ? "#bde8d7" : "#91a4b4"}
                      strokeWidth="1"
                    />
                    <path
                      d={`M${point(dx + 5, dy + 28, 26).join(" ")}L${point(dx + 5, dy + 28, 0).join(" ")}M${point(dx + 60, dy + 28, 26).join(" ")}L${point(dx + 60, dy + 28, 0).join(" ")}`}
                      stroke="#34495b"
                      strokeWidth="4"
                    />
                    <rect
                      x={px - 18}
                      y={py - 22}
                      width="30"
                      height="20"
                      rx="3"
                      fill="#111e2b"
                      stroke="#8196a8"
                    />
                    <rect
                      x={px - 15}
                      y={py - 19}
                      width="24"
                      height="14"
                      rx="1"
                      fill={working ? "#37665b" : "#293d51"}
                    />
                    <path
                      className="screen-lines"
                      d={`M${px - 12} ${py - 15}h13m-13 4h17m-17 4h10`}
                      stroke={colors[a.state]}
                      strokeWidth="1.3"
                      opacity=".7"
                    />
                    <g className="character">
                      <ellipse
                        cx={px + 17}
                        cy={py + 25}
                        rx="12"
                        ry="8"
                        fill="#152a3c"
                      />
                      <path
                        d={`M${px + 9},${py + 20}q-4,-16 8,-16q13,0 10,16`}
                        fill={palette[i]}
                      />
                      <circle cx={px + 18} cy={py - 1} r="7" fill="#d5b7a2" />
                      <path
                        d={`M${px + 11},${py - 3}q0,-10 8,-8q9,0 7,9`}
                        fill="#293344"
                      />
                      <path
                        className="arms"
                        d={`M${px + 10},${py + 10}l-12,-5m27,5l-9,-5`}
                        stroke={palette[i]}
                        strokeWidth="5"
                        strokeLinecap="round"
                      />
                    </g>
                    <circle
                      cx={px + 34}
                      cy={py - 22}
                      r="4"
                      fill={stale ? "#edbd77" : colors[a.state]}
                      className={working ? "status-glow" : ""}
                    />
                    <title>{`${a.name}: ${a.state} — ${a.reason}`}</title>
                  </g>
                );
              })}
              <Plant x={x + 189} y={y + 118} />
            </g>
          );
        })}
        <g aria-hidden="true">
          <polygon
            points={pts([
              [230, 360, 7],
              [655, 360, 7],
              [655, 520, 7],
              [230, 520, 7],
            ])}
            fill="#30424e"
            stroke="#5b6f7c"
            strokeOpacity=".4"
          />
          <polygon
            points={pts([
              [335, 396, 18],
              [492, 396, 18],
              [492, 438, 18],
              [335, 438, 18],
            ])}
            fill="#718e89"
          />
          <polygon
            points={pts([
              [335, 396, 18],
              [492, 396, 18],
              [492, 396, 35],
              [335, 396, 35],
            ])}
            fill="#91aaa4"
          />
          <polygon
            points={pts([
              [345, 457, 16],
              [495, 457, 16],
              [495, 482, 16],
              [345, 482, 16],
            ])}
            fill="#547475"
          />
          <polygon
            points={pts([
              [367, 435, 22],
              [450, 435, 22],
              [450, 460, 22],
              [367, 460, 22],
            ])}
            fill="#b3a387"
          />
          <Plant x={620} y={390} />
          <Plant x={265} y={478} />
          <text
            x={point(520, 494)[0]}
            y={point(520, 494)[1]}
            fill="#9caeae"
            fontSize="11"
            letterSpacing="3"
            textAnchor="middle"
          >
            THE COMMONS
          </text>
        </g>
        {departments.map((dep, i) => {
          const x = (i % 3) * 225,
            y = Math.floor(i / 3) * 178;
          const [labelX, labelY] = point(x + 105, y + 150);
          return (
            <g key={`labels-${dep}`} pointerEvents="none">
              <rect
                x={labelX - 96}
                y={labelY + 1}
                width={192}
                height={19}
                rx={5}
                fill="#172936"
                fillOpacity={0.85}
              />
              <text
                x={labelX}
                y={labelY + 13}
                textAnchor="middle"
                fill="#b8cbd9"
                fontSize={9}
                letterSpacing={0.8}
              >
                {dep.toUpperCase()}
              </text>
              {agents
                .filter((a) => a.department === dep)
                .map((a, j) => {
                  const [px, py] = point(
                    x + 60 + (j % 2) * 92,
                    y + 58 + Math.floor(j / 2) * 62,
                    34,
                  );
                  return (
                    <text
                      key={a.id}
                      x={px + 18}
                      y={py + 42}
                      textAnchor="middle"
                      fill="#c8d9e5"
                      fontSize={8}
                    >
                      {a.name}
                    </text>
                  );
                })}
            </g>
          );
        })}
        <text x="32" y="648" fill="#70899e" fontSize="10" letterSpacing="2">
          HQ / LEVEL 01
        </text>
        <text
          x="1065"
          y="648"
          textAnchor="end"
          fill="#70899e"
          fontSize="10"
          letterSpacing="2"
        >
          READ-ONLY OPERATIONS
        </text>
      </svg>
      <div className="office-legend">
        {Object.entries(colors).map(([state, color]) => (
          <span key={state}>
            <i style={{ background: color }} />
            {state.toLowerCase()}
          </span>
        ))}
      </div>
    </div>
  );
}
