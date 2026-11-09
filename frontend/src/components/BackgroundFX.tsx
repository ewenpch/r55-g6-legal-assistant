import { ScalesIcon } from './icons'

const WIDTH = 1440
const HEIGHT = 360
const PERIOD = 720
const SAMPLES = 120

interface WaveProps {
  id: string
  className: string
  baseline: number
  amplitude: number
  phase?: number
  variant?: 'fill' | 'line'
  strokeWidth?: number
  from: string
  to: string
}

function buildPath(baseline: number, amplitude: number, phase: number) {
  const points: string[] = []
  for (let i = 0; i <= SAMPLES; i++) {
    const x = (WIDTH * i) / SAMPLES
    const y =
      baseline + amplitude * Math.sin((2 * Math.PI * x) / PERIOD + phase)
    points.push(`${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`)
  }
  return points.join(' ')
}

function Wave({
  id,
  className,
  baseline,
  amplitude,
  phase = 0,
  variant = 'fill',
  strokeWidth = 1.6,
  from,
  to,
}: WaveProps) {
  const line = buildPath(baseline, amplitude, phase)
  const d =
    variant === 'fill' ? `${line} L${WIDTH} ${HEIGHT} L0 ${HEIGHT} Z` : line

  return (
    <div className={`waves__layer ${className}`}>
      <div className="waves__track">
        {(['a', 'b'] as const).map((copy) => {
          const gradientId = `wave-${id}-${copy}`
          return (
            <svg
              key={copy}
              className="waves__svg"
              viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
              preserveAspectRatio="none"
              focusable="false"
            >
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor={from} />
                  <stop offset="50%" stopColor={to} />
                  <stop offset="100%" stopColor={from} />
                </linearGradient>
              </defs>
              {variant === 'fill' ? (
                <path d={d} fill={`url(#${gradientId})`} />
              ) : (
                <path
                  d={d}
                  fill="none"
                  stroke={`url(#${gradientId})`}
                  strokeWidth={strokeWidth}
                  strokeLinecap="round"
                  vectorEffect="non-scaling-stroke"
                />
              )}
            </svg>
          )
        })}
      </div>
    </div>
  )
}

export function BackgroundFX() {
  return (
    <div className="background" aria-hidden="true">
      <div className="background__glow" />
      <div className="background__watermark">
        <ScalesIcon size={420} />
      </div>
      <div className="waves">
        <Wave
          id="deep"
          className="waves__layer--deep"
          baseline={196}
          amplitude={38}
          from="#d9b66a"
          to="#244a8f"
        />
        <Wave
          id="mid"
          className="waves__layer--mid waves__layer--reverse"
          baseline={228}
          amplitude={46}
          phase={1.1}
          from="#c9a24a"
          to="#1a3570"
        />
        <Wave
          id="front"
          className="waves__layer--front"
          baseline={272}
          amplitude={32}
          phase={2.2}
          from="#f4e6bf"
          to="#4f83e8"
        />
        <Wave
          id="crest"
          className="waves__layer--crest waves__layer--reverse"
          baseline={182}
          amplitude={34}
          phase={0.6}
          variant="line"
          strokeWidth={2.2}
          from="#f4e6bf"
          to="#7fb3ff"
        />
        <Wave
          id="line-a"
          className="waves__layer--line-a"
          baseline={86}
          amplitude={26}
          phase={0.2}
          variant="line"
          strokeWidth={1.8}
          from="#e8cf96"
          to="#7fb3ff"
        />
        <Wave
          id="line-b"
          className="waves__layer--line-b waves__layer--reverse"
          baseline={126}
          amplitude={22}
          phase={2.4}
          variant="line"
          strokeWidth={1.4}
          from="#4f83e8"
          to="#c9a24a"
        />
      </div>
      <div className="background__vignette" />
    </div>
  )
}
