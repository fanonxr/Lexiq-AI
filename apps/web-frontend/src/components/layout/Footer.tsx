"use client";

/**
 * Footer Component
 * 
 * Marketing site footer with links and company information.
 * 
 * @example
 * ```tsx
 * <Footer />
 * ```
 */

import Link from "next/link";

export interface FooterProps {
  /**
   * Additional footer links
   */
  links?: Array<{ label: string; href: string }>;
}

/**
 * Marketing site footer
 */
export function Footer({ links }: FooterProps) {
  const defaultLinks = {
    product: [
      { label: "Features", href: "/#features" },
      { label: "Pricing", href: "/pricing" },
      { label: "Documentation", href: "/docs" },
    ],
    company: [
      { label: "About", href: "/about" },
      { label: "Blog", href: "/blog" },
      { label: "Careers", href: "/careers" },
    ],
    legal: [
      { label: "Privacy", href: "/privacy" },
      { label: "Terms", href: "/terms" },
      { label: "Security", href: "/security" },
    ],
  };

  const footerLinks = links
    ? { product: links, company: [], legal: [] }
    : defaultLinks;

  const currentYear = new Date().getFullYear();

  return (
    <footer
      className="border-t border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950"
      role="contentinfo"
    >
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-4">
          {/* Brand */}
          <div className="col-span-1 md:col-span-1">
            <Link
              href="/"
              className="text-xl font-bold text-zinc-900 dark:text-zinc-100"
              aria-label="LexiqAI Home"
            >
              LexiqAI
            </Link>
            <p className="mt-4 text-sm text-zinc-600 dark:text-zinc-400">
              AI-powered voice orchestration for law firms.
            </p>
          </div>

          {/* Product Links */}
          <div>
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              Product
            </h3>
            <ul className="mt-4 space-y-3">
              {footerLinks.product.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Company Links */}
          {footerLinks.company.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
                Company
              </h3>
              <ul className="mt-4 space-y-3">
                {footerLinks.company.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Legal Links */}
          <div>
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              Legal
            </h3>
            <ul className="mt-4 space-y-3">
              {footerLinks.legal.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Copyright */}
        <div className="mt-8 border-t border-zinc-200 pt-8 dark:border-zinc-800">
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            © {currentYear} LexiqAI. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
