import os
import logging

from typing import List
from config import (GLOBAL_LOG_LEVEL, UPLOAD_DIR, CONFIG_DATA, CHROMA_DATA_PATH)
from apps.utils import load_embedding
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

# log setting
log = logging.getLogger(__name__)
log.setLevel(GLOBAL_LOG_LEVEL)

def get_loader(file_id:str, extract_images:bool=False):
    file_path = os.path.join(UPLOAD_DIR, file_id)
    return PyPDFLoader(file_path, extract_images=extract_images)

def get_split_docs(data: List[Document], filename:str):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CONFIG_DATA['index']['chunk_size'],
        chunk_overlap=CONFIG_DATA['index']['chunk_overlap'],
        add_start_index=True,
    )
    docs = text_splitter.split_documents(data)
    # insert filename to split_docs
    [setattr(doc, 'page_content', f"{filename}\n{doc.page_content}") for doc in docs]

    return docs

def store_docs_in_vector_db(docs:List[Document], collection_name:str):
    Chroma.from_documents(
        documents=docs, 
        embedding=load_embedding(),
        collection_name=collection_name,
        persist_directory=CHROMA_DATA_PATH
    )