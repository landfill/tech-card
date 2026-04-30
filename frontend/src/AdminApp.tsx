import { AppShell } from './App'
import PipelinePage from './PipelinePage'

export default function AdminApp() {
  return <AppShell adminMode renderPipeline={(initialDate) => <PipelinePage initialDate={initialDate} />} />
}
