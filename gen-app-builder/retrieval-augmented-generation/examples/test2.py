import vertexai
from langchain.llms import VertexAI
from langchain.retrievers import GoogleCloudEnterpriseSearchRetriever

def search_enterprise_search_llm(
    project_id: str,
    region: str,
    search_engine_id: str,
    search_query:str,
    model:str
):
    print("1")
    vertexai.init(project=project_id, location=region)
    llm = VertexAI(model_name=model)
    print("2")
    retriever = GoogleCloudEnterpriseSearchRetriever(
        project_id=project_id, search_engine_id=search_engine_id
    )
    print("3")
    from langchain.chains import RetrievalQA

    retrieval_qa = RetrievalQA.from_chain_type(
        llm=llm, chain_type="refine", retriever=retriever, return_source_documents=True
    )
    #print(retrieval_qa)
    print("4")

    results = retrieval_qa({"query": search_query})
    print(results["result"])

ss = search_enterprise_search_llm(
    project_id = "jo-search-2-aygj",  # @param {type:"string"}
    search_engine_id = "unstructured-internal-docs_1691496411334",  # @param {type:"string"}
    region = "us-central1",  # @param {type:"string"}
    model = "text-bison@001",
    search_query = "what are the main principles of rail safety in the US?"
)