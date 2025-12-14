# Form Components

Reusable form components with validation support for authentication and other forms.

## Components

### FormInput

Enhanced input component with validation integration.

```tsx
import { FormInput } from "@/components/forms";

// Basic usage
<FormInput
  name="email"
  label="Email Address"
  type="email"
  required
/>

// With error
<FormInput
  name="email"
  label="Email"
  type="email"
  error="Please enter a valid email"
/>

// With validation rules
<FormInput
  name="password"
  label="Password"
  type="password"
  rules={{
    required: "Password is required",
    minLength: { value: 8, message: "Password must be at least 8 characters" },
  }}
/>
```

### FormButton

Button optimized for form submissions with loading states.

```tsx
import { FormButton } from "@/components/forms";

<FormButton
  type="submit"
  isLoading={isSubmitting}
  loadingText="Submitting..."
  disabled={!isValid}
>
  Submit
</FormButton>
```

### FormError

Component for displaying form-level errors.

```tsx
import { FormError } from "@/components/forms";

<FormError
  error={formError}
  title="Submission Error"
  dismissible
  onDismiss={() => setFormError(null)}
/>
```

## Validation Schemas

Validation schemas are available in `@/lib/validation/schemas`:

```tsx
import {
  loginSchema,
  signupSchema,
  resetPasswordRequestSchema,
  validateForm,
  getFieldErrors,
} from "@/lib/validation/schemas";

// Validate form data
const result = validateForm(loginSchema, formData);
if (!result.success) {
  const errors = getFieldErrors(result.errors);
  // Handle errors
}
```

## Example: Login Form

```tsx
"use client";

import { useState } from "react";
import { FormInput, FormButton, FormError } from "@/components/forms";
import { loginSchema, validateForm, getFieldErrors } from "@/lib/validation/schemas";

export function LoginForm() {
  const [formData, setFormData] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrors({});
    setFormError(null);

    // Validate
    const result = validateForm(loginSchema, formData);
    if (!result.success) {
      setErrors(getFieldErrors(result.errors));
      return;
    }

    // Submit
    setIsSubmitting(true);
    try {
      // Your submission logic here
      await submitLogin(result.data);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Login failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <FormError error={formError} />
      
      <FormInput
        name="email"
        label="Email"
        type="email"
        value={formData.email}
        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
        error={errors.email}
      />

      <FormInput
        name="password"
        label="Password"
        type="password"
        value={formData.password}
        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
        error={errors.password}
      />

      <FormButton type="submit" isLoading={isSubmitting}>
        Sign In
      </FormButton>
    </form>
  );
}
```

## Features

- ✅ Client-side validation with Zod
- ✅ Error message display
- ✅ Loading states during submission
- ✅ Accessibility (labels, error associations, ARIA)
- ✅ TypeScript support
- ✅ Dark mode support
- ✅ Responsive design
