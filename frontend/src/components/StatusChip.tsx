import type { JobStatus } from '../types'

const LABEL: Record<JobStatus, string> = {
  queued: 'Queued',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
}

export default function StatusChip({ status }: { status: JobStatus }) {
  return <span className={`chip chip-${status}`}>{LABEL[status]}</span>
}
