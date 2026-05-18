"""Transactional email templates for account verification and recovery."""

from html import escape


def _email_layout(*, title: str, eyebrow: str, intro: str, content_html: str, footer_note: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>{escape(title)}</title>
      </head>
      <body style="margin:0;padding:0;background:#f3f6fb;font-family:Segoe UI,Arial,sans-serif;color:#0f172a;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3f6fb;padding:32px 16px;">
          <tr>
            <td align="center">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;background:#ffffff;border-radius:28px;overflow:hidden;box-shadow:0 24px 64px rgba(15,23,42,0.12);">
                <tr>
                  <td style="padding:40px 40px 24px;background:linear-gradient(135deg,#0f172a 0%,#1e3a8a 60%,#0f766e 100%);color:#ffffff;">
                    <div style="display:inline-block;padding:8px 14px;border-radius:999px;background:rgba(255,255,255,0.14);font-size:12px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;">{escape(eyebrow)}</div>
                    <h1 style="margin:20px 0 12px;font-size:30px;line-height:1.2;">{escape(title)}</h1>
                    <p style="margin:0;font-size:16px;line-height:1.7;color:rgba(255,255,255,0.88);">{escape(intro)}</p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:32px 40px 12px;">
                    {content_html}
                  </td>
                </tr>
                <tr>
                  <td style="padding:8px 40px 40px;font-size:13px;line-height:1.7;color:#475569;">
                    <p style="margin:0;">{escape(footer_note)}</p>
                    <p style="margin:18px 0 0;">InsightPro Security Team</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """.strip()


def render_email_verification_email(*, full_name: str, company_name: str, otp_code: str, expires_minutes: int) -> tuple[str, str]:
    name = escape(full_name or "there")
    company = escape(company_name or "your workspace")
    otp = "".join(
        f"<span style=\"display:inline-block;min-width:42px;margin:0 6px;padding:12px 0;border-radius:14px;background:#e2e8f0;font-size:28px;font-weight:800;color:#0f172a;text-align:center;\">{escape(digit)}</span>"
        for digit in otp_code
    )
    content_html = f"""
      <p style="margin:0 0 18px;font-size:16px;line-height:1.7;color:#1e293b;">Hi {name},</p>
      <p style="margin:0 0 24px;font-size:16px;line-height:1.7;color:#1e293b;">Your admin workspace for <strong>{company}</strong> has been created. Use the verification code below to activate your account and finish signing in.</p>
      <div style="margin:0 0 24px;padding:24px;border:1px solid #dbeafe;border-radius:24px;background:linear-gradient(135deg,#eff6ff 0%,#ecfeff 100%);text-align:center;">
        <p style="margin:0 0 14px;font-size:13px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#1d4ed8;">Verification code</p>
        <div>{otp}</div>
        <p style="margin:16px 0 0;font-size:14px;color:#334155;">This code expires in <strong>{expires_minutes} minutes</strong>.</p>
      </div>
      <p style="margin:0;font-size:15px;line-height:1.7;color:#475569;">If you did not request this account, you can safely ignore this email.</p>
    """
    text = (
        f"Hi {full_name or 'there'},\n\n"
        f"Your InsightPro admin workspace for {company_name or 'your workspace'} has been created. "
        f"Use this verification code to activate your account: {otp_code}\n\n"
        f"This code expires in {expires_minutes} minutes.\n\n"
        "If you did not request this account, you can ignore this email."
    )
    html = _email_layout(
        title="Verify your InsightPro account",
        eyebrow="Email Verification",
        intro="Complete your sign-up securely before accessing the dashboard.",
        content_html=content_html,
        footer_note="For security reasons, never share this code with anyone. InsightPro support will never ask for it.",
    )
    return html, text


def render_password_reset_email(*, full_name: str, reset_url: str, expires_minutes: int) -> tuple[str, str]:
    name = escape(full_name or "there")
    safe_url = escape(reset_url)
    content_html = f"""
      <p style="margin:0 0 18px;font-size:16px;line-height:1.7;color:#1e293b;">Hi {name},</p>
      <p style="margin:0 0 24px;font-size:16px;line-height:1.7;color:#1e293b;">We received a request to reset your InsightPro password. Use the secure button below to choose a new password.</p>
      <div style="margin:0 0 24px;padding:24px;border:1px solid #e2e8f0;border-radius:24px;background:#f8fafc;text-align:center;">
        <a href="{safe_url}" style="display:inline-block;padding:14px 24px;border-radius:14px;background:#0f766e;color:#ffffff;font-size:15px;font-weight:700;text-decoration:none;">Reset password</a>
        <p style="margin:16px 0 0;font-size:14px;color:#475569;line-height:1.6;">This link expires in <strong>{expires_minutes} minutes</strong>.</p>
      </div>
      <p style="margin:0 0 12px;font-size:14px;line-height:1.7;color:#475569;">If the button does not open, copy and paste this URL into your browser:</p>
      <p style="margin:0;font-size:13px;line-height:1.8;word-break:break-all;color:#1d4ed8;">{safe_url}</p>
    """
    text = (
        f"Hi {full_name or 'there'},\n\n"
        "We received a request to reset your InsightPro password. "
        f"Use the link below to choose a new password. The link expires in {expires_minutes} minutes.\n\n"
        f"{reset_url}\n\n"
        "If you did not request a password reset, you can ignore this email."
    )
    html = _email_layout(
        title="Reset your InsightPro password",
        eyebrow="Password Recovery",
        intro="Secure access to your workspace starts with a fresh password.",
        content_html=content_html,
        footer_note="If you did not request a password reset, no further action is required and your account remains protected.",
    )
    return html, text