import { Server } from 'socket.io';
import { createClient } from 'redis';
import { createServer } from 'http';

// Redis client configuration
const redisClient = createClient({
  url: process.env.REDIS_URL || 'redis://localhost:6379/0'
});

// Allowed channels for Redis pub/sub 
const allowedChannels = ['Scene:Jack', 'Scene:Jane', 'Human:Jack', 'Jack:Human', 'Agent:Runtime', 'Runtime:Agent'];

// Connect Redis client
redisClient.on('error', (err) => {
  console.error('Redis error:', err);
});

const init = async () => {
  console.log('Connecting to Redis...');
  await redisClient.connect();
  console.log('Redis connected!');

  // Create HTTP server
  const httpServer = createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.writeHead(200);
    res.end('Socket.IO server running');
  });

  // Initialize Socket.IO server with CORS
  const io = new Server(httpServer, {
    cors: {
      origin: [
        "http://localhost:3000",
        "https://sotopia-lab--cotomata-frontend.modal.run"
      ],
      methods: ["GET", "POST"],
      credentials: true,
      transports: ['websocket', 'polling']
    },
    allowEIO3: true,
    path: '/socket.io',
    serveClient: false,
    pingTimeout: 60000,
    pingInterval: 25000
  });

  // Redis subscriber setup
  console.log('Setting up Redis subscriber...');
  const subscriber = redisClient.duplicate();
  await subscriber.connect();
  console.log('Redis subscriber connected!');

  await subscriber.subscribe(allowedChannels, (message, channel) => {
    console.log(`Received message from ${channel}: ${message}`);
    io.emit('new_message', { channel, message });
  });

  // Socket.IO connection handling
  io.on('connection', (socket) => {
    console.log('A user connected:', socket.id);

    socket.on('chat_message', async (message) => {
      console.log('Received chat message:', message);
      try {
        const agentAction = {
          data: {
            agent_name: "user",
            action_type: "speak",
            argument: message,
            path: "",
            data_type: "agent_action"
          }
        };
        await redisClient.publish('Human:Jack', JSON.stringify(agentAction));
      } catch (err) {
        console.error('Error publishing chat message:', err);
      }
    });

    socket.on('save_file', async ({ path, content }) => {
      console.log('Saving file:', path);
      try {
        const saveMessage = {
          data: {
            agent_name: "user",
            action_type: "write",
            argument: content,
            path: path,
            data_type: "agent_action"
          }
        };
        await redisClient.publish('Agent:Runtime', JSON.stringify(saveMessage));
      } catch (err) {
        console.error('Error publishing save file message:', err);
      }
    });

    socket.on('terminal_command', async (command) => {
      console.log('Received terminal command:', command);
      try {
        const messageEnvelope = {
          data: {
            agent_name: "user",
            action_type: "run",
            argument: command,
            path: "",
            data_type: "agent_action"
          }
        };
        await redisClient.publish('Agent:Runtime', JSON.stringify(messageEnvelope));
      } catch (err) {
        console.error('Error publishing command:', err);
        socket.emit('new_message', {
          channel: 'Runtime:Agent',
          message: JSON.stringify({
            data: {
              data_type: "text",
              text: `Error: ${err.message}`
            }
          })
        });
      }
    });

    // Handle process initialization
    socket.on('init_process', async () => {
      console.log('Received init_process request');
      try {
        const initParams = {
          node_name: "openhands_node",
          input_channels: ["Agent:Runtime"],
          output_channels: ["Runtime:Agent"],
          modal_session_id: "arpan"
        };

        const response = await fetch('http://localhost:5000/initialize', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(initParams)
        });
        
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(`Failed to initialize process: ${errorData.error || response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.status === 'initialized') {
          socket.emit('init_process_result', { success: true });
          console.log('OpenHands initialized successfully');
        } else {
          throw new Error(`Unexpected initialization status: ${result.status}`);
        }
      } catch (err) {
        console.error('Error initializing process:', err);
        socket.emit('init_process_result', { 
          success: false, 
          error: err.message 
        });
      }
    });

    socket.on('disconnect', () => {
      console.log('A user disconnected:', socket.id);
    });
  });

  // Start the server
  const port = process.env.PORT || 8000;
  httpServer.listen(port, '0.0.0.0', () => {
    console.log(`> Backend server ready on http://0.0.0.0:${port}`);
  });
};

init().catch(console.error); 