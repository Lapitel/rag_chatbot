import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import os

from typing import List
from config import (UPLOAD_DIR, CONFIG_DATA)
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings

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

def load_embedding():
    model_name = CONFIG_DATA['rag']['embedding_model']
    return HuggingFaceEmbeddings(model_name=model_name)

def store_docs_in_vector_db(docs:List[Document], embeddings:HuggingFaceEmbeddings, file_id:str):
    pass

if __name__ == "__main__":
    store_docs_in_vector_db(
        [Document(metadata={'source':'test', 'page': 0}, page_content="test")],
        load_embedding(),
        "test"
    )