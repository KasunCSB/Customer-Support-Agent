const messages: Record<string, string> = {
  'api.validation.email_required': 'Email is required.',
  'api.validation.email_code_required': 'Email and code are required.',
  'api.validation.message_required': 'Message is required.',
  'api.validation.subject_description_required': 'Subject and description are required.',
  'api.validation.service_code_required': 'Service code is required.',
  'api.error.backend_failed': 'The service is unavailable. Please try again.',
  'api.error.internal': 'Something went wrong. Please try again.',
  'api.error.no_response_body': 'No response body received.',
  'api.error.unauthorized': 'Please log in or verify before continuing.',
};

export function uiMsg(key: string): string {
  return messages[key] || key;
}
