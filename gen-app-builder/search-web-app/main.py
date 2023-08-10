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
    WIDGET_CONFIGS
)
from genappbuilder_utils import (
    list_documents,
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
        "name": "Search + GenAI | Rail Safety",
        "icon": "science",
    },
    {
        "link": "/widget", 
        "name": "Search | Rail Safety | Widget", 
        "icon": "widgets"
    },
    {
        "link": "/search",
        "name": "Search | Rail Safety | Custom",
        "icon": "build",
    }
]

@app.route("/widget", methods=["GET"])
def widget() -> str:
    return render_template(
        "widget.html",
        nav_links=NAV_LINKS,
        search_engine_options=WIDGET_CONFIGS,
    )

@app.route("/search", methods=["GET"])
def search() -> str:
    return render_template(
        "search.html",
        nav_links=NAV_LINKS,
    )

@app.route("/search_genappbuilder", methods=["POST"])
def search_genappbuilder() -> str:
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

@app.route("/", methods=["GET"])
@app.route("/search-llm", methods=["GET"])
def searchllm() -> str:
    return render_template(
        "search-llm.html",
        nav_links=NAV_LINKS,
    )

@app.route("/search-llm_genappbuilder", methods=["POST"])
def searchllm_genappbuilder() -> str:
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
        model=CUSTOM_UI_LLM_DATASTORE_IDS[0]["model"],
        search_query=search_query,
    )

    return render_template(
        "search-llm.html",
        nav_links=NAV_LINKS,
        message_success=search_query,
        results=results
    )

@app.errorhandler(Exception)
def handle_exception(ex: Exception):
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
