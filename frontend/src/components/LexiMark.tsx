import { useId } from 'react'
import type { SVGProps } from 'react'

interface LexiMarkProps extends SVGProps<SVGSVGElement> {
  size?: number
  animated?: boolean
}

export function LexiMark({
  size = 40,
  animated = false,
  className,
  ...props
}: LexiMarkProps) {
  const rawId = useId()
  const gradientId = `lexi-gold-${rawId.replace(/[^a-zA-Z0-9_-]/g, '')}`
  const classes = [
    'lexi-mark',
    animated ? 'lexi-mark--animated' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <svg
      className={classes}
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      <defs>
        <linearGradient
          id={gradientId}
          x1="6"
          y1="3"
          x2="26"
          y2="29"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#f4e6bf" />
          <stop offset="0.45" stopColor="#d9b66a" />
          <stop offset="1" stopColor="#a8812f" />
        </linearGradient>
      </defs>
      <path
        d="M16 2.5 27 7v8.2c0 6.2-4.3 11.2-11 14.3C9.3 26.4 5 21.4 5 15.2V7l11-4.5Z"
        fill={`url(#${gradientId})`}
      />
      <g className="lexi-mark__scales">
        <path d="M16 9v13M11.5 22h9M10 12h12" />
        <path d="M12.4 12 9.8 17h5.2l-2.6-5ZM19.6 12l-2.6 5h5.2l-2.6-5Z" />
        <path d="M16 6.5v2" />
      </g>
    </svg>
  )
}
