export interface GoogleFormItem {
  id: string;
  name: string;
  createdTime?: string;
  modifiedTime?: string;
  webViewLink?: string;
}

export interface FormDetails {
  formId: string;
  info: {
    title: string;
    description?: string;
    documentTitle?: string;
  };
  items?: any[];
  responderUri?: string;
}

export interface FormResponseItem {
  responseId: string;
  createTime: string;
  lastSubmittedTime: string;
  answers?: Record<string, { answers?: { value?: string }[] }>;
}

// 1. List Google Forms using Drive Files API
export async function listGoogleForms(accessToken: string): Promise<GoogleFormItem[]> {
  try {
    const q = "mimeType='application/vnd.google-apps.form' and trashed=false";
    const url = `https://www.googleapis.com/drive/v3/files?q=${encodeURIComponent(
      q
    )}&fields=files(id,name,createdTime,modifiedTime,webViewLink)&orderBy=modifiedTime desc&pageSize=20`;

    const res = await fetch(url, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || `Failed to list forms: ${res.status}`);
    }

    const data = await res.json();
    return data.files || [];
  } catch (error: any) {
    console.error('List Google Forms error:', error);
    throw error;
  }
}

// 2. Get Form Structure and Details
export async function getGoogleForm(accessToken: string, formId: string): Promise<FormDetails> {
  const safeFormId = encodeURIComponent(formId.trim());
  const res = await fetch(`https://forms.googleapis.com/v1/forms/${safeFormId}`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || `Failed to get form ${formId}: ${res.status}`);
  }

  return res.json();
}

// 3. Get Form Responses
export async function getGoogleFormResponses(
  accessToken: string,
  formId: string
): Promise<FormResponseItem[]> {
  const safeFormId = encodeURIComponent(formId.trim());
  const res = await fetch(`https://forms.googleapis.com/v1/forms/${safeFormId}/responses`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || `Failed to get responses: ${res.status}`);
  }

  const data = await res.json();
  return data.responses || [];
}

// 4. Create a New Google Form with questions (DevOps template support)
export async function createGoogleForm(
  accessToken: string,
  title: string,
  documentTitle: string,
  questions: { title: string; required?: boolean; type?: 'text' | 'choice'; options?: string[] }[]
): Promise<FormDetails> {
  // Step A: Create empty form
  const createRes = await fetch('https://forms.googleapis.com/v1/forms', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      info: {
        title,
        documentTitle,
      },
    }),
  });

  if (!createRes.ok) {
    const err = await createRes.json().catch(() => ({}));
    throw new Error(err.error?.message || `Failed to create form: ${createRes.status}`);
  }

  const newForm: FormDetails = await createRes.json();
  const formId = newForm.formId;

  // Step B: If questions are provided, add them via batchUpdate
  if (questions && questions.length > 0) {
    const requests = questions.map((q, index) => {
      if (q.type === 'choice' && q.options) {
        return {
          createItem: {
            item: {
              title: q.title,
              questionItem: {
                question: {
                  required: q.required ?? true,
                  choiceQuestion: {
                    type: 'RADIO',
                    options: q.options.map((opt) => ({ value: opt })),
                  },
                },
              },
            },
            location: { index },
          },
        };
      }
      return {
        createItem: {
          item: {
            title: q.title,
            questionItem: {
              question: {
                required: q.required ?? true,
                textQuestion: {
                  paragraph: false,
                },
              },
            },
          },
          location: { index },
        },
      };
    });

    const updateRes = await fetch(
      `https://forms.googleapis.com/v1/forms/${encodeURIComponent(formId)}:batchUpdate`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ requests }),
      }
    );

    if (!updateRes.ok) {
      console.warn('Form created but failed to populate items:', await updateRes.text());
    }
  }

  return newForm;
}

// 5. Delete Form (via Drive API)
export async function deleteGoogleForm(accessToken: string, fileId: string): Promise<void> {
  const safeId = encodeURIComponent(fileId.trim());
  const res = await fetch(`https://www.googleapis.com/drive/v3/files/${safeId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!res.ok && res.status !== 204) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || `Failed to delete form: ${res.status}`);
  }
}
