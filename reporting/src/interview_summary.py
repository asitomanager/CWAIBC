"""
Module for summarizing interview responses.

This module provides functionalities to save and retrieve interview summaries.

Classes:
- InterviewSummary: Handles the saving and retrieval of interview summaries.
"""

import json
import os

from docx import Document
from google.genai.types import Part
from weasyprint import CSS, HTML

from commons import FileName, logger
from reporting.src.formatter import Formatter
from reporting.src.gemini_connector import GeminiConnector
from reporting.src.prompt import ANALYSIS_PROMPT
from user_management import Candidate

FILES_DIR = os.environ.get("FILES_DIR")


class InterviewSummary:
    """
    Generate an interview summary for the given candidate ID.

    The summary will contain the analysis of the candidate's speech, grammar,
    and facial expressions during the interview. The analysis will be generated
    by the Gemini AI model.

    The summary will be saved as an HTML and PDF file in the results directory
    specified in the environment variable `FILES_DIR`.

    Args:
        candidate_id (int): The ID of the candidate for whom to generate the
            summary.

    Attributes:
        results_dir (str): The directory where the summary files will be saved.
        __gemini_connector (GeminiConnector): The Gemini AI model connector.

    Methods:
        __call__() : Generate the summary and save it to the results directory.
        __prompt_content(dict): Generate the prompt content for the Gemini AI
            model.
        save_response(str): Save the response from the Gemini AI model to the
            results directory.
    """

    def __init__(self, candidate_id: int, qa_dir: str):
        logger.info("Initializing Interview Summary...")
        self.qa_dir = qa_dir
        self.results_dir = os.path.join(FILES_DIR, str(candidate_id))
        os.makedirs(self.results_dir, exist_ok=True)
        self.__gemini_connector = GeminiConnector()
        self.__candidate = Candidate(user_id=candidate_id)

    def __call__(self):
        logger.info("Generating analysis...")
        file_paths = {
            "video": os.path.join(self.results_dir, f"{FileName.VIDEO.value}.webm"),
            "transcript": os.path.join(
                self.results_dir, f"{FileName.TRANSCRIPT.value}.txt"
            ),
            "qa": self.__convert_docx_to_txt(
                os.path.join(self.qa_dir, f"{FileName.QUESTION_BANK.value}.docx"),
            ),
        }
        for file_path in file_paths.values():
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

        prompt_content = self.__prompt_content(file_paths)
        response = self.__gemini_connector.get_response(prompt_content)
        self.__save_response(response)

    def __convert_docx_to_txt(self, docx_file_path: str) -> str:
        doc = Document(docx_file_path)
        txt_file_path = os.path.join(self.qa_dir, f"{FileName.QUESTION_BANK.value}.txt")
        if not os.path.exists(txt_file_path):
            logger.info("Converting %s to TXT", docx_file_path)
            with open(txt_file_path, "w", encoding="utf-8") as f:
                for paragraph in doc.paragraphs:
                    f.write(paragraph.text + "\n")
        return txt_file_path

    def __prompt_content(self, file_paths: dict):
        logger.info("Preparing Analysis prompt ...")

        # Upload the video, transcript, and Q&A files
        video_file_uri = self.__gemini_connector.upload_file_to_gcs(
            file_paths["video"], self.__candidate.user_id
        )
        transcript_file_uri = self.__gemini_connector.upload_file_to_gcs(
            file_paths["transcript"], self.__candidate.user_id
        )
        qa_file_uri = self.__gemini_connector.upload_file_to_gcs(
            file_paths["qa"], self.__candidate.user_id
        )
        logger.debug(
            "video_file: %s, transcript_file: %s, qa_file: %s",
            video_file_uri,
            transcript_file_uri,
            qa_file_uri,
        )
        logger.info("Files uploaded to GCS.")

        return [
            ANALYSIS_PROMPT,
            "\n- Interview Transcript: ",
            Part.from_uri(file_uri=transcript_file_uri, mime_type="text/plain"),
            "\n- Q&A Document: ",
            Part.from_uri(file_uri=qa_file_uri, mime_type="text/plain"),
            "\n- Candidate Video: ",
            Part.from_uri(file_uri=video_file_uri, mime_type="video/webm"),
        ]

    def __save_response(self, response: str):
        json_response = json.loads(response)
        logger.info("Saving response...")
        with open(
            os.path.join(self.results_dir, "response.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(json_response, f, indent=4)
        formatter = Formatter(json_response, self.__candidate)
        html_content = formatter()

        output_html_file = os.path.join(self.results_dir, "analysis.html")
        with open(output_html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info("HTML file saved as %s", output_html_file)

        # Convert HTML to PDF
        output_pdf_file = os.path.join(self.results_dir, "analysis.pdf")
        css = CSS(string="@page { size: A4 landscape; }")
        # css = CSS(string="@page { size: A4 portrait; }")
        HTML(string=html_content).write_pdf(output_pdf_file, stylesheets=[css])
        logger.info("PDF file saved as %s", output_pdf_file)


if __name__ == "__main__":
    from commons import create_log_file

    create_log_file("interview_summary")
    InterviewSummary(
        77, "/home/ravi/Documents/CareerWingsAI/assets/PEGA/SOFTWARE ENGINEER"
    )()
    # interview_summary = InterviewSummary(12, "")
    # with open(
    #     os.path.join(interview_summary.results_dir, "response.json"),
    #     "r",
    #     encoding="utf-8",
    # ) as analysis_fh:
    #     input_text = analysis_fh.read()
    # interview_summary._InterviewSummary__save_response(input_text)
