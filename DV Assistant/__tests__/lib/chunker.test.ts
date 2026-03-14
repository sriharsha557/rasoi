import { splitIntoChunks, inferDocType } from '@/lib/chunker';
import fc from 'fast-check';

describe('Document Chunker', () => {
  describe('splitIntoChunks', () => {
    it('should create at least one chunk for any document', () => {
      const text = 'This is a test document with some content.';
      const chunks = splitIntoChunks(text);
      
      expect(chunks.length).toBeGreaterThanOrEqual(1);
    });

    it('should create chunks within size bounds', () => {
      const text = 'Lorem ipsum dolor sit amet, '.repeat(100);
      const chunks = splitIntoChunks(text);
      
      chunks.forEach((chunk) => {
        expect(chunk.content.length).toBeGreaterThanOrEqual(40);
        expect(chunk.content.length).toBeLessThanOrEqual(1000);
      });
    });

    it('should assign sequential chunk indices', () => {
      const text = 'Test content. '.repeat(200);
      const chunks = splitIntoChunks(text);
      
      chunks.forEach((chunk, idx) => {
        expect(chunk.chunk_index).toBe(idx);
      });
    });

    it('should include metadata in chunks', () => {
      const text = 'Test document content.';
      const metadata = { document_id: 'test-123', filename: 'test.pdf' };
      const chunks = splitIntoChunks(text, metadata);
      
      chunks.forEach((chunk) => {
        expect(chunk.metadata).toMatchObject(metadata);
      });
    });
  });

  describe('inferDocType', () => {
    it('should infer hub type from filename', () => {
      expect(inferDocType('customer_hub.pdf')).toBe('hub');
      expect(inferDocType('HUB_definition.md')).toBe('hub');
    });

    it('should infer link type from filename', () => {
      expect(inferDocType('customer_order_link.pdf')).toBe('link');
      expect(inferDocType('LINK_patterns.md')).toBe('link');
    });

    it('should infer satellite type from filename', () => {
      expect(inferDocType('customer_satellite.pdf')).toBe('satellite');
      expect(inferDocType('sat_details.md')).toBe('satellite');
    });

    it('should infer methodology type from filename', () => {
      expect(inferDocType('dv_methodology.pdf')).toBe('methodology');
      expect(inferDocType('standards_guide.md')).toBe('methodology');
    });

    it('should default to general for unknown types', () => {
      expect(inferDocType('random_document.pdf')).toBe('general');
      expect(inferDocType('notes.txt')).toBe('general');
    });
  });
});

// Feature: data-vault-knowledge-assistant, Property 11: Minimum Chunk Count
describe('Property: Minimum Chunk Count', () => {
  it('should create at least one chunk for any document with meaningful content', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 40, maxLength: 10000 }).filter(s => s.trim().length >= 40),
        (text) => {
          const chunks = splitIntoChunks(text);
          expect(chunks.length).toBeGreaterThanOrEqual(1);
        }
      ),
      { numRuns: 100 }
    );
  });
});
