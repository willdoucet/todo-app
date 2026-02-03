/**
 * MSW server for Node.js (used in tests).
 *
 * This creates a mock server that intercepts HTTP requests
 * and returns responses defined in handlers.js.
 */

import { setupServer } from 'msw/node'
import { handlers } from './handlers'

// Create the server with default handlers
export const server = setupServer(...handlers)
