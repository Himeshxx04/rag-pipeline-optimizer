import os


def save_extracted_text(doc_folder: str, text: str) -> str:
    """
    Saves extracted text to disk inside the document folder.
    Returns the full path of the saved text file.
    """
    text_path = os.path.join(doc_folder, "extracted.txt")
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(text)
    return text_path
