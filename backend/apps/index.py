import os
from typing import List
from config import (UPLOAD_DIR, CONFIG_DATA)
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

def get_loader(file_id: str):
    file_path = os.path.join(UPLOAD_DIR, file_id)
    return PyPDFLoader(file_path, extract_images=True)

def get_split_docs(data: List[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CONFIG_DATA['index']['chunk_size'],
        chunk_overlap=CONFIG_DATA['index']['chunk_overlap'],
        add_start_index=True,
    )

    return text_splitter.split_documents(data)