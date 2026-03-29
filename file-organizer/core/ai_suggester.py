"""AI-powered file category suggestion module."""

import json
import re

from google import genai
from google.genai import types
from google.genai import errors as genai_errors

from core import FileInfo, CategorySuggestion


class AIError(Exception):
    """Custom exception for AI-related errors with a user-friendly message."""

    def __init__(self, message: str, user_message: str):
        super().__init__(message)
        self.user_message = user_message


SYSTEM_INSTRUCTION = (
    "You are a file organization assistant. Analyze the provided file list "
    "(extension counts + sample filenames) and suggest 3-8 logical folder "
    "categories.\n\n"
    "Use the sample filenames to understand context — for example, if you see "
    "'Invoice_March.pdf' and 'Tax_Return.pdf', create a Finance category for "
    ".pdf files matching those patterns, separate from 'Ebook_Python.pdf' "
    "which belongs in Books.\n\n"
    "Respond with JSON in this exact format:\n"
    '{"categories": [\n'
    '  {"folder_name": "Finance", "description": "Invoices, receipts and tax documents", '
    '"extensions": [".pdf", ".xlsx"], "keywords": ["invoice", "receipt", "tax", "budget", "payroll", "expense", "bank", "payment"]},\n'
    '  ...\n'
    "]}\n\n"
    "Rules:\n"
    "- Use simple English folder names (e.g. Finance, Photos, Music, Code)\n"
    "- 'keywords' are lowercase words found in filenames that indicate the category\n"
    "- An extension can appear in multiple categories if keywords distinguish them\n"
    '- Always include an "Other" category for miscellaneous files\n'
    "- Only output valid JSON, no additional text"
)


class AISuggester:
    """Uses Gemini to suggest file organization categories."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash-lite"):
        self.model_name = model
        self._client = genai.Client(api_key=api_key)

    def suggest_categories(
        self, file_summary: str, files: list[FileInfo]
    ) -> list[CategorySuggestion]:
        """Suggest categories for the given files using AI.

        Makes an API call with the file summary, parses the response into
        CategorySuggestion objects. Retries once on JSON parse failure.
        """
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.3,
        )

        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=file_summary,
                config=config,
            )
            response_text = response.text

            try:
                return self._parse_response(response_text, files)
            except (json.JSONDecodeError, KeyError, ValueError):
                # Retry once with an extra instruction to return valid JSON
                retry_config = types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.1,
                )
                retry_response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=f"{file_summary}\n\nYou MUST respond with valid JSON only. No markdown, no explanation.",
                    config=retry_config,
                )
                return self._parse_response(retry_response.text, files)

        except genai_errors.ClientError as e:
            if hasattr(e, "code") and e.code in (401, 403):
                raise AIError(
                    f"Gemini authentication failed: {e}",
                    "Invalid API key. Please check your Gemini API key and try again.",
                )
            if hasattr(e, "status") and e.status in ("UNAUTHENTICATED", "PERMISSION_DENIED"):
                raise AIError(
                    f"Gemini authentication failed: {e}",
                    "Invalid API key. Please check your Gemini API key and try again.",
                )
            raise AIError(
                f"Gemini client error: {e}",
                f"AI service error: {e}",
            )
        except genai_errors.ServerError as e:
            raise AIError(
                f"Gemini server error: {e}",
                "Could not connect to AI service. Please check your internet "
                "connection and try again.",
            )
        except Exception as e:
            raise AIError(
                f"Gemini error: {type(e).__name__}: {e}",
                f"Error ({type(e).__name__}): {e}",
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

        # Build lookup structures: extension+keyword -> category
        category_info: dict[str, str] = {}
        # Each entry: (extensions_set, keywords_set, folder_name)
        rules: list[tuple[set, set, str]] = []

        for cat in categories_data:
            folder_name = cat["folder_name"]
            category_info[folder_name] = cat.get("description", "")
            exts = {e.lower() if e.startswith(".") else f".{e}".lower() for e in cat.get("extensions", [])}
            keywords = {k.lower() for k in cat.get("keywords", [])}
            rules.append((exts, keywords, folder_name))

        def assign_file(file: FileInfo) -> str:
            ext = file.extension.lower()
            name_lower = file.name.lower()
            # First pass: keyword match within matching extension
            for exts, keywords, folder in rules:
                if folder == "Other":
                    continue
                if ext in exts and keywords and any(kw in name_lower for kw in keywords):
                    return folder
            # Second pass: extension-only match (no keywords defined or no keyword hit)
            for exts, keywords, folder in rules:
                if folder == "Other":
                    continue
                if ext in exts and not keywords:
                    return folder
            # Third pass: extension match ignoring keywords
            for exts, keywords, folder in rules:
                if folder == "Other":
                    continue
                if ext in exts:
                    return folder
            return "Other"

        category_files: dict[str, list[FileInfo]] = {}
        for file in files:
            folder = assign_file(file)
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

        ext_to_category: dict[str, str] = {}
        for category_name, extensions in category_map.items():
            for ext in extensions:
                ext_to_category[ext] = category_name

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
