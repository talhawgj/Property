import { defineBackend } from '@aws-amplify/backend';
import { auth } from './auth/resource.js';

/**
 * @see https://docs.amplify.aws/react/build-a-backend/ to add storage, functions, and more
 */
const backend = defineBackend({
  auth,
});
