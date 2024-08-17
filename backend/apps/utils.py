import os
import logging
import operator
from typing import Optional, List, Any, Sequence
from config import (GLOBAL_LOG_LEVEL, CONFIG_DATA, CHROMA_DATA_PATH, SENTENCE_TRANSFORMERS_HOME)

import sentence_transformers
from huggingface_hub import snapshot_download

import chromadb
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import BaseDocumentCompressor, Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

# log setting
log = logging.getLogger(__name__)
log.setLevel(GLOBAL_LOG_LEVEL)

def load_embedding():
    model_name = CONFIG_DATA['rag']['embedding_model']
    return HuggingFaceEmbeddings(model_name=model_name)

def get_model_path(model: str, update_model: bool = False):
    # Construct huggingface_hub kwargs with local_files_only to return the snapshot path
    cache_dir = SENTENCE_TRANSFORMERS_HOME

    local_files_only = not update_model

    snapshot_kwargs = {
        "cache_dir": cache_dir,
        "local_files_only": local_files_only,
    }

    log.debug(f"model: {model}")
    log.debug(f"snapshot_kwargs: {snapshot_kwargs}")

    # Inspiration from upstream sentence_transformers
    if (
        os.path.exists(model)
        or ("\\" in model or model.count("/") > 1)
        and local_files_only
    ):
        # If fully qualified path exists, return input, else set repo_id
        return model
    elif "/" not in model:
        # Set valid repo_id for model short-name
        model = "sentence-transformers" + "/" + model

    snapshot_kwargs["repo_id"] = model

    # Attempt to query the huggingface_hub library to determine the local path and/or to update
    try:
        model_repo_path = snapshot_download(**snapshot_kwargs)
        log.debug(f"model_repo_path: {model_repo_path}")
        return model_repo_path
    except Exception as e:
        log.exception(f"Cannot determine model snapshot path: {e}")
        return model

def load_sentence_transformer_rf():
    return sentence_transformers.CrossEncoder(
        get_model_path(CONFIG_DATA['rag']['reranking_model']),
        device="cuda",
        trust_remote_code=True,
    )

def get_collection_from_vector_store(collection_name:str):
    persistent_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
    collection = persistent_client.get_or_create_collection(collection_name)

    return collection

def get_vector_store(collection_name:str):
    persistent_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)

    vector_store = Chroma(
        client=persistent_client,
        collection_name=collection_name,
        embedding_function=load_embedding(),
    )

    return vector_store

def get_last_user_message_item(messages: List[dict]) -> Optional[dict]:
    for message in reversed(messages):
        if message["role"] == "user":
            return message
    return None

def get_content_from_message(message: dict) -> Optional[str]:
    if isinstance(message["content"], list):
        for item in message["content"]:
            if item["type"] == "text":
                return item["text"]
    else:
        return message["content"]
    return None

def get_last_user_message(messages: List[dict]) -> Optional[str]:
    message = get_last_user_message_item(messages)
    if message is None:
        return None

    return get_content_from_message(message)

def get_contextualize_query(llm, query, history):
    contextualize_q_system_prompt = """Given a chat history and the latest user question \
    which might reference context in the chat history, formulate a standalone question \
    which can be understood without the chat history. Do NOT answer the question, \
    just reformulate it if needed and otherwise return it as is."""
    contextualize_q_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("chat_history"),
            ("human", "{question}"),
        ]
    )

    return {"question": query, "chat_history": history} | contextualize_q_prompt | llm | StrOutputParser()

class RerankCompressor(BaseDocumentCompressor):
    embedding_function: Any
    top_n: int
    reranking_function: Any
    r_score: float

    class Config:
        extra = 'forbid'
        arbitrary_types_allowed = True

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
    ) -> Sequence[Document]:
        reranking = self.reranking_function is not None

        if reranking:
            scores = self.reranking_function.predict(
                [(query, doc.page_content) for doc in documents]
            )
        else:
            from sentence_transformers import util

            query_embedding = self.embedding_function(query)
            document_embedding = self.embedding_function(
                [doc.page_content for doc in documents]
            )
            scores = util.cos_sim(query_embedding, document_embedding)[0]

        docs_with_scores = list(zip(documents, scores.tolist()))
        if self.r_score:
            docs_with_scores = [
                (d, s) for d, s in docs_with_scores if s >= self.r_score
            ]

        result = sorted(docs_with_scores, key=operator.itemgetter(1), reverse=True)
        final_results = []
        for doc, doc_score in result[: self.top_n]:
            metadata = doc.metadata
            metadata["score"] = doc_score
            doc = Document(
                page_content=doc.page_content,
                metadata=metadata,
            )
            final_results.append(doc)
        return final_results
