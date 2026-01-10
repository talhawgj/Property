import { defineAuth } from '@aws-amplify/backend';

/**
 * Define and configure your auth resource
 * @see https://docs.amplify.aws/gen2/build-a-backend/auth
 */
export const auth = defineAuth({
  loginWith: {
    email: true,
  },
  userAttributes: {
    email: {
      required: true,
      mutable: false,
    },
    // Custom attribute to store user role (admin or user)
    'custom:role': {
      dataType: 'String',
      mutable: true,
    },
  },
  accountRecovery: 'EMAIL_ONLY',
  multifactor: {
    mode: 'OPTIONAL',
    sms: false,
    totp: true,
  },
});
