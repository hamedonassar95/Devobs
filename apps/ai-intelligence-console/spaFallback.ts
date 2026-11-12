import path from 'node:path';
import type { RequestHandler } from 'express';

/** Serve the production single-page app for any route not matched by a static file. */
export function createSpaFallbackHandler(distDirectory: string): RequestHandler {
  return (_request, response) => {
    response.sendFile(path.resolve(distDirectory, 'index.html'), (error) => {
      if (error) response.status(404).end();
    });
  };
}
