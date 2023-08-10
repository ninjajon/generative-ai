# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Generative AI App Builder Utilities"""
import os
import sys

import vertexai
from langchain.llms import VertexAI
from langchain.retrievers import GoogleCloudEnterpriseSearchRetriever
from langchain.chains import RetrievalQA

from os.path import basename
from typing import Dict, List, Optional, Tuple

from google.cloud import discoveryengine_v1beta as discoveryengine

JSON_INDENT = 2


def list_documents(
    project_id: str,
    location: str,
    datastore_id: str,
) -> List[Dict[str, str]]:
    client = discoveryengine.DocumentServiceClient()

    parent = client.branch_path(
        project=project_id,
        location=location,
        data_store=datastore_id,
        branch="default_branch",
    )

    request = discoveryengine.ListDocumentsRequest(parent=parent, page_size=10)

    page_result = client.list_documents(request=request)

    return [
        {"id": document.id, "title": basename(document.content.uri)}
        for document in page_result
    ]


def search_enterprise_search(
    project_id: str,
    location: str,
    search_engine_id: str,
    page_size: int = 50,
    search_query: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    params: Optional[Dict] = None,
) -> Tuple[List[Dict[str, str | List]], str, str, str]:
    if bool(search_query) == bool(image_bytes):
        raise Exception("Cannot provide both search_query and image_bytes")

    # Create a client
    client = discoveryengine.SearchServiceClient()

    # The full resource name of the search engine serving config
    # e.g. projects/{project_id}/locations/{location}
    serving_config = client.serving_config_path(
        project=project_id,
        location=location,
        data_store=search_engine_id,
        serving_config="default_config",
    )

    print(serving_config)

    # Configuration options for search
    content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
        snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
            max_snippet_count=5, return_snippet=True
        ),
        summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
            summary_result_count=5,
            include_citations=True,
            ignore_adversarial_query=True,
            ignore_non_summary_seeking_query=True,
        ),
        extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
            max_extractive_answer_count=1, max_extractive_segment_count=1
        ),
    )

    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        page_size=page_size,
        content_search_spec=content_search_spec,
        query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
            condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
        ),
        spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
            mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
        ),
        params=params,
    )

    if search_query:
        request.query = search_query
    elif image_bytes:
        request.image_query = discoveryengine.SearchRequest.ImageQuery(
            image_bytes=image_bytes
        )

    try:
        print("3")
        response_pager = client.search(request)
        print("4")
    except Exception as e:
        print("error: ", e.__traceback__)
        raise Exception("An internal error occured")

    response = discoveryengine.SearchResponse(
        results=response_pager.results,
        facets=response_pager.facets,
        guided_search_result=response_pager.guided_search_result,
        total_size=response_pager.total_size,
        attribution_token=response_pager.attribution_token,
        next_page_token=response_pager.next_page_token,
        corrected_query=response_pager.corrected_query,
        summary=response_pager.summary,
    )

    request_url = (
        f"https://discoveryengine.googleapis.com/v1beta/{serving_config}:search"
    )

    request_json = discoveryengine.SearchRequest.to_json(
        request,
        including_default_value_fields=True,
        use_integers_for_enums=False,
        indent=JSON_INDENT,
    )
    response_json = discoveryengine.SearchResponse.to_json(
        response,
        including_default_value_fields=True,
        use_integers_for_enums=False,
        indent=JSON_INDENT,
    )

    results = get_enterprise_search_results(response)
    return results, request_url, request_json, response_json


