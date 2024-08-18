import pytest
from typing import List
from apps.index import get_loader, get_split_docs, store_docs_in_vector_db
from apps.utils import get_collection_from_vector_store
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

def test_store_docs_in_vector_db():
    collection_name = 'test'
    store_docs_in_vector_db(DATA, collection_name)

    collection = get_collection_from_vector_store(collection_name=collection_name)
    documents = collection.get()
    print(documents.get("documents")) 

    # assert documents[0]