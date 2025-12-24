"""
Document Ingestion Module

This module handles loading, processing, and ingesting documents
into the vector store for later retrieval.

Features:
- Multiple file format support (txt, md, json, jsonl)
- Automatic chunking with metadata preservation
- Batch processing for efficiency
- Deduplication support

Usage:
    from src.ingestion import DocumentIngester
    
    ingester = DocumentIngester()
    ingester.ingest_file("data/faq.jsonl")
    ingester.ingest_directory("data/documents/")
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Iterator, Union
from dataclasses import dataclass, field

from src.core.embeddings import EmbeddingProvider, AzureEmbeddingProvider
from src.core.vectorstore import VectorStore, ChromaVectorStore
from src.pipeline.chunker import TextChunker, Chunk
from src.config import settings
from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Document:
    """
    Represents a document to be ingested.
    
    Attributes:
        text: Document text content
        metadata: Document metadata (source, title, etc.)
        id: Optional unique identifier
    """
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[str] = None


@dataclass
class IngestionResult:
    """
    Result of an ingestion operation.
    
    Attributes:
        documents_processed: Number of documents processed
        chunks_created: Number of chunks created
        chunks_ingested: Number of chunks added to store
        errors: List of any errors encountered
    """
    documents_processed: int = 0
    chunks_created: int = 0
    chunks_ingested: int = 0
    errors: List[str] = field(default_factory=list)
    
    @property
    def success(self) -> bool:
        """Check if ingestion was successful."""
        return len(self.errors) == 0


class DocumentLoader:
    """
    Loads documents from various file formats.
    
    Supported formats:
    - .txt: Plain text files
    - .md: Markdown files
    - .json: JSON files (expects "text" or "content" field)
    - .jsonl: JSON Lines (one JSON object per line)
    """
    
    SUPPORTED_EXTENSIONS = {".txt", ".md", ".json", ".jsonl"}
    
    def load_file(self, filepath: Union[str, Path]) -> List[Document]:
        """
        Load documents from a file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            List of Document objects
        """
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format: {path.suffix}")
        
        logger.info(f"Loading file: {path}")
        
        if path.suffix.lower() in {".txt", ".md"}:
            return self._load_text_file(path)
        elif path.suffix.lower() == ".json":
            return self._load_json_file(path)
        elif path.suffix.lower() == ".jsonl":
            return self._load_jsonl_file(path)
        
        return []
    
    def _load_text_file(self, path: Path) -> List[Document]:
        """Load a plain text or markdown file."""
        text = path.read_text(encoding="utf-8", errors="ignore")
        return [Document(
            text=text,
            metadata={"source": path.name, "type": "text"}
        )]
    
    def _load_json_file(self, path: Path) -> List[Document]:
        """Load a JSON file."""
        content = json.loads(path.read_text(encoding="utf-8"))
        
        documents = []
        
        if isinstance(content, list):
            # Array of documents
            for i, item in enumerate(content):
                doc = self._parse_json_item(item, path.name, i)
                if doc:
                    documents.append(doc)
        elif isinstance(content, dict):
            # Single document
            doc = self._parse_json_item(content, path.name, 0)
            if doc:
                documents.append(doc)
        
        return documents
    
    def _load_jsonl_file(self, path: Path) -> List[Document]:
        """Load a JSON Lines file."""
        documents = []
        
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    doc = self._parse_json_item(item, path.name, i)
                    if doc:
                        documents.append(doc)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse line {i} in {path}: {e}")
        
        return documents
    
    def _parse_json_item(
        self,
        item: Dict[str, Any],
        source: str,
        index: int
    ) -> Optional[Document]:
        """Parse a JSON item into a Document."""
        # Prefer rich text fields first.
        # IMPORTANT: For FAQ-style entries we want to embed Question+Answer together,
        # not only one field.
        text_fields = ["text", "content", "body"]
        text = None

        for field in text_fields:
            if field in item and isinstance(item[field], str) and item[field].strip():
                text = item[field]
                break

        # FAQ style: concatenate question + answer when available
        if text is None and "question" in item and "answer" in item:
            q = str(item.get("question", "")).strip()
            a = str(item.get("answer", "")).strip()
            if q or a:
                text = f"Question: {q}\n\nAnswer: {a}".strip()

        # If we still don't have text, fall back to either question or answer alone
        if text is None and "question" in item and isinstance(item["question"], str):
            q = item["question"].strip()
            if q:
                text = q
        if text is None and "answer" in item and isinstance(item["answer"], str):
            a = item["answer"].strip()
            if a:
                text = a
        
        if not text:
            return None
        
        # Build metadata from remaining fields
        metadata = {"source": source, "index": index}
        for key, value in item.items():
            if key not in text_fields and isinstance(value, (str, int, float, bool)):
                metadata[key] = value
        
        return Document(text=text, metadata=metadata, id=item.get("id"))


class DocumentIngester:
    """
    Handles document ingestion into the vector store.
    
    Orchestrates:
    1. Loading documents from files
    2. Chunking documents
    3. Generating embeddings
    4. Storing in vector store
    
    Example:
        ingester = DocumentIngester()
        
        # Ingest a single file
        result = ingester.ingest_file("data/faq.jsonl")
        print(f"Ingested {result.chunks_ingested} chunks")
        
        # Ingest a directory
        result = ingester.ingest_directory("data/documents/")
    """
    
    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        vector_store: Optional[VectorStore] = None,
        chunker: Optional[TextChunker] = None
    ):
        """
        Initialize the document ingester.
        
        Args:
            embedding_provider: Provider for embeddings
            vector_store: Store for documents
            chunker: Text chunker for splitting
        """
        self.embedding_provider = embedding_provider or AzureEmbeddingProvider()
        self.vector_store = vector_store or ChromaVectorStore()
        self.chunker = chunker or TextChunker()
        self.loader = DocumentLoader()
        
        logger.info("Initialized DocumentIngester")
    
    def ingest_documents(
        self,
        documents: List[Document],
        batch_size: int = 64
    ) -> IngestionResult:
        """
        Ingest a list of documents.
        
        Args:
            documents: List of Document objects
            batch_size: Batch size for embedding
            
        Returns:
            IngestionResult with statistics
        """
        result = IngestionResult()
        
        # Chunk all documents
        all_chunks: List[Chunk] = []
        for doc in documents:
            try:
                chunks = self.chunker.chunk_text(doc.text, metadata=doc.metadata)
                all_chunks.extend(chunks)
                result.documents_processed += 1
            except Exception as e:
                logger.error(f"Failed to chunk document: {e}")
                result.errors.append(f"Chunking error: {str(e)}")
        
        result.chunks_created = len(all_chunks)
        
        if not all_chunks:
            return result
        
        # Process in batches
        for batch_start in range(0, len(all_chunks), batch_size):
            batch = all_chunks[batch_start:batch_start + batch_size]
            
            try:
                # Get texts and metadata
                texts = [c.text for c in batch]
                metadatas = [c.metadata for c in batch]
                ids = [c.id for c in batch]
                
                # Generate embeddings
                embeddings = self.embedding_provider.embed_batch(texts)
                
                # Add to vector store
                self.vector_store.add_documents(
                    texts=texts,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids
                )
                
                result.chunks_ingested += len(batch)
                logger.info(
                    f"Ingested batch {batch_start // batch_size + 1}: "
                    f"{len(batch)} chunks"
                )
                
            except Exception as e:
                logger.error(f"Failed to ingest batch: {e}")
                result.errors.append(f"Batch ingestion error: {str(e)}")
        
        return result
    
    def ingest_file(self, filepath: Union[str, Path]) -> IngestionResult:
        """
        Ingest documents from a file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            IngestionResult with statistics
        """
        try:
            documents = self.loader.load_file(filepath)
            logger.info(f"Loaded {len(documents)} documents from {filepath}")
            return self.ingest_documents(documents)
        except Exception as e:
            logger.error(f"Failed to ingest file {filepath}: {e}")
            result = IngestionResult()
            result.errors.append(f"File error: {str(e)}")
            return result
    
    def ingest_directory(
        self,
        directory: Union[str, Path],
        recursive: bool = True,
        extensions: Optional[List[str]] = None
    ) -> IngestionResult:
        """
        Ingest all documents from a directory.
        
        Args:
            directory: Path to directory
            recursive: Whether to process subdirectories
            extensions: File extensions to process (defaults to all supported)
            
        Returns:
            Combined IngestionResult
        """
        path = Path(directory)
        
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        extensions = extensions or list(DocumentLoader.SUPPORTED_EXTENSIONS)
        extensions = [ext if ext.startswith(".") else f".{ext}" for ext in extensions]
        
        # Find all files
        files = []
        pattern = "**/*" if recursive else "*"
        for ext in extensions:
            files.extend(path.glob(f"{pattern}{ext}"))
        
        logger.info(f"Found {len(files)} files in {directory}")
        
        # Ingest all files
        combined_result = IngestionResult()
        
        for file_path in files:
            result = self.ingest_file(file_path)
            combined_result.documents_processed += result.documents_processed
            combined_result.chunks_created += result.chunks_created
            combined_result.chunks_ingested += result.chunks_ingested
            combined_result.errors.extend(result.errors)
        
        return combined_result
    
    def ingest_text(
        self,
        text: str,
        source: str = "direct_input",
        metadata: Optional[Dict[str, Any]] = None
    ) -> IngestionResult:
        """
        Ingest raw text directly.
        
        Args:
            text: Text content to ingest
            source: Source identifier
            metadata: Additional metadata
            
        Returns:
            IngestionResult
        """
        meta = metadata or {}
        meta["source"] = source
        
        doc = Document(text=text, metadata=meta)
        return self.ingest_documents([doc])
    
    @property
    def document_count(self) -> int:
        """Get number of chunks in vector store."""
        return self.vector_store.count()
