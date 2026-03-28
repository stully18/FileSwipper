"""AI-powered file category suggestion module."""

import json
import re

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from core import FileInfo, CategorySuggestion


class AIError(Exception):
    """Custom exception for AI-related errors with a user-friendly message."""

    def __init__(self, message: str, user_message: str):
        super().__init__(message)
        self.user_message = user_message


class AISuggester:
    """Uses Gemini to suggest file organization categories."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.model_name = model
        genai.configure(api_key=api_key)
        system_message = (
            "You are a file organization assistant. Analyze the provided list of "
            "files and suggest 3-8 logical folder categories to organize them.\n\n"
            "Respond with JSON in this exact format:\n"
            '{"categories": [\n'
            '  {"folder_name": "Documents", "description": "Text documents and '
            'spreadsheets", "extensions": [".pdf", ".docx", ".txt"]},\n'
            '  ...\n'
            "]}\n\n"
            "Rules:\n"
            "- Use simple English folder names (e.g. Documents, Images, Music)\n"
            "- Every common file extension must appear in exactly one category\n"
            '- Always include an "Other" category for miscellaneous files\n'
            "- Only output valid JSON, no additional text"
        )
        self._model = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_message,
            generation_config={"temperature": 0.3},
        )

    def suggest_categories(
        self, file_summary: str, files: list[FileInfo]
    ) -> list[CategorySuggestion]:
        """Suggest categories for the given files using AI.

        Makes an API call with the file summary, parses the response into
        CategorySuggestion objects. Retries once on JSON parse failure.
        """
        try:
            chat = self._model.start_chat()
            response = chat.send_message(file_summary)
            response_text = response.text

            try:
                return self._parse_response(response_text, files)
            except (json.JSONDecodeError, KeyError, ValueError):
                # Retry once with an extra instruction to return valid JSON
                retry_model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=self._model._system_instruction,
                    generation_config={"temperature": 0.1},
                )
                retry_chat = retry_model.start_chat()
                retry_chat.send_message(file_summary)
                retry_response = retry_chat.send_message("Respond with valid JSON only.")
                return self._parse_response(retry_response.text, files)

        except google_exceptions.PermissionDenied:
            raise AIError(
                "Gemini authentication failed.",
                "Invalid API key. Please check your Gemini API key and try again.",
            )
        except google_exceptions.Unauthenticated:
            raise AIError(
                "Gemini authentication failed.",
                "Invalid API key. Please check your Gemini API key and try again.",
            )
        except (google_exceptions.ServiceUnavailable, google_exceptions.DeadlineExceeded):
            raise AIError(
                "Gemini API connection error.",
                "Could not connect to AI service. Please check your internet "
                "connection and try again.",
            )
        except google_exceptions.GoogleAPICallError as e:
            raise AIError(
                f"Gemini API error: {e}",
                "An unexpected AI service error occurred. Please try again later.",
            )

    def _parse_response(
        self, response_text: str, files: list[FileInfo]
    ) -> list[CategorySuggestion]:
        """Parse the AI response and assign files to categories.

        Tries json.loads first, then attempts to extract JSON from markdown
        code fences. Performs a second pass to ensure every file is assigned
        to exactly one category based on its extension.
        """
        # Try direct JSON parse first
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            # Try extracting from markdown code fences
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", response_text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
            else:
                raise

        categories_data = data["categories"]

        # Build extension-to-category mapping
        ext_to_category: dict[str, str] = {}
        category_info: dict[str, str] = {}

        for cat in categories_data:
            folder_name = cat["folder_name"]
            description = cat.get("description", "")
            category_info[folder_name] = description
            for ext in cat.get("extensions", []):
                ext_lower = ext.lower() if ext.startswith(".") else f".{ext}".lower()
                ext_to_category[ext_lower] = folder_name

        # CRITICAL second pass: iterate ALL files and assign each to a category
        category_files: dict[str, list[FileInfo]] = {}

        for file in files:
            ext = file.extension.lower()
            folder = ext_to_category.get(ext, "Other")
            if folder not in category_files:
                category_files[folder] = []
            category_files[folder].append(file)

        # Ensure "Other" has a description if it was created during assignment
        if "Other" not in category_info:
            category_info["Other"] = "Miscellaneous files"

        # Build CategorySuggestion list (only categories that have files)
        suggestions = []
        for folder_name, file_list in category_files.items():
            description = category_info.get(folder_name, "")
            suggestions.append(
                CategorySuggestion(
                    folder_name=folder_name,
                    description=description,
                    files=file_list,
                )
            )

        return suggestions

    @staticmethod
    def fallback_categories(files: list[FileInfo]) -> list[CategorySuggestion]:
        """Group files into standard categories by extension, without AI.

        Returns only categories that contain at least one file.
        """
        category_map = {
            "Documents": {
                ".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt",
                ".xls", ".xlsx", ".csv", ".ppt", ".pptx",
            },
            "Images": {
                ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg",
                ".webp", ".tiff", ".ico",
            },
            "Audio": {
                ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a",
            },
            "Video": {
                ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm",
            },
            "Archives": {
                ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".deb", ".rpm",
            },
            "Code": {
                ".py", ".js", ".ts", ".html", ".css", ".java", ".c", ".cpp",
                ".h", ".rs", ".go", ".sh", ".json", ".xml", ".yaml", ".yml",
                ".sql",
            },
        }

        # Invert: extension -> category name
        ext_to_category: dict[str, str] = {}
        for category_name, extensions in category_map.items():
            for ext in extensions:
                ext_to_category[ext] = category_name

        # Group files
        grouped: dict[str, list[FileInfo]] = {}
        for file in files:
            ext = file.extension.lower()
            category_name = ext_to_category.get(ext, "Other")
            if category_name not in grouped:
                grouped[category_name] = []
            grouped[category_name].append(file)

        descriptions = {
            "Documents": "Text documents, spreadsheets, and presentations",
            "Images": "Image and graphic files",
            "Audio": "Music and audio files",
            "Video": "Video and movie files",
            "Archives": "Compressed and archive files",
            "Code": "Source code and data files",
            "Other": "Miscellaneous files",
        }

        return [
            CategorySuggestion(
                folder_name=name,
                description=descriptions.get(name, ""),
                files=file_list,
            )
            for name, file_list in grouped.items()
        ]