def get_enterprise_search_results(
    response: discoveryengine.SearchResponse,
) -> List[Dict[str, str | List]]:
    """
    Extract Results from Enterprise Search Response
    """

    ROBOT = "https://www.google.com/images/errors/robot.png"

    def get_thumbnail_image(data: Dict) -> str:
        cse_thumbnail = data.get("pagemap", {}).get("cse_thumbnail")
        image_link = data.get("image", {}).get("thumbnailLink")

        if cse_thumbnail:
            return cse_thumbnail[0]["src"]
        elif image_link:
            return image_link
        else:
            return ROBOT

    def get_formatted_link(data: Dict) -> str:
        html_formatted_url = data.get("htmlFormattedUrl")
        image_context_link = data.get("image", {}).get("contextLink")
        return html_formatted_url or image_context_link or ROBOT

    return [
        {
            "title": result.document.derived_struct_data["title"],
            "htmlTitle": result.document.derived_struct_data.get(
                "htmlTitle", result.document.derived_struct_data["title"]
            ),
            "link": result.document.derived_struct_data["link"],
            "htmlFormattedUrl": get_formatted_link(result.document.derived_struct_data),
            "displayLink": result.document.derived_struct_data["displayLink"],
            "snippets": [
                s["snippet"] for s in result.document.derived_struct_data["snippets"]
            ],
            "thumbnailImage": get_thumbnail_image(result.document.derived_struct_data),
            "resultJson": discoveryengine.SearchResponse.SearchResult.to_json(
                result, including_default_value_fields=True, indent=JSON_INDENT
            ),
        }
        for result in response.results
    ]


def recommend_personalize(
    project_id: str,
    location: str,
    datastore_id: str,
    serving_config_id: str,
    document_id: str,
    user_pseudo_id: Optional[str] = "xxxxxxxxxxx",
    attribution_token: Optional[str] = None,
) -> Tuple:
    # Create a client
    client = discoveryengine.RecommendationServiceClient()

    # The full resource name of the search engine serving config
    # e.g. projects/{project_id}/locations/{location}
    serving_config = client.serving_config_path(
        project=project_id,
        location=location,
        data_store=datastore_id,
        serving_config=serving_config_id,
    )

    user_event = discoveryengine.UserEvent(
        event_type="view-item",
        user_pseudo_id=user_pseudo_id,
        attribution_token=attribution_token,
        documents=[discoveryengine.DocumentInfo(id=document_id)],
    )

    request = discoveryengine.RecommendRequest(
        serving_config=serving_config,
        user_event=user_event,
        params={"returnDocument": True, "returnScore": True},
    )

    response = client.recommend(request)

    request_url = (
        f"https://discoveryengine.googleapis.com/v1beta/{serving_config}:recommend"
    )

    request_json = discoveryengine.RecommendRequest.to_json(
        request, including_default_value_fields=True, indent=JSON_INDENT
    )
    response_json = discoveryengine.RecommendResponse.to_json(
        response, including_default_value_fields=True, indent=JSON_INDENT
    )

    results = get_personalize_results(response)
    return results, response.attribution_token, request_url, request_json, response_json


def get_storage_link(uri: str) -> str:
    return uri.replace("gs://", "https://storage.googleapis.com/")


def get_personalize_results(
    response: discoveryengine.RecommendResponse,
) -> List[Dict]:
    """
    Extract Results from Personalize Response
    """
    return [
        {
            "id": result.id,
            "title": basename(result.document.content.uri),
            "htmlFormattedUrl": result.document.content.uri,
            "link": get_storage_link(result.document.content.uri),
            "mimeType": result.document.content.mime_type,
            "resultJson": discoveryengine.RecommendResponse.RecommendationResult.to_json(
                result, including_default_value_fields=True, indent=JSON_INDENT
            ),
        }
        for result in response.results
    ]

def search_enterprise_search_llm(
    project_id: str,
    region: str,
    search_engine_id: str,
    search_query: Optional[str] = None,
):
    model = "text-bison@001"
    vertexai.init(project=project_id, location=region)
    llm = VertexAI(model_name=model)

    retriever = GoogleCloudEnterpriseSearchRetriever(
        project_id=project_id, search_engine_id=search_engine_id
    )

    retrieval_qa = RetrievalQA.from_chain_type(
        llm=llm, chain_type="refine", retriever=retriever, return_source_documents=False
    )

    try:
        results = retrieval_qa({"query": search_query})
    except Exception as e:
        print("error:", e)

    return results
