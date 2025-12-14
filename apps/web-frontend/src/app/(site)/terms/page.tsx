import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "Terms of Service for LexiqAI - Enterprise Voice Orchestration for the Legal Industry",
};

/**
 * Terms of Service Page
 */
export default function TermsPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8 bg-white dark:bg-zinc-950">
      <div className="mb-8">
        <Link
          href="/"
          className="text-sm font-medium text-black hover:text-zinc-700 dark:text-zinc-100 dark:hover:text-zinc-300"
        >
          ← Back to Home
        </Link>
      </div>

      <h1 className="mb-8 text-4xl font-bold text-black dark:text-white">
        Terms of Service
      </h1>

      <div className="prose prose-zinc dark:prose-invert max-w-none">
        <p className="text-sm text-black dark:text-zinc-100">
          Last updated: {new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
        </p>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            1. Agreement to Terms
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            By accessing or using LexiqAI ("Service"), you agree to be bound by these Terms of Service ("Terms").
            If you disagree with any part of these terms, then you may not access the Service.
          </p>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            2. Description of Service
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            LexiqAI provides enterprise voice orchestration services for the legal industry, including
            AI-powered voice assistants, call management, and integration with legal CRM systems.
          </p>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            3. User Accounts
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            To access certain features of the Service, you must register for an account. You agree to:
          </p>
          <ul className="mb-4 ml-6 list-disc space-y-2 text-black dark:text-zinc-100">
            <li>Provide accurate, current, and complete information during registration</li>
            <li>Maintain and update your account information to keep it accurate</li>
            <li>Maintain the security of your account credentials</li>
            <li>Accept responsibility for all activities that occur under your account</li>
            <li>Notify us immediately of any unauthorized use of your account</li>
          </ul>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            4. Acceptable Use
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            You agree not to:
          </p>
          <ul className="mb-4 ml-6 list-disc space-y-2 text-black dark:text-zinc-100">
            <li>Use the Service for any illegal purpose or in violation of any laws</li>
            <li>Violate or infringe upon the rights of others</li>
            <li>Transmit any harmful, offensive, or inappropriate content</li>
            <li>Attempt to gain unauthorized access to the Service or related systems</li>
            <li>Interfere with or disrupt the Service or servers</li>
            <li>Use automated systems to access the Service without authorization</li>
          </ul>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            5. Intellectual Property
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            The Service and its original content, features, and functionality are owned by LexiqAI and
            are protected by international copyright, trademark, patent, trade secret, and other
            intellectual property laws.
          </p>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            6. Payment and Billing
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            If you purchase a subscription or other paid features:
          </p>
          <ul className="mb-4 ml-6 list-disc space-y-2 text-black dark:text-zinc-100">
            <li>You agree to pay all fees associated with your subscription</li>
            <li>Fees are billed in advance on a recurring basis</li>
            <li>All fees are non-refundable unless otherwise stated</li>
            <li>We reserve the right to change our pricing with 30 days notice</li>
          </ul>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            7. Termination
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            We may terminate or suspend your account and access to the Service immediately, without
            prior notice, for conduct that we believe violates these Terms or is harmful to other users,
            us, or third parties, or for any other reason.
          </p>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            8. Disclaimer of Warranties
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            The Service is provided "as is" and "as available" without warranties of any kind,
            either express or implied. We do not warrant that the Service will be uninterrupted,
            secure, or error-free.
          </p>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            9. Limitation of Liability
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            To the maximum extent permitted by law, LexiqAI shall not be liable for any indirect,
            incidental, special, consequential, or punitive damages, or any loss of profits or
            revenues, whether incurred directly or indirectly, or any loss of data, use, goodwill,
            or other intangible losses.
          </p>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            10. Changes to Terms
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            We reserve the right to modify these Terms at any time. We will notify users of any
            material changes by posting the new Terms on this page and updating the "Last updated"
            date. Your continued use of the Service after such changes constitutes acceptance of
            the new Terms.
          </p>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            11. Contact Information
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            If you have any questions about these Terms, please contact us at:
          </p>
          <p className="mb-4 text-black dark:text-zinc-100">
            Email: legal@lexiqai.com<br />
            Address: [Your Company Address]
          </p>
        </section>
      </div>
    </div>
  );
}
