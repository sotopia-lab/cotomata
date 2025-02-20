import os
from openai import OpenAI
import sys

class ConversationAgent:
    def __init__(self, name, system_prompt):
        self.name = name
        self.system_prompt = system_prompt + "\nKeep your responses concise and conversational, around 2-3 sentences."
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError('OPENAI_API_KEY environment variable is not set')
        self.conversation_history = []

    def respond(self, message):
        """Generate a streaming response based on the conversation history and new message"""
        # Add the received message to conversation history
        if message:
            self.conversation_history.append({"role": "user", "content": message})

        # Prepare messages for the API call
        messages = [
            {"role": "system", "content": self.system_prompt}
        ] + self.conversation_history

        try:
            stream = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True
            )
            
            # Initialize response content
            content = ""
            print(f"\n{self.name} is typing: ", end="", flush=True)
            
            # Process the stream
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    chunk_content = chunk.choices[0].delta.content
                    content += chunk_content
                    print(chunk_content, end="", flush=True)
            
            print()  # New line after response
            
            # Add the complete response to conversation history
            self.conversation_history.append({"role": "assistant", "content": content})
            return content
        except Exception as e:
            print(f'Error generating response: {e}')
            return None

def simulate_conversation(turns=2):
    # Initialize two software engineer agents with planning phase prompts
    agent1 = ConversationAgent(
        "SWE1",
        "You are a software engineer in the planning phase. Your goal is to write code "
        "that outputs 'hello I am agent1'. First, discuss your approach with the other engineer "
        "for 2 turns to ensure both individual goals can be achieved in the final merged code."
    )

    agent2 = ConversationAgent(
        "SWE2",
        "You are a software engineer in the planning phase. Your goal is to write code "
        "that outputs 'hello I am agent2'. First, discuss your approach with the other engineer "
        "for 2 turns to ensure both individual goals can be achieved in the final merged code."
    )

    # Planning Phase
    print("\n=== Planning Phase ===")
    current_message = "Let's discuss how we can structure our code to output both our messages when merged. What's your approach?"
    print(f"\nInitial Question: {current_message}\n")

    # Planning discussion for specified number of turns
    for i in range(turns):
        print(f"\n--- Planning Turn {i + 1} ---")

        # Agent 1's turn
        response1 = agent1.respond(current_message)
        if not response1:
            print("[Failed to generate response]")
            break
        current_message = response1

        # Agent 2's turn
        response2 = agent2.respond(current_message)
        if not response2:
            print("[Failed to generate response]")
            break
        current_message = response2

    # Update agents with coding phase prompts
    agent1.system_prompt = (
        "You are now in the coding phase. Based on the previous discussion, implement code "
        "that outputs 'hello I am agent1' in a way that will work when merged with your colleague's code."
    )

    agent2.system_prompt = (
        "You are now in the coding phase. Based on the previous discussion, implement code "
        "that outputs 'hello I am agent2' in a way that will work when merged with your colleague's code."
    )

    # Coding Phase
    print("\n=== Coding Phase ===")
    current_message = "Now, let's implement our code based on our discussion. Please share your implementation."

    # Get implementations from both agents
    print("\n--- Agent 1's Implementation ---")
    agent1_code = agent1.respond(current_message)

    print("\n--- Agent 2's Implementation ---")
    agent2_code = agent2.respond(agent1_code)

    # Code Comparison Phase
    print("\n=== Code Comparison Phase ===")
    
    # Update agents with code review prompts
    agent1.system_prompt = (
        "You are now in the code review phase. Review both implementations and ensure they will work "
        "together to achieve both goals. Suggest any necessary modifications."
    )

    agent2.system_prompt = (
        "You are now in the code review phase. Review both implementations and ensure they will work "
        "together to achieve both goals. Suggest any necessary modifications."
    )

    # Final review and agreement
    review_message = "Let's review our implementations and ensure they will work together. Any suggestions for modifications?"
    
    print("\n--- Final Review ---")
    agent1_review = agent1.respond(review_message)
    agent2_review = agent2.respond(agent1_review)

if __name__ == '__main__':
    simulate_conversation()