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

"""Flask Web Server"""

import base64
import os
import re
from urllib.parse import urlparse

import requests
from flask import Flask, render_template, request
from google.api_core.exceptions import ResourceExhausted
from werkzeug.exceptions import HTTPException

from consts import (
    CUSTOM_UI_DATASTORE_IDS,
    CUSTOM_UI_LLM_DATASTORE_IDS,
    LOCATION,
    REGION,
    PROJECT_ID,
    VALID_LANGUAGES,
    WIDGET_CONFIGS,
    IMAGE_SEARCH_DATASTORE_IDs,
    RECOMMENDATIONS_DATASTORE_IDs,
)
from ekg_utils import search_public_kg
from genappbuilder_utils import (
    list_documents,
    recommend_personalize,
    search_enterprise_search,
    search_enterprise_search_llm
)

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # Set maximum upload size to 16MB

FORM_OPTIONS = {
    "language_list": VALID_LANGUAGES,
    "default_language": VALID_LANGUAGES[0],
}

NAV_LINKS = [
    {
        "link": "/", 
        "name": "Search | Rail Safety | Widget", 
        "icon": "widgets"
    },
    {
        "link": "/search",
        "name": "Search | Rail Safety | Custom",
        "icon": "build",
    },
    {
        "link": "/search-llm",
        "name": "Search + GenAI | Rail Safety | Custom",
        "icon": "science",
    },
    # {
    #     "link": "/image-search",
    #     "name": "Image Search",
    #     "icon": "image",
    # },
    # {
    #     "link": "/recommend",
    #     "name": "Recommendations",
    #     "icon": "recommend",
    # },
    # {"link": "/ekg", "name": "Enterprise Knowledge Graph", "icon": "scatter_plot"},
]

RECOMMENDATIONS_DOCUMENTS = list_documents(
    project_id=PROJECT_ID,
    location=LOCATION,
    datastore_id=RECOMMENDATIONS_DATASTORE_IDs[0]["datastore_id"],
)

VALID_IMAGE_MIMETYPES = {"image/jpeg", "image/png", "image/bmp"}


@app.route("/", methods=["GET"])
@app.route("/finance", methods=["GET"])
def index() -> str:
    """
    Web Server, Homepage for Widgets
    """

    return render_template(
        "index.html",
        nav_links=NAV_LINKS,
        search_engine_options=WIDGET_CONFIGS,
    )


@app.route("/search", methods=["GET"])
def search() -> str:
    """
    Web Server, Homepage for Search - Custom UI
    """
    return render_template(
        "search.html",
        nav_links=NAV_LINKS,
    )


@app.route("/search_genappbuilder", methods=["POST"])
def search_genappbuilder() -> str:
    """
    Handle Search Gen App Builder Request
    """
    search_query = request.form.get("search_query", "")

    # Check if POST Request includes search query
    if not search_query:
        return render_template(
            "search.html",
            nav_links=NAV_LINKS,
            message_error="No query provided",
        )

    results, request_url, raw_request, raw_response = search_enterprise_search(
        project_id=PROJECT_ID,
        location=LOCATION,
        search_engine_id=CUSTOM_UI_DATASTORE_IDS[0]["datastore_id"],
        search_query=search_query,
    )

    return render_template(
        "search.html",
        nav_links=NAV_LINKS,
        message_success=search_query,
        results=results,
        request_url=request_url,
        raw_request=raw_request,
        raw_response=raw_response,
    )


@app.route("/search-llm", methods=["GET"])
def searchllm() -> str:
    """
    Web Server, Homepage for Search - LLM
    """
    return render_template(
        "search-llm.html",
        nav_links=NAV_LINKS,
    )


@app.route("/search-llm_genappbuilder", methods=["POST"])
def searchllm_genappbuilder() -> str:
    """
    Handle Search Gen App Builder Request
    """
    search_query = request.form.get("search_query", "")

    # Check if POST Request includes search query
    if not search_query:
        return render_template(
            "search-llm.html",
            nav_links=NAV_LINKS,
            message_error="No query provided",
        )

    results = search_enterprise_search_llm(
        project_id=PROJECT_ID,
        region=REGION,
        search_engine_id=CUSTOM_UI_LLM_DATASTORE_IDS[0]["datastore_id"],
        search_query=search_query,
    )

    #print(results)

    return render_template(
        "search-llm.html",
        nav_links=NAV_LINKS,
        message_success=search_query,
        results=results
    )


@app.route("/image-search", methods=["GET"])
def image_search() -> str:
    """
    Web Server, Homepage for Image Search - Custom UI
    """
    return render_template(
        "image-search.html",
        nav_links=NAV_LINKS,
    )


