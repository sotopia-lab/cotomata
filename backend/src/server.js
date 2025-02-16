import { Server } from 'socket.io';
import { createClient } from 'redis';
import { createServer } from 'http';
import { v4 as uuidv4 } from 'uuid';
import { createClient as createSupabaseClient } from '@supabase/supabase-js';

// Redis client configuration
const redisClient = createClient({
  url: 'redis://localhost:6379/0'
});

// Supabase client configuration


const saveMessageToSupabase = async (sessionId, channel, message, messageType) => {
  try {
    const messageData = JSON.parse(message);
    const timestamp = new Date().toISOString();

    if (messageType === 'scene') {
      const { data, error } = await supabase
        .from('scene_messages')
        .insert([{
          session_id: sessionId,
          channel: channel,
          content: messageData.data.text,
          timestamp: timestamp
        }]);
      
      if (error) throw error;
    } else {
      const { data, error } = await supabase
        .from('messages')
        .insert([{
          session_id: sessionId,
          channel: channel,
          agent_name: messageData.data.agent_name,
          action_type: messageData.data.action_type,
          argument: messageData.data.argument,
          path: messageData.data.path || '',
          timestamp: timestamp
        }]);
      
      if (error) throw error;
    }
  } catch (err) {
    console.error('Error saving message to Supabase:', err);
  }
};

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
        `Jack:Jane:${sessionId}`,
        `Jane:Jack:${sessionId}`,
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

        // // Determine message type based on channel
        // const messageType = channels.startsWith('Scene:') ? 'scene' : 'message';
        
        // // Save message to Supabase
        // saveMessageToSupabase(sessionId, channels, message, messageType);

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

    socket.on('init_agent_conversation', async ({ sessionId }, callback) => {
      if (!sessionId) return;
      try {
        const init_params = {
          redis_url: 'redis://localhost:6379/0',
          extra_modules: [
            "interview_case.interview_agent",
            "interview_case.nodes.initial_message_node",
            "interview_case.nodes.chat_print_node"
          ],
          nodes: [
            {
              "node_name": "Jack",
              "node_class": "llm_agent",
              "node_args": {
                "query_interval": 5,
                "output_channel": `Jack:Jane:${sessionId}`,
                "input_text_channels": [`Jane:Jack:${sessionId}`],
                "input_env_channels": [`Scene:Jack:${sessionId}`, `Runtime:Agent:${sessionId}`],
                "input_tick_channel": `tick/secs/${sessionId}`,
                "goal": "Your goal is to effectively test Jane's technical ability and finally decide if she has passed the interview. Make sure to also evaluate her communication skills, problem-solving approach, and enthusiasm.",
                "model_name": "gpt-4o",
                "agent_name": "Jack"
              }
            },
            {
              "node_name": "Jane",
              "node_class": "llm_agent",
              "node_args": {
                "query_interval": 7,
                "output_channel": `Jane:Jack:${sessionId}`,
                "input_text_channels": [`Jack:Jane:${sessionId}`], 
                "input_env_channels": [`Scene:Jane:${sessionId}`, `Runtime:Agent:${sessionId}`],
                "input_tick_channel": `tick/secs/${sessionId}`,
                "goal": "Your goal is to perform well in the interview by demonstrating your technical skills, clear communication, and enthusiasm for the position. Stay calm, ask clarifying questions when needed, and confidently explain your thought process.",
                "model_name": "gpt-4o",
                "agent_name": "Jane"
              }
            },
            {
              "node_name": "tick",
              "node_class": "tick"
            },
            {
              "node_name": "JaneScene",
              "node_class": "initial_message",
              "node_args": {
                "input_tick_channel": `tick/secs/${sessionId}`,
                "output_channels": [`Scene:Jane:${sessionId}`],
                "env_scenario": "You are Jane, a college senior at Stanford University interviewing for a Software Engineering Intern position at a Fintech company. You are currently sitting in an office with your interviewer, Jack.\nIt's natural to feel a bit nervous, but remind yourself that you have prepared well. You are very good at PyTorch but do not know anything about JAX. Please ask questions and use the resources the interviewer provides.\nYou MUST look into the meand and square documentation before implmentaing the function by using browse. You should also ask clarifying questions about the array shapes to the interviewer.\nKeep your conversations short and to the point and NEVER repeat yourself\n\nYou need to code uisng the JAX library. The initial question has some URLs to documentation that you can use to check the syntax.\nIf you have a question about reshape syntax use: https://jax.readthedocs.io/en/latest/_autosummary/jax.numpy.reshape.html\nIf you have a question about mean syntax: https://jax.readthedocs.io/en/latest/_autosummary/jax.numpy.mean.html\nIf you have a question about concatenate:  https://jax.readthedocs.io/en/latest/_autosummary/jax.numpy.concatenate.html\nIf you have a question about square check: https://jax.readthedocs.io/en/latest/_autosummary/jax.numpy.square.html\n\nRun your code to verify the working."
              }
            },
            {
              "node_name": "JackScene",
              "node_class": "initial_message",
              "node_args": {
                "input_tick_channel": `tick/secs/${sessionId}`,
                "output_channels": [`Scene:Jack:${sessionId}`],
                "env_scenario": "You are Jack, a Principal Software Engineer at a Fintech company with over 10 years of experience in the field.\nYou graduated from Stanford with a degree in Computer Science and have been with the Fintech company for the past 5 years.\nYou enjoy mentoring interns and new hires, and you're known for your approachable demeanor and knack for explaining complex concepts in an understandable way.\nToday, you are interviewing Jane, a promising candidate from Stanford who is aiming for a Software Engineering Internship.\nTRY using none action to allow the interviewer to do her work UNLESS you need to provide feedback or do any action.\nIf the interviewer takes no action for 2 turns nudge them and see if they need help.\nKeep your conversations short and to the point and NEVER repeat yourself"
              }
            },
            {
              "node_name": "chat_print",
              "node_class": "chat_print",
              "node_args": {
                "print_channel_types": {
                  [`Jane:Jack:${sessionId}`]: "agent_action",
                  [`Jack:Jane:${sessionId}`]: "agent_action",
                  [`Agent:Runtime:${sessionId}`]: "agent_action"
                },
                "env_agents": ["Jack", "Jane"]
              }
            },
            {
              "node_name": "record",
              "node_class": "record",
              "node_args": {
                "jsonl_file_path": "../logs/interview_openhands.jsonl",
                "record_channel_types": {
                  [`Jane:Jack:${sessionId}`]: "agent_action",
                  [`Jack:Jane:${sessionId}`]: "agent_action",
                  [`Agent:Runtime:${sessionId}`]: "agent_action",
                  [`Runtime:Agent:${sessionId}`]: "text",
                  [`Scene:Jane:${sessionId}`]: "text",
                  [`Scene:Jack:${sessionId}`]: "text"
                }
              }
            }
          ]
        };

        const response = await fetch('http://localhost:9000/init-agents', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(init_params),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(`Failed to initialize process: ${errorData.error || response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.status === 'success') {
          callback({ success: true });
        } else {
          callback({ success: false, error: result.error });;
        }
      } catch (err) {
        callback({ success: false, error: err.message });
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