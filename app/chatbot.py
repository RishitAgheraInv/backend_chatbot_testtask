""" chatbot agent class"""
from typing import Dict, List, Any

from dotenv import load_dotenv
from langchain.schema import HumanMessage, AIMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END

load_dotenv()


class ChatbotState:
    """chatbot state class"""
    def __init__(self):
        self.messages: List[Dict[str, str]] = []
        self.current_response: str = ""


def create_chatbot_graph():
    """ langgraph creation"""
    # Initialize the LLM
    llm = ChatGroq(model="llama3-8b-8192", temperature=0.3)

    def process_message(state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the user message and generate response"""
        messages = state.get("messages", [])

        # Convert to LangChain message format
        chat_messages = []
        for msg in messages:
            if msg["role"] == "user":
                chat_messages.append(HumanMessage(content=msg["content"]))
            else:
                chat_messages.append(AIMessage(content=msg["content"]))

        # Generate response
        response = llm.invoke(chat_messages)

        # Add the response to messages
        messages.append({
            "role": "assistant",
            "content": response.content
        })

        return {
            "messages": messages,
            "current_response": response.content
        }

    # def should_continue(state: Dict[str, Any]) -> str:
    #     """Determine if we should continue or end"""
    #     return END

    # Create the graph
    workflow = StateGraph(dict)

    # Add nodes
    workflow.add_node("process_message", process_message)

    # Add edges
    workflow.set_entry_point("process_message")
    workflow.add_edge("process_message", END)

    return workflow.compile()


class StreamingChatbot:
    """ Streaming chatbot"""
    def __init__(self):
        self.llm = ChatGroq(model="llama3-8b-8192", temperature=0.7)

    async def stream_response(self, messages: List[Dict[str, str]]):
        """Stream response word by word"""
        # Convert to LangChain message format
        chat_messages = []
        for msg in messages:
            if msg["role"] == "user":
                chat_messages.append(HumanMessage(content=msg["content"]))
            else:
                chat_messages.append(AIMessage(content=msg["content"]))

        # Stream the response
        full_response = ""
        async for chunk in self.llm.astream(chat_messages):
            if chunk.content:
                full_response += chunk.content
                yield {
                    "chunk": chunk.content,
                    "full_response": full_response
                }

    def get_response(self, messages: List[Dict[str, str]]) -> str:
        """Get complete response (non-streaming)"""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "user":
                chat_messages.append(HumanMessage(content=msg["content"]))
            else:
                chat_messages.append(AIMessage(content=msg["content"]))

        response = self.llm.invoke(chat_messages)
        return response.content
