import { AlertIcon } from './icons'

interface AlertProps {
  message: string
}

export function Alert({ message }: AlertProps) {
  return (
    <p className="alert" role="alert">
      <span className="alert__icon" aria-hidden="true">
        <AlertIcon size={16} />
      </span>
      <span>{message}</span>
    </p>
  )
}
