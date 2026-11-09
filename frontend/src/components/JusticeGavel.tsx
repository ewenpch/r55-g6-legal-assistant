import { useId } from 'react'

interface JusticeGavelProps {
  active: boolean
}

export function JusticeGavel({ active }: JusticeGavelProps) {
  const rawId = useId()
  const id = rawId.replace(/[^a-zA-Z0-9_-]/g, '')
  const goldId = `gavel-gold-${id}`
  const woodId = `gavel-wood-${id}`

  return (
    <div
      className={`gavel${active ? ' gavel--striking' : ''}`}
      aria-hidden="true"
    >
      <div className="gavel__figure">
        <svg
          className="gavel__svg"
          viewBox="0 0 64 140"
          fill="none"
          focusable="false"
        >
          <defs>
            <linearGradient
              id={goldId}
              x1="8"
              y1="112"
              x2="56"
              y2="140"
              gradientUnits="userSpaceOnUse"
            >
              <stop stopColor="#f4e6bf" />
              <stop offset="0.42" stopColor="#d9b66a" />
              <stop offset="1" stopColor="#a8812f" />
            </linearGradient>
            <linearGradient
              id={woodId}
              x1="28"
              y1="10"
              x2="36"
              y2="106"
              gradientUnits="userSpaceOnUse"
            >
              <stop stopColor="#7d5f22" />
              <stop offset="0.5" stopColor="#c9a24a" />
              <stop offset="1" stopColor="#7d5f22" />
            </linearGradient>
          </defs>

          <g
            className="gavel__handle"
            stroke="#071026"
            strokeWidth="1.2"
            strokeLinejoin="round"
          >
            <rect
              x="28.5"
              y="12"
              width="7"
              height="94"
              rx="3.5"
              fill={`url(#${woodId})`}
            />
            <rect
              x="25"
              y="100"
              width="14"
              height="9"
              rx="3"
              fill={`url(#${goldId})`}
            />
            <circle cx="32" cy="8" r="5.5" fill={`url(#${goldId})`} />
          </g>

          <g
            className="gavel__head"
            stroke="#071026"
            strokeWidth="1.4"
            strokeLinejoin="round"
          >
            <rect
              x="5"
              y="112"
              width="54"
              height="28"
              rx="10"
              fill={`url(#${goldId})`}
            />
            <path
              d="M14 118h36"
              stroke="rgba(255, 251, 235, 0.45)"
              strokeWidth="1.6"
              strokeLinecap="round"
            />
            <path
              d="M12 114v24M52 114v24M29.5 112v28"
              stroke="rgba(7, 16, 38, 0.32)"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </g>
        </svg>
        <span className="gavel__impact" />
      </div>
    </div>
  )
}
