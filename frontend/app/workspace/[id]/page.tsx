import { Metadata } from 'next'
import App from './editor'

// Define the static params that should be generated at build time
export async function generateStaticParams() {
  // Since this is a dynamic workspace where IDs are created at runtime,
  // we'll pre-render a placeholder page that will be hydrated with 
  // the actual session data on the client side
  return [
    {
      id: 'new'  // This creates a default /workspace/new route
    }
  ]
}

// Optional: Add metadata for the page
export const metadata: Metadata = {
  title: 'Workspace',
  description: 'Interactive coding workspace'
}

// Page component
export default function WorkspacePage({ params }: { params: { id: string } }) {
  return <App />
}