"""
Connects to the Gemini API.

Provides methods for authentication and data retrieval.
"""

import json
import os
from typing import List

from dotenv import load_dotenv
from google import genai
from google.cloud import storage
from google.genai import types

from commons import ConfigLoader, logger

load_dotenv(override=True)

FILES_DIR = os.environ.get("FILES_DIR")


class GeminiConnector:
    """
    A class used to connect to the Gemini 1.5 model and upload files to GCS.

    Attributes:
        client (genai.Client): The client for the Gemini 1.5 model.
        __bucket_name (str): The name of the GCS bucket to upload files to.
    """

    __CONFIG_PATH = os.path.join("commons", "config.jsonc")

    def __init__(self):
        self.__config = ConfigLoader.get_config(self.__CONFIG_PATH)
        self.client = genai.Client(vertexai=True, project=self.__config["gcp_project"])
        self.__bucket_name = self.__config["gcp_bucket"]

    def upload_file_to_gcs(self, file_path: str, prefix: str):
        """Uploads a file to a specified GCS bucket and returns the file URL."""
        logger.info("Uploading file: %s", file_path)
        storage_client = storage.Client()
        bucket = storage_client.bucket(self.__bucket_name)
        blob = bucket.blob(f"{prefix}_{os.path.basename(file_path)}")
        blob.chunk_size = 50 * 1024 * 1024  # 50 MB
        blob.upload_from_filename(file_path, timeout=600)
        return f"gs://{self.__bucket_name}/{prefix}_{os.path.basename(file_path)}"

    def get_response(self, contents: List[str]):
        """
        Calls the Gemini 1.5 Flash model to generate the analysis.

        Args:
            contents (List[str]): The contents of the prompt.

        Returns:
            str: The response from the model.
        """
        with open(
            os.path.join("reporting", "src", "response_schema.json"),
            "r",
            encoding="utf-8",
        ) as f:
            response_schema = json.load(f)
        generate_content_config = types.GenerateContentConfig(
            temperature=0,
            top_p=0.95,
            max_output_tokens=8192,
            response_mime_type="application/json",
            response_schema=response_schema,
            # response_modalities=["TEXT"],
        )
        logger.info("Fetching response...")
        response = self.client.models.generate_content(
            model=self.__config["analysis_model"],
            contents=contents,
            config=generate_content_config,
        )
        # No explicit close() needed; the client is stateless.
        return response.text
