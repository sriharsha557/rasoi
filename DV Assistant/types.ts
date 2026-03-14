// Core type definitions for Data Vault Knowledge Assistant

export type DocType = 'hub' | 'link' | 'satellite' | 'methodology' | 'pit_bridge' | 'general';

export interface Document {
  id: string;
  filename: string;
  doc_type: DocType;
  file_size: number;
  chunk_count: number;
  status: 'processing' | 'ready' | 'error';
  created_at: string;
}

export interface Chunk {
  id: string;
  document_id: string;
  content: string;
  embedding: number[];
  chunk_index: number;
  doc_type: DocType;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface MatchedChunk {
  id: string;
  content: string;
  doc_type: string;
  metadata: Record<string, unknown>;
  filename: string;
  similarity: number;
}

export interface Source {
  filename: string;
  doc_type?: string;
  similarity: number;
  excerpt: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: Source[];
  isStreaming?: boolean;
}

// API Request/Response types
export interface QueryRequest {
  query: string;
  doc_type_filter?: string | null;
  top_k?: number;
  chat_history?: Array<{ role: string; content: string }>;
}

export interface IngestResponse {
  success: boolean;
  document_id?: string;
  chunk_count?: number;
  error?: string;
}

export interface ErrorResponse {
  error: string;
  code?: string;
  details?: string;
}