@app.route("/imagesearch_genappbuilder", methods=["POST"])
def imagesearch_genappbuilder() -> str:
    """
    Handle Image Search Gen App Builder Request
    """
    search_query = request.form.get("search_query", "")
    image_file = request.files["image"]
    image_content = None
    image_bytes = None

    # Check if POST Request includes search query
    if not search_query and not image_file:
        return render_template(
            "image-search.html",
            nav_links=NAV_LINKS,
            message_error="No query provided",
        )

    if image_file:
        image_content = image_file.read()
    elif search_query:
        # Check if text is a url
        image_url = urlparse(search_query)
        if all([image_url.scheme, image_url.netloc, image_url.path]):
            image_response = requests.get(image_url.geturl(), allow_redirects=True)
            mime_type = image_response.headers["Content-Type"]
            if mime_type not in VALID_IMAGE_MIMETYPES:
                return render_template(
                    "image-search.html",
                    nav_links=NAV_LINKS,
                    message_error=f"Invalid image format - {mime_type}. Valid types {VALID_IMAGE_MIMETYPES}",
                )
            image_content = image_response.content

    if image_content:
        search_query = None
        image_bytes = base64.b64encode(image_content)

    try:
        results, request_url, raw_request, raw_response = search_enterprise_search(
            project_id=PROJECT_ID,
            location=LOCATION,
            search_engine_id=IMAGE_SEARCH_DATASTORE_IDs[0]["datastore_id"],
            search_query=search_query,
            image_bytes=image_bytes,
            params={"search_type": 1},
        )
    except Exception as e:
        return render_template(
            "image-search.html",
            nav_links=NAV_LINKS,
            message_error=e.args[0],
        )

    return render_template(
        "image-search.html",
        nav_links=NAV_LINKS,
        message_success="Success",
        results=results,
        request_url=request_url,
        raw_request=raw_request,
        raw_response=raw_response,
    )


@app.route("/recommend", methods=["GET"])
def recommend() -> str:
    """
    Web Server, Homepage for Recommendations - Custom UI
    """
    return render_template(
        "recommend.html",
        nav_links=NAV_LINKS,
        documents=RECOMMENDATIONS_DOCUMENTS,
        attribution_token="",
    )


@app.route("/recommend_genappbuilder", methods=["POST"])
def recommend_genappbuilder() -> str:
    """
    Handle Recommend Gen App Builder Request
    """
    document_id = request.form.get("document_id", "")
    attribution_token = request.form.get("attribution_token", "")

    # Check if POST Request includes document id
    if not document_id:
        return render_template(
            "recommend.html",
            nav_links=NAV_LINKS,
            documents=RECOMMENDATIONS_DOCUMENTS,
            attribution_token=attribution_token,
            message_error="No document provided",
        )

    (
        results,
        attribution_token,
        request_url,
        raw_request,
        raw_response,
    ) = recommend_personalize(
        project_id=PROJECT_ID,
        location=LOCATION,
        datastore_id=RECOMMENDATIONS_DATASTORE_IDs[0]["datastore_id"],
        serving_config_id=RECOMMENDATIONS_DATASTORE_IDs[0]["engine_id"],
        document_id=document_id,
        attribution_token=attribution_token,
    )

    return render_template(
        "recommend.html",
        nav_links=NAV_LINKS,
        documents=RECOMMENDATIONS_DOCUMENTS,
        message_success=document_id,
        results=results,
        attribution_token=attribution_token,
        request_url=request_url,
        raw_request=raw_request,
        raw_response=raw_response,
    )


@app.route("/ekg", methods=["GET"])
def ekg() -> str:
    """
    Web Server, Homepage for EKG
    """

    return render_template("ekg.html", nav_links=NAV_LINKS, form_options=FORM_OPTIONS)


@app.route("/search_ekg", methods=["POST"])
def search_ekg() -> str:
    """
    Handle Search EKG Request
    """
    search_query = request.form.get("search_query", "")

    # Check if POST Request includes search query
    if not search_query:
        return render_template(
            "ekg.html",
            nav_links=NAV_LINKS,
            form_options=FORM_OPTIONS,
            message_error="No query provided",
        )

    languages = request.form.getlist("languages")
    form_types = request.form.get("types", "")

    types = re.split(r"[\s,]", form_types) if form_types else []

    entities, request_url, raw_request, raw_response = search_public_kg(
        project_id=PROJECT_ID,
        location=LOCATION,
        search_query=search_query,
        languages=languages,
        types=types,
    )

    return render_template(
        "ekg.html",
        nav_links=NAV_LINKS,
        form_options=FORM_OPTIONS,
        message_success=search_query,
        entities=entities,
        request_url=request_url,
        raw_request=raw_request,
        raw_response=raw_response,
    )


@app.errorhandler(Exception)
def handle_exception(ex: Exception):
    """
    Handle Application Exceptions
    """
    message_error = "An Unknown Error Occured"

    # Pass through HTTP errors
    if isinstance(ex, HTTPException):
        message_error = ex.get_description()
    elif isinstance(ex, ResourceExhausted):
        message_error = ex.message
    else:
        message_error = str(ex)

    return render_template(
        "search.html",
        form_options=FORM_OPTIONS,
        nav_links=NAV_LINKS,
        message_error=message_error,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
