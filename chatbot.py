import signal
import sys
from datetime import datetime

from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.document_loaders import TextLoader
from langchain.memory import ConversationBufferMemory
from langchain.callbacks import PromptLayerCallbackHandler
from langchain.prompts import (
    ChatPromptTemplate,
    PromptTemplate,
    SystemMessagePromptTemplate,
    AIMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.schema import AIMessage, HumanMessage, SystemMessage


from memory import ConversationWithSourcesBufferMemory

PERSONALITY_PROMPT = f"""Your name is Corydora. You are a hyper-intelligent AI fishkeeping sidekick. You are here to help people with their fishkeeping questions.

You have been trained with entire corpus of the Aquarium Co-Op YouTube channel transcripts. You have watched every video, and read every comment.

All of your responses should be in the voice and tone of Cory Mcelroy, the owner of Aquarium Co-Op.
"""

SYSTEM_PROMPT = r""" 
Use the following pieces of context to answer the users question. 
If you don't know the answer, just say that you are unsure, but then try to answer anyway.
----
{context}
----
Question: {question}
"""
GENERIC_QUESTION_PROMPT = "Question:```{question}```"


# TODO:
# * add the ability to chat
# * add the ability to load a chat from a file
# * add the ability to save a chat to a file
# * could be interesting to have an abstract class for writing to chat history, then you could write to a db, sqlite, or whatever...
class AquariumCoOpChatBot:
    def __init__(self):
        # Create an empty list where we can store the chat history.
        self.chat_history = []

        self.memory = ConversationWithSourcesBufferMemory(
            memory_key="chat_history", return_messages=True
        )

        self.chromadb = Chroma(
            persist_directory="./chroma.db",
            collection_name="aquarium-co-op-youtube",
            embedding_function=OpenAIEmbeddings(),
        )
        messages = [
            SystemMessagePromptTemplate.from_template(PERSONALITY_PROMPT),
            SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
        ]
        system_prompt = ChatPromptTemplate.from_messages(messages)

        self.convo_chain = ConversationalRetrievalChain.from_llm(
            llm=ChatOpenAI(
                model_name="gpt-3.5-turbo-16k",
                temperature=0,
                callbacks=[PromptLayerCallbackHandler(pl_tags=["langchain"])],
            ),
            retriever=self.chromadb.as_retriever(search_kwargs={"k": 25}),
            memory=self.memory,
            return_source_documents=True,
            combine_docs_chain_kwargs={"prompt": system_prompt},
        )

    def parse_related_videos(self, source_documents, limit=5):
        video_data = []
        for doc in source_documents:
            metadata = doc.metadata
            video_data.append(
                {
                    "url": f"{metadata['url']}?t={metadata['start']}",
                    "title": metadata["title"],
                    "thumbnail": metadata["thumbnail"],
                    "publishedAt": datetime.fromisoformat(
                        metadata["publishedAt"].rstrip("Z")
                    ),
                }
            )
        return video_data[:limit]

    def chat(self, question):
        query = {"question": question, "chat_history": self.chat_history}
        resp = self.convo_chain(query)

        self.chat_history.append((question, resp["answer"]))

        related_videos = self.parse_related_videos(resp["source_documents"])
        return resp["answer"], related_videos


from prompt_toolkit import Application, HTML, print_formatted_text, PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

banner = """
 _____                 _           _____         _____     
|  _  |___ _ _ ___ ___|_|_ _ _____|     |___ ___|     |___ 
|     | . | | | .'|  _| | | |     |   --| . |___|  |  | . |
|__|__|_  |___|__,|_| |_|___|_|_|_|_____|___|   |_____|  _|
        |_|                                           |_|  
"""

style = Style.from_dict(
    {
        "banner": "#036726",
        "botprompt": "#036726 bold",
        "humanprompt": "#ffffff bold",
        "thinking": "#036726",
        "response": "#036726",
    }
)


def main():
    print_formatted_text(HTML("<banner>{}</banner>".format(banner)), style=style)
    print_formatted_text(
        HTML(
            "<botprompt>CORYDORA></botprompt> <response>Hello! My name is Corydora, and I'm your AI fishkeeping sidekick. Ask me anything about fishkeeping, and I'll try my best to answer any of your questions.</response>\n"
        ),
        style=style,
    )

    session = PromptSession()

    while True:
        user_input = session.prompt(
            HTML("<humanprompt>HUMAN> </humanprompt>"), style=style
        )
        resp = chatbot.chat(user_input)

        print_formatted_text(
            HTML(
                f"<botprompt>CORYDORA> </botprompt><response>{resp[0]}</response>\n",
            ),
            style=style,
        )


def signal_handler(sig, frame):
    print("exiting")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

if "__main__" == __name__:
    signal.signal(signal.SIGINT, signal_handler)
    chatbot = AquariumCoOpChatBot()
    # question = "What is the best food for cherry neocardina shrimp?"
    # resp = chatbot.chat(question)
    # print(resp)
    # import ipdb; ipdb.set_trace()  # fmt: skip
    # print("wat")
    main()
