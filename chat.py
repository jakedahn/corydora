from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.document_loaders import TextLoader


embedding = OpenAIEmbeddings()

# Now we can load the persisted database from disk, and use it as normal.
vectordb = Chroma(
    persist_directory="./chroma.db",
    collection_name="aquarium-co-op-youtube",
    embedding_function=embedding,
)

qa = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model_name="gpt-3.5-turbo-16k"),
    chain_type="stuff",
    retriever=vectordb.as_retriever(search_kwargs={"k": 25}),
    return_source_documents=True,
)


query = "What is the best food for cherry neocardina shrimp?"
resp = qa({"query": query})

print("query: ", query)
print("result: ", resp["result"])

import ipdb

ipdb.set_trace()
