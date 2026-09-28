interface Props {
  message: string | null
  prominent?: boolean
}

export default function ExaminerMessage({ message, prominent = false }: Props) {
  if (!message) return null
  return (
    <div className={`examiner${prominent ? ' prominent' : ''}`} data-testid="examiner-message" role="status">
      {message}
    </div>
  )
}
