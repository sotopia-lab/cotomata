const config = {
  backendUrl: process.env.NODE_ENV === 'production' 
    ? 'wss://sotopia-lab--cotomata-backend.modal.run'  // Modal backend URL
    : 'ws://localhost:8000',  // Local development
  basePath: process.env.NODE_ENV === 'production' ? '' : ''
}

export default config; 