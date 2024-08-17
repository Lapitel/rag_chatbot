import pytest
from typing import List
from apps.index import get_loader, get_split_docs, load_embedding
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings

TEST_FILE_ID = "test"
def test_get_loader():
    loader = get_loader(TEST_FILE_ID)
    assert isinstance(loader, PyPDFLoader)

DATA = [Document(metadata={'source':'test', 'page': 0}, page_content="test")]
def test_get_split_docs():
    docs = get_split_docs(DATA)
    assert len(docs) > 0
    assert isinstance(docs, list)
    assert isinstance(docs[0], Document)
    assert isinstance(docs[0].page_content, str)

def test_load_embedding():
    embedding = load_embedding()
    assert isinstance(embedding, HuggingFaceEmbeddings)