const config = {
  // Always connect to local backend for now
  backendUrl: 'ws://localhost:8000',
  basePath: process.env.NODE_ENV === 'production' ? '' : ''
}

export default config; 