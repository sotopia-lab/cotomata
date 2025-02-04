#!/bin/bash

echo "Sending request to http://localhost:9000/init-agents..."

# Send the request and capture both stdout and stderr
response=$(curl -v -X POST http://localhost:9000/init-agents \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d @- << 'EOF'
{
    "redis_url": "redis://localhost:6379/0",
    "extra_modules": [
        "interview_case.interview_agent",
        "interview_case.nodes.initial_message_node",
        "interview_case.nodes.chat_print_node"
    ],
    "nodes": [
        {
            "node_name": "Jack",
            "node_class": "llm_agent",
            "node_args": {
                "query_interval": 5,
                "output_channel": "Jack:Jane",
                "input_text_channels": ["Jane:Jack"],
                "input_env_channels": ["Scene:Jack", "Runtime:Agent"],
                "input_tick_channel": "tick/secs/1",
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
                "output_channel": "Jane:Jack",
                "input_text_channels": ["Jack:Jane"],
                "input_env_channels": ["Scene:Jane", "Runtime:Agent"],
                "input_tick_channel": "tick/secs/1",
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
                "input_tick_channel": "tick/secs/1",
                "output_channels": ["Scene:Jane"],
                "env_scenario": "You are Jane, a college senior at Stanford University interviewing for a Software Engineering Intern position at a Fintech company. You are currently sitting in an office with your interviewer, Jack.\nIt's natural to feel a bit nervous, but remind yourself that you have prepared well. You are very good at PyTorch but do not know anything about JAX. Please ask questions and use the resources the interviewer provides.\nYou MUST look into the meand and square documentation before implmentaing the function by using browse. You should also ask clarifying questions about the array shapes to the interviewer.\nKeep your conversations short and to the point and NEVER repeat yourself\n\nYou need to code uisng the JAX library. The initial question has some URLs to documentation that you can use to check the syntax.\nIf you have a question about reshape syntax use: https://jax.readthedocs.io/en/latest/_autosummary/jax.numpy.reshape.html\nIf you have a question about mean syntax: https://jax.readthedocs.io/en/latest/_autosummary/jax.numpy.mean.html\nIf you have a question about concatenate:  https://jax.readthedocs.io/en/latest/_autosummary/jax.numpy.concatenate.html\nIf you have a question about square check: https://jax.readthedocs.io/en/latest/_autosummary/jax.numpy.square.html\n\nRun your code to verify the working."
            }
        },
        {
            "node_name": "JackScene",
            "node_class": "initial_message",
            "node_args": {
                "input_tick_channel": "tick/secs/1",
                "output_channels": ["Scene:Jack"],
                "env_scenario": "You are Jack, a Principal Software Engineer at a Fintech company with over 10 years of experience in the field.\nYou graduated from Stanford with a degree in Computer Science and have been with the Fintech company for the past 5 years.\nYou enjoy mentoring interns and new hires, and you're known for your approachable demeanor and knack for explaining complex concepts in an understandable way.\nToday, you are interviewing Jane, a promising candidate from Stanford who is aiming for a Software Engineering Internship.\nTRY using none action to allow the interviewer to do her work UNLESS you need to provide feedback or do any action.\nIf the interviewer takes no action for 2 turns nudge them and see if they need help.\nKeep your conversations short and to the point and NEVER repeat yourself"
            }
        },
        {
            "node_name": "chat_print",
            "node_class": "chat_print",
            "node_args": {
                "print_channel_types": {
                    "Jane:Jack": "agent_action",
                    "Jack:Jane": "agent_action",
                    "Agent:Runtime": "agent_action"
                },
                "env_agents": ["Jack", "Jane"]
            }
        },
        {
            "node_name": "record",
            "node_class": "record",
            "node_args": {
                "jsonl_file_path": "/Users/arpan/Desktop/cotomata/backend/logs/interview_openhands.jsonl",
                "record_channel_types": {
                    "Jane:Jack": "agent_action",
                    "Jack:Jane": "agent_action",
                    "Agent:Runtime": "agent_action",
                    "Runtime:Agent": "text",
                    "Scene:Jane": "text",
                    "Scene:Jack": "text"
                }
            }
        }
    ]
}
EOF
)

# Print the full response including headers
echo -e "\nFull response:"
echo "$response"

# Extract and print just the response body (assuming it's JSON)
body=$(echo "$response" | sed -n '/^{/,/^}/p')
if [ ! -z "$body" ]; then
    echo -e "\nResponse body (parsed):"
    echo "$body" | python3 -m json.tool
fi 