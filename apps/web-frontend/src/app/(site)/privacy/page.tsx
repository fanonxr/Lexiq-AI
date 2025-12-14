import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "Privacy Policy for LexiqAI - Enterprise Voice Orchestration for the Legal Industry",
};

/**
 * Privacy Policy Page
 */
export default function PrivacyPage() {
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
        Privacy Policy
      </h1>

      <div className="prose prose-zinc dark:prose-invert max-w-none">
        <p className="text-sm text-black dark:text-zinc-100">
          Last updated: {new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
        </p>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            1. Introduction
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            LexiqAI ("we," "our," or "us") is committed to protecting your privacy. This Privacy Policy
            explains how we collect, use, disclose, and safeguard your information when you use our
            Service. Please read this policy carefully to understand our practices regarding your data.
          </p>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            2. Information We Collect
          </h2>
          <h3 className="mb-3 text-xl font-semibold text-black dark:text-white">
            2.1 Information You Provide
          </h3>
          <p className="mb-4 text-black dark:text-zinc-100">
            We collect information that you provide directly to us, including:
          </p>
          <ul className="mb-4 ml-6 list-disc space-y-2 text-black dark:text-zinc-100">
            <li>Account registration information (name, email address)</li>
            <li>Profile information and preferences</li>
            <li>Payment and billing information</li>
            <li>Communications with us (support requests, feedback)</li>
          </ul>

          <h3 className="mb-3 mt-6 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
            2.2 Automatically Collected Information
          </h3>
          <p className="mb-4 text-black dark:text-zinc-100">
            When you use our Service, we automatically collect certain information, including:
          </p>
          <ul className="mb-4 ml-6 list-disc space-y-2 text-black dark:text-zinc-100">
            <li>Device information (IP address, browser type, operating system)</li>
            <li>Usage data (pages visited, features used, time spent)</li>
            <li>Call recordings and transcripts (as part of our voice orchestration service)</li>
            <li>Log files and analytics data</li>
          </ul>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            3. How We Use Your Information
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            We use the information we collect to:
          </p>
          <ul className="mb-4 ml-6 list-disc space-y-2 text-black dark:text-zinc-100">
            <li>Provide, maintain, and improve our Service</li>
            <li>Process transactions and send related information</li>
            <li>Send technical notices, updates, and support messages</li>
            <li>Respond to your comments, questions, and requests</li>
            <li>Monitor and analyze usage patterns and trends</li>
            <li>Detect, prevent, and address technical issues or security threats</li>
            <li>Comply with legal obligations</li>
          </ul>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            4. Information Sharing and Disclosure
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            We do not sell your personal information. We may share your information in the following circumstances:
          </p>
          <ul className="mb-4 ml-6 list-disc space-y-2 text-black dark:text-zinc-100">
            <li>
              <strong>Service Providers:</strong> With third-party vendors who perform services on our behalf
              (e.g., payment processing, data analytics, cloud hosting)
            </li>
            <li>
              <strong>Legal Requirements:</strong> When required by law, court order, or government regulation
            </li>
            <li>
              <strong>Business Transfers:</strong> In connection with a merger, acquisition, or sale of assets
            </li>
            <li>
              <strong>With Your Consent:</strong> When you explicitly authorize us to share your information
            </li>
          </ul>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            5. Data Security
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            We implement appropriate technical and organizational security measures to protect your
            information against unauthorized access, alteration, disclosure, or destruction. However,
            no method of transmission over the Internet or electronic storage is 100% secure, and we
            cannot guarantee absolute security.
          </p>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            6. Data Retention
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            We retain your personal information for as long as necessary to fulfill the purposes
            outlined in this Privacy Policy, unless a longer retention period is required or
            permitted by law. When we no longer need your information, we will securely delete or
            anonymize it.
          </p>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            7. Your Rights and Choices
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            Depending on your location, you may have certain rights regarding your personal information:
          </p>
          <ul className="mb-4 ml-6 list-disc space-y-2 text-black dark:text-zinc-100">
            <li>
              <strong>Access:</strong> Request access to your personal information
            </li>
            <li>
              <strong>Correction:</strong> Request correction of inaccurate or incomplete information
            </li>
            <li>
              <strong>Deletion:</strong> Request deletion of your personal information
            </li>
            <li>
              <strong>Portability:</strong> Request transfer of your data to another service
            </li>
            <li>
              <strong>Opt-out:</strong> Opt-out of certain data processing activities
            </li>
          </ul>
          <p className="mb-4 text-black dark:text-zinc-100">
            To exercise these rights, please contact us using the information provided in Section 11.
          </p>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            8. Cookies and Tracking Technologies
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            We use cookies and similar tracking technologies to track activity on our Service and
            store certain information. You can instruct your browser to refuse all cookies or to
            indicate when a cookie is being sent. However, if you do not accept cookies, you may
            not be able to use some portions of our Service.
          </p>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            9. Third-Party Services
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            Our Service may contain links to third-party websites or services. We are not responsible
            for the privacy practices of these third parties. We encourage you to read the privacy
            policies of any third-party services you visit.
          </p>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            10. Children's Privacy
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            Our Service is not intended for children under the age of 18. We do not knowingly collect
            personal information from children. If you become aware that a child has provided us with
            personal information, please contact us immediately.
          </p>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            11. Changes to This Privacy Policy
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            We may update this Privacy Policy from time to time. We will notify you of any changes
            by posting the new Privacy Policy on this page and updating the "Last updated" date.
            You are advised to review this Privacy Policy periodically for any changes.
          </p>
        </section>

        <section className="mt-8">
          <h2 className="mb-4 text-2xl font-semibold text-black dark:text-white">
            12. Contact Us
          </h2>
          <p className="mb-4 text-black dark:text-zinc-100">
            If you have any questions about this Privacy Policy or our data practices, please contact us at:
          </p>
          <p className="mb-4 text-black dark:text-zinc-100">
            Email: privacy@lexiqai.com<br />
            Address: [Your Company Address]
          </p>
        </section>
      </div>
    </div>
  );
}
