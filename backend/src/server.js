import { Server } from 'socket.io';
import { createClient } from 'redis';
import { createServer } from 'http';
import { v4 as uuidv4 } from 'uuid';

// Redis client configuration
const redisClient = createClient({
  url: 'redis://localhost:6379/0'
});

// // Allowed channels for Redis pub/sub 
// const allowedChannels = ['Scene:Jack', 'Scene:Jane', 'Human:Jack', 'Jack:Human', 'Agent:Runtime', 'Runtime:Agent'];

// Connect Redis client
redisClient.on('error', (err) => {
  console.error('Redis error:', err);
});

const init = async () => {
  await redisClient.connect();

  // Create HTTP server
  const httpServer = createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.writeHead(200);
    res.end('Socket.IO server running');
  });

  // Initialize Socket.IO server with CORS
  const io = new Server(httpServer, {
    cors: {
      origin: "http://localhost:3000",
      methods: ["GET", "POST"]
    }
  });

  // Redis subscriber setup
  const subscriber = redisClient.duplicate();
  await subscriber.connect();

  // await subscriber.subscribe(allowedChannels, (message, channel) => {
  //   console.log(`Received message from ${channel}: ${message}`);
  //   io.emit('new_message', { channel, message });
  // });

  // Store active sessions and their Redis channels
  const activeSessions = {};

  const getAllowedChannels = (sessionId, sessionType) => {
    if (sessionType === 'Human/AI') {
      return [
        `Scene:Jack:${sessionId}`,
        `Scene:Jane:${sessionId}`,
        `Human:Jack:${sessionId}`,
        `Jack:Human:${sessionId}`,
        `Agent:Runtime:${sessionId}`,
        `Runtime:Agent:${sessionId}`,
      ];
    }
    return [
      `Human:Jack:${sessionId}`,
      `Jack:Human:${sessionId}`,
      `Agent:Runtime:${sessionId}`,
      `Runtime:Agent:${sessionId}`,
    ];
  };

  // Socket.IO connection handling
  io.on('connection', (socket) => {

    console.log('A user connected');
    // const socketState = {
    //   currentSessionId: null
    // };

    socket.on('create_session', async ({sessionType}, callback) => {
      const sessionId = uuidv4();
      const channels = getAllowedChannels(sessionId, sessionType)
      activeSessions[sessionId] = {channels, sessionType}

      console.log(`New session created: ${sessionId}, Type: ${sessionType}`);

      await subscriber.subscribe(channels, (message, channels) => {
        console.log(`Received message from ${channels}: ${message}`);
        io.to(sessionId).emit('new_message', { channels, message });
      })

      callback({ sessionId });

      socket.join(sessionId);
    });

    // Join an existing session
    socket.on('join_session', async ({ sessionId }, callback) => {
      if (!activeSessions[sessionId]) {
        callback({ success: false, error: 'Session does not exist' });
        return;
      }

      console.log(`User joined session: ${sessionId}`);
      socket.join(sessionId);
      // socketState.currentSessionId = sessionId;
      callback({ success: true });
    });

    socket.on('chat_message', async ({ sessionId, message}) => {
      if (!sessionId) return;

      console.log(`Chat message in session ${sessionId}:`, message);
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
        await redisClient.publish(`Human:Jack:${sessionId}`, JSON.stringify(agentAction));
      } catch (err) {
        console.error('Error publishing chat message:', err);
      }
    });

    socket.on('save_file', async ({ sessionId, path, content }) => {
      if (!sessionId) return;

      console.log(`Saving file in session ${sessionId}:`, path);
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
        await redisClient.publish(`Agent:Runtime:${sessionId}`, JSON.stringify(saveMessage));
      } catch (err) {
        console.error('Error publishing save file message:', err);
      }
    });

    socket.on('terminal_command', async ({ sessionId, command }) => {
      if (!sessionId) return;
      console.log(`Terminal command in session ${sessionId}:`, command);

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
        await redisClient.publish(`Agent:Runtime:${sessionId}`, JSON.stringify(messageEnvelope));
      } catch (err) {
        console.error('Error publishing command:', err);
        socket.emit('new_message', {
          channel: `Runtime:Agent:${sessionId}`,
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
    socket.on('init_process', async (sessionId) => {
      if (!sessionId) return;

      console.log(`Initializing process in session ${sessionId}`);
      try {
        const initParams = {
          node_name: "openhands_node",
          input_channels: [`Agent:Runtime:${sessionId}`],
          output_channels: [`Runtime:Agent:${sessionId}`],
          modal_session_id: sessionId
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
          socket.emit('init_process_result', { success: true, sessionId: sessionId });
          // callback({ success: true });
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
        // callback({ success: false, error: err.message });
      }
    });

    // Stop/Kill a session
    socket.on('kill_session', async ( { sessionId }, callback ) => {
      if (!activeSessions[sessionId]) {
        callback({ success: false, error: 'Session does not exist' });
        return;
      }

      console.log(`Killing session: ${sessionId}`);
      const { channels } = activeSessions[sessionId];
      await subscriber.unsubscribe(channels);

      io.to(sessionId).emit('session_terminated');
      delete activeSessions[sessionId];

      callback({ success: true });
    });

    socket.on('disconnect', () => {
      console.log('A user disconnected');
    });
  });

  // Start the server
  const port = process.env.PORT || 8000;
  httpServer.listen(port, () => {
    console.log(`> Backend server ready on http://localhost:${port}`);
  });
};

init().catch(console.error); 