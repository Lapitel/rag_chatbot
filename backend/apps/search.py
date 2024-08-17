import logging
from config import (GLOBAL_LOG_LEVEL)
from typing import List

from utils import (
    get_last_user_message, 
    load_embedding, 
    load_sentence_transformer_rf, 
    get_collection_from_vector_store, 
    get_vector_store,
    get_contextualize_query,
    RerankCompressor
)
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import (
    ContextualCompressionRetriever,
    EnsembleRetriever,
)

# log setting
log = logging.getLogger(__name__)
log.setLevel(GLOBAL_LOG_LEVEL)

def query_doc_with_hybrid_search(
    collection_name: str,
    query: str,
    embedding_function,
    k: int,
    reranking_function,
    r: float,
):
    try:
        collection = get_collection_from_vector_store(collection_name=collection_name)
        documents = collection.get()  # get all documents

        bm25_retriever = BM25Retriever.from_texts(
            texts=documents.get("documents"),
            metadatas=documents.get("metadatas"),
        )
        bm25_retriever.k = k

        chroma_vector_store = get_vector_store(collection_name=collection_name)
        chroma_retriever = chroma_vector_store.as_retriever(search_kwargs={"k": k})

        ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, chroma_retriever], weights=[0.5, 0.5]
        )

        compressor = RerankCompressor(
            embedding_function=embedding_function,
            top_n=k,
            reranking_function=reranking_function,
            r_score=r,
        )

        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor, base_retriever=ensemble_retriever
        )

        result = compression_retriever.invoke(query)
        result = {
            "distances": [[d.metadata.get("score") for d in result]],
            "documents": [[d.page_content for d in result]],
            "metadatas": [[d.metadata for d in result]],
        }

        log.info(f"query_doc_with_hybrid_search:result {result}")
        
        return result
    except Exception as e:
        raise e
    
def merge_and_sort_query_results(query_results, k, reverse=False):
    # Initialize lists to store combined data
    combined_distances = []
    combined_documents = []
    combined_metadatas = []

    for data in query_results:
        combined_distances.extend(data["distances"][0])
        combined_documents.extend(data["documents"][0])
        combined_metadatas.extend(data["metadatas"][0])

    # Create a list of tuples (distance, document, metadata)
    combined = list(zip(combined_distances, combined_documents, combined_metadatas))

    # Sort the list based on distances
    combined.sort(key=lambda x: x[0], reverse=reverse)

    # We don't have anything :-(
    if not combined:
        sorted_distances = []
        sorted_documents = []
        sorted_metadatas = []
    else:
        # Unzip the sorted list
        sorted_distances, sorted_documents, sorted_metadatas = zip(*combined)

        # Slicing the lists to include only k elements
        sorted_distances = list(sorted_distances)[:k]
        sorted_documents = list(sorted_documents)[:k]
        sorted_metadatas = list(sorted_metadatas)[:k]

    # Create the output dictionary
    result = {
        "distances": [sorted_distances],
        "documents": [sorted_documents],
        "metadatas": [sorted_metadatas],
    }

    return result

def query_collection_with_hybrid_search(
    collection_names: List[str],
    query: str,
    embedding_function,
    k: int,
    reranking_function,
    r: float,
):
    results = []
    for collection_name in collection_names:
        try:
            result = query_doc_with_hybrid_search(
                collection_name=collection_name,
                query=query,
                embedding_function=embedding_function,
                k=k,
                reranking_function=reranking_function,
                r=r,
            )
            results.append(result)
        except:
            pass
    return merge_and_sort_query_results(results, k=k, reverse=True)

def get_rag_context(file_infos, messages, k, r, llm):
    query = get_last_user_message(messages)
    history = messages[:-1]
    if history:
        rag_query = get_contextualize_query(llm, query, history)

    extracted_collections = []
    relevant_contexts = []

    for file_info in file_infos:
        context = None

        collection_names = file_info.file_id
        collection_names = set(collection_names).difference(extracted_collections)
        if not collection_names:
            log.debug(f"skipping {file_info.name} as it has already been extracted")
            continue

        try:
            context = query_collection_with_hybrid_search(
                        collection_names=collection_names,
                        query=rag_query,
                        embedding=load_embedding(),
                        k=k,
                        reranking=load_sentence_transformer_rf(),
                        r=r,
                    )
        except Exception as e:
            log.exception(e)
            context = None

        if context:
            relevant_contexts.append({**context, "source": file_info.name})

        extracted_collections.extend(collection_names)

        contexts = []
    citations = []

    for context in relevant_contexts:
        try:
            if "documents" in context:
                contexts.append(
                    "\n\n".join(
                        [text for text in context["documents"][0] if text is not None]
                    )
                )

                if "metadatas" in context:
                    citations.append(
                        {
                            "source": context["source"],
                            "document": context["documents"][0],
                            "metadata": context["metadatas"][0],
                        }
                    )
        except Exception as e:
            log.exception(e)

    return contexts, citations