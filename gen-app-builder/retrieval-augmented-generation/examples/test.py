import os
import sys

if "google.colab" in sys.modules:
    from google.colab import auth as google_auth

    google_auth.authenticate_user()

PROJECT_ID = "jo-search-2-aygj"  # @param {type:"string"}
SEARCH_ENGINE_ID = "unstructured-internal-docs_1691496411334"  # @param {type:"string"}
REGION = "us-central1"  # @param {type:"string"}
MODEL = "text-bison@001"

os.environ["SEARCH_ENGINE_ID"] = SEARCH_ENGINE_ID
os.environ["PROJECT_ID"] = PROJECT_ID
os.environ["REGION"] = REGION
os.environ["MODEL"] = MODEL

import vertexai
from langchain.llms import VertexAI
from langchain.retrievers import GoogleCloudEnterpriseSearchRetriever

vertexai.init(project=PROJECT_ID, location=REGION)
llm = VertexAI(model_name=MODEL)

retriever = GoogleCloudEnterpriseSearchRetriever(
    project_id=PROJECT_ID, search_engine_id=SEARCH_ENGINE_ID
)

from langchain.chains import RetrievalQA

search_query = "What are the main rail safety things to consider?"

# retrieval_qa = RetrievalQA.from_chain_type(
#     llm=llm, chain_type="refine", retriever=retriever
# )
# retrieval_qa.run(search_query)

retrieval_qa = RetrievalQA.from_chain_type(
    llm=llm, chain_type="refine", retriever=retriever, return_source_documents=True
)

results = retrieval_qa({"query": search_query})



print(results["result"])
#print("*" * 79)
#print(results["result"])
#print("*" * 79)
#for doc in results["source_documents"]:
#     print("-" * 79)
#     print(doc)

# from langchain.chains import RetrievalQAWithSourcesChain

# retrieval_qa_with_sources = RetrievalQAWithSourcesChain.from_chain_type(
#     llm=llm, chain_type="stuff", retriever=retriever
# )

# retrieval_qa_with_sources({"question": search_query}, return_only_outputs=True)

#print(retrieval_qa_with_sources.)
