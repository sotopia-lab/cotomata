import React from 'react';
import ReactMarkdown from 'react-markdown';

// Define the structure of the props for the SceneContext component
interface SceneContextProps {
  messages: { text: string; agentName?: string }[];
}

// Main SceneContext component definition
export const SceneContext: React.FC<SceneContextProps> = ({ messages }) => {
  console.log(messages); // Log messages for debugging purposes

  return (
    <div id="scene-context-container">
      <div id="scene-context-header">Scene Context</div>
      <div id="scene-context-messages">
        {messages.map((message, index) => (
          <div key={index} className="scene-message">
            {message.agentName && <strong>{message.agentName}: </strong>} {/* Display agent name if available */}
            <ReactMarkdown>{message.text}</ReactMarkdown> {/* Render message text as markdown */}
          </div>
        ))}
      </div>
    </div>
  );
};