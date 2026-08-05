import { getUploadStatus, uploadChunk } from "@/lib/api";

const CHUNK_SIZE = 64 * 1024;

/**
 * Split `blob` into fixed-size chunks and upload sequentially, tracking
 * offset so a dropped connection can resume from `/media/status` instead
 * of re-sending everything (§4.1 M2, §5: "a completed recording is never
 * lost to a network failure").
 */
export async function uploadBlobChunked(
  sessionId: string,
  blob: Blob,
  onProgress?: (bytesSent: number, totalBytes: number) => void,
): Promise<void> {
  const total = blob.size;
  let offset = 0;

  try {
    const status = await getUploadStatus(sessionId);
    offset = status.bytes_received;
  } catch {
    offset = 0;
  }

  while (offset < total) {
    const chunk = blob.slice(offset, Math.min(offset + CHUNK_SIZE, total));
    const result = await uploadChunk(sessionId, offset, chunk);
    offset = result.bytes_received;
    onProgress?.(offset, total);
  }
}
