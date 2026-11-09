import type { ReactNode, SVGProps } from 'react'

export interface IconProps extends SVGProps<SVGSVGElement> {
  size?: number
}

function Icon({
  size = 24,
  children,
  ...props
}: IconProps & { children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  )
}

export function ScalesIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 3v18M8 21h8M4 7h16" />
      <path d="M7 7l-3 6h6L7 7ZM17 7l-3 6h6l-3-6Z" />
    </Icon>
  )
}

export function GavelIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M14 3l7 7-4 4-7-7 4-4Z" />
      <path d="M12 9l-8 8" />
      <path d="M3 21h9" />
    </Icon>
  )
}

export function SealIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="10" r="5.5" />
      <path d="M8.5 15 7 21l5-2.5L17 21l-1.5-6" />
      <path d="M9.5 10l1.8 1.8L14.8 8" />
    </Icon>
  )
}

export function ScrollIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M7 3h10a2 2 0 0 1 2 2v11a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V5a2 2 0 0 1 2-2Z" />
      <path d="M8 8h7M8 12h7M8 16h4" />
      <path d="M4 17a3 3 0 0 0 3 3h10" />
    </Icon>
  )
}

export function ColumnIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M5 3h14M6 6h12M7 6v12M12 6v12M17 6v12M6 18h12M5 21h14" />
      <path d="M5 3v3M19 3v3" />
    </Icon>
  )
}

export function LaurelIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M5 21c3-2 5-5 6-9 1-4 3-7 7-9" />
      <path d="M6 17c-2 0-4-1-5-3 2-1 4-1 6 1M8 13c-2-1-3-3-3-5 2 0 4 1 5 3M11 9c-1-2-1-4 0-6 2 1 3 3 3 5M15 6c0-2 1-3 3-4 1 2 0 4-2 5" />
    </Icon>
  )
}

export function ShieldIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3Z" />
      <path d="M9 11.5l2 2 4-4" />
    </Icon>
  )
}

export function QuillIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M20 4c-7 0-12 4-14 10l-2 6 6-2C16 16 20 11 20 4Z" />
      <path d="M4 20l9-9" />
    </Icon>
  )
}

export function BookIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M3 5c3-1 5-1 8 1v13c-3-2-5-2-8-1V5Z" />
      <path d="M21 5c-3-1-5-1-8 1v13c3-2 5-2 8-1V5Z" />
      <path d="M12 6v13" />
    </Icon>
  )
}

export function AlertIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 3l9 16H3L12 3Z" />
      <path d="M12 9v5M12 17h.01" />
    </Icon>
  )
}

export function CheckIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 12l5 5L20 6" />
    </Icon>
  )
}

export function ArrowRightIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </Icon>
  )
}

export function UploadIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 16V4M7 9l5-5 5 5" />
      <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
    </Icon>
  )
}

export function TrashIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13" />
    </Icon>
  )
}

export function SearchIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="11" cy="11" r="6" />
      <path d="M16 16l5 5" />
    </Icon>
  )
}

export function LogoutIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M9 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h4" />
      <path d="M16 8l4 4-4 4M20 12H9" />
    </Icon>
  )
}

export function ClockIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 7v5l3 2" />
    </Icon>
  )
}

export function UserIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 20c1-4 4-6 8-6s7 2 8 6" />
    </Icon>
  )
}
