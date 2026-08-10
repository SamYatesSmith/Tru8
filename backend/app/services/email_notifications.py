"""
Email notification service using Resend API
"""

import html
import logging
from typing import Dict, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailNotificationService:
    def __init__(self):
        self.api_key = settings.RESEND_API_KEY
        self.from_address = settings.EMAIL_FROM_ADDRESS
        self.from_name = settings.EMAIL_FROM_NAME
        self.enabled = settings.ENABLE_EMAIL_NOTIFICATIONS
        self._resend = None

    def _get_resend(self):
        """Lazy load resend module"""
        if self._resend is None:
            try:
                import resend

                if self.api_key:
                    resend.api_key = self.api_key
                self._resend = resend
            except ImportError:
                logger.warning(
                    "Resend package not installed - email notifications disabled"
                )
                return None
        return self._resend

    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Send an email via Resend API (synchronous)"""
        if not self.enabled or not self.api_key:
            logger.info(f"Email notifications disabled, skipping email to {to_email}")
            return False

        resend = self._get_resend()
        if resend is None:
            return False

        try:
            params = {
                "from": f"{self.from_name} <{self.from_address}>",
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }
            if headers:
                params["headers"] = headers

            response = resend.Emails.send(params)
            email_id = (
                response.get("id")
                if isinstance(response, dict)
                else getattr(response, "id", "unknown")
            )
            logger.info(f"Email sent successfully to {to_email}, id: {email_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    # ========== SYNC METHODS (for Celery workers) ==========

    def send_check_completed_email_sync(
        self,
        user_id: str,
        check_id: str,
        claims_count: int,
        # ClaimMap parameters
        entry_mode: Optional[str] = None,
        selected_claims_count: int = 0,
        input_url: Optional[str] = None,
        input_title: Optional[str] = None,
        total_sources: int = 0,
        claims_analyzed: Optional[list] = None,
    ) -> bool:
        """
        Send email when an evidence research check is completed (SYNC version for Celery workers).
        Uses synchronous database session to avoid event loop conflicts.
        """
        if not self.enabled or not self.api_key:
            logger.info("Email notifications disabled")
            return False

        try:
            from app.core.database import sync_session
            from app.models.user import User

            with sync_session() as session:
                user = session.get(User, user_id)

                if not user:
                    logger.info(f"User {user_id} not found")
                    return False

                if (
                    not user.email_notifications_enabled
                    or not user.email_check_completion
                ):
                    logger.info(f"User {user_id} has check completion emails disabled")
                    return False

                subject = f"Your evidence landscape is ready \u2014 {claims_count} claim{'s' if claims_count != 1 else ''} analysed"

                html_content = self._render_check_completed_template(
                    check_id=check_id,
                    claims_count=claims_count,
                    entry_mode=entry_mode,
                    selected_claims_count=selected_claims_count,
                    input_url=input_url,
                    input_title=input_title,
                    total_sources=total_sources,
                    claims_analyzed=claims_analyzed or [],
                )

                return self._send_email(
                    to_email=user.email, subject=subject, html_content=html_content
                )

        except Exception as e:
            logger.error(
                f"Failed to send check completion email to user {user_id}: {e}"
            )
            return False

    def send_check_failed_email_sync(
        self, user_id: str, check_id: str, error_message: str
    ) -> bool:
        """
        Send email when an evidence research check fails (SYNC version for Celery workers).
        Uses synchronous database session to avoid event loop conflicts.
        """
        if not self.enabled or not self.api_key:
            logger.info("Email notifications disabled")
            return False

        try:
            from app.core.database import sync_session
            from app.models.user import User

            with sync_session() as session:
                user = session.get(User, user_id)

                if not user:
                    logger.info(f"User {user_id} not found")
                    return False

                if not user.email_notifications_enabled or not user.email_check_failure:
                    logger.info(f"User {user_id} has check failure emails disabled")
                    return False

                subject = (
                    "We hit a wall \u2014 your analysis couldn\u2019t be completed"
                )

                html_content = self._render_check_failed_template(
                    check_id=check_id, error_message=error_message
                )

                return self._send_email(
                    to_email=user.email, subject=subject, html_content=html_content
                )

        except Exception as e:
            logger.error(f"Failed to send check failed email to user {user_id}: {e}")
            return False

    # ========== ASYNC METHODS (for API endpoints) ==========

    async def send_check_completed_email(
        self,
        user_id: str,
        check_id: str,
        claims_count: int,
        # ClaimMap parameters
        entry_mode: Optional[str] = None,
        selected_claims_count: int = 0,
        input_url: Optional[str] = None,
        input_title: Optional[str] = None,
        total_sources: int = 0,
        claims_analyzed: Optional[list] = None,
    ) -> bool:
        """Send email when an evidence research check is completed (async wrapper)"""
        # For now, delegate to sync version - Resend SDK is synchronous
        return self.send_check_completed_email_sync(
            user_id=user_id,
            check_id=check_id,
            claims_count=claims_count,
            entry_mode=entry_mode,
            selected_claims_count=selected_claims_count,
            input_url=input_url,
            input_title=input_title,
            total_sources=total_sources,
            claims_analyzed=claims_analyzed,
        )

    async def send_check_failed_email(
        self, user_id: str, check_id: str, error_message: str
    ) -> bool:
        """Send email when an evidence research check fails (async wrapper)"""
        return self.send_check_failed_email_sync(
            user_id=user_id, check_id=check_id, error_message=error_message
        )

    # ========== LIFECYCLE (FUNNEL) EMAILS ==========
    #
    # Eligibility, exactly-once claiming and dispatch live in
    # app/services/lifecycle_emails.py. These methods only render and send —
    # they deliberately do NOT re-check preferences or markers, because doing
    # so in two places is how the two copies drift apart.

    def _lifecycle_headers(self) -> Dict[str, str]:
        """Unsubscribe affordance for lifecycle mail.

        mailto rather than a one-click URL: a one-click unsubscribe needs an
        unauthenticated tokened endpoint, deliberately deferred until volume
        justifies a new public surface (see the design doc).
        """
        return {"List-Unsubscribe": f"<mailto:{self.from_address}?subject=unsubscribe>"}

    def send_welcome_email_sync(
        self, to_email: str, name: Optional[str] = None
    ) -> bool:
        """Send the welcome email. Caller has already claimed the marker."""
        return self._send_email(
            to_email=to_email,
            subject="Welcome to Tru8 — your three free checks are ready",
            html_content=self._render_welcome_template(name=name),
            headers=self._lifecycle_headers(),
        )

    def send_trial_exhausted_email_sync(
        self, to_email: str, checks_run: int = 0, sources_organised: int = 0
    ) -> bool:
        """Send the trial-exhausted email. Caller has already claimed the marker."""
        return self._send_email(
            to_email=to_email,
            subject="You’ve used your three free checks",
            html_content=self._render_trial_exhausted_template(
                checks_run=checks_run, sources_organised=sources_organised
            ),
            headers=self._lifecycle_headers(),
        )

    # ========== EMAIL TEMPLATES ==========

    def _render_check_completed_template(
        self,
        check_id: str,
        claims_count: int,
        entry_mode: Optional[str] = None,
        selected_claims_count: int = 0,
        input_url: Optional[str] = None,
        input_title: Optional[str] = None,
        total_sources: int = 0,
        claims_analyzed: Optional[list] = None,
    ) -> str:
        """Render check completion email HTML"""
        frontend_url = settings.FRONTEND_URL

        # Build source info section
        source_section = ""
        if input_url or input_title:
            display_title = input_title or input_url
            source_section = f"""
          <!-- Source Info -->
          <div style="border: 1px solid #E5E7EB; padding: 12px 16px; margin-bottom: 24px;">
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 9px; text-transform: uppercase; letter-spacing: 0.2em; color: #9CA3AF; margin-bottom: 4px;">Analysed</div>
            <div style="color: #111827; font-size: 14px; font-weight: 500;">{display_title}</div>
          </div>
"""

        # Build analysed claims section with orientation lines
        claims_section = ""
        if claims_analyzed and len(claims_analyzed) > 0:
            claims_html = ""
            for idx, claim in enumerate(claims_analyzed[:3]):  # Max 3 claims
                claim_text = claim.get("text", "")
                if len(claim_text) > 120:
                    claim_text = claim_text[:117] + "..."
                element_count = claim.get("element_count", 0)
                orientation = claim.get("orientation", "")
                rank_label = str(idx + 1).zfill(2)

                orientation_html = ""
                if orientation:
                    orientation_html = f"""
                <div style="color: #6B7280; font-size: 12px; margin-top: 6px; line-height: 1.5;">{orientation}</div>
"""

                claims_html += f"""
            <div style="border: 1px solid #E5E7EB; padding: 12px 16px; margin-bottom: 8px;">
              <div style="display: flex; align-items: baseline; gap: 8px; margin-bottom: 4px;">
                <span style="font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #D1D5DB;">{rank_label}</span>
                <span style="color: #111827; font-size: 13px;">{claim_text}</span>
              </div>
              <div style="font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #9CA3AF;">{element_count} element{'s' if element_count != 1 else ''} analysed</div>{orientation_html}
            </div>
"""

            claims_section = f"""
          <!-- Claims Analysed -->
          <div style="margin-bottom: 24px;">
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 10px; text-transform: uppercase; letter-spacing: 0.25em; color: #9CA3AF; margin-bottom: 8px;">Claims Analysed</div>
            {claims_html}
          </div>
"""

        # Summary stats
        analyzed_count = selected_claims_count or claims_count
        mode_label = "article" if entry_mode == "article" else "focused"

        return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #F9FAFB; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; padding: 32px 16px;">
    <tr>
      <td>
        <!-- Header: Logo -->
        <div style="text-align: center; margin-bottom: 32px; padding-bottom: 24px; border-bottom: 1px solid #E5E7EB;">
          <img src="{frontend_url}/icon-192.png" alt="Tru8" width="48" height="48" style="display: inline-block;" />
        </div>

        <!-- Main Card -->
        <div style="background: #FFFFFF; border: 1px solid #E5E7EB; padding: 32px;">

          <!-- Mono label -->
          <div style="font-family: 'JetBrains Mono', 'SF Mono', Monaco, monospace; font-size: 10px; text-transform: uppercase; letter-spacing: 0.25em; color: #9CA3AF; margin-bottom: 16px;">
            Evidence Landscape Ready
          </div>

          <h2 style="color: #111827; font-size: 18px; font-weight: 600; margin: 0 0 12px 0; line-height: 1.4;">
            Your evidence has been organised.
          </h2>

          <p style="color: #6B7280; font-size: 14px; line-height: 1.6; margin: 0 0 24px 0;">
            We gathered <strong style="color: #111827;">{total_sources} sources</strong> across <strong style="color: #111827;">{analyzed_count} claim{'s' if analyzed_count != 1 else ''}</strong>, classified by tier and type. The landscape is ready for your review.
          </p>

          {source_section}

          <!-- Stats -->
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px; border: 1px solid #E5E7EB;">
            <tr>
              <td style="text-align: center; padding: 16px; border-right: 1px solid #E5E7EB;" width="33%">
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 24px; font-weight: 600; color: #111827;">{analyzed_count}</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 9px; text-transform: uppercase; letter-spacing: 0.2em; color: #9CA3AF; margin-top: 4px;">Claims</div>
              </td>
              <td style="text-align: center; padding: 16px; border-right: 1px solid #E5E7EB;" width="34%">
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 24px; font-weight: 600; color: #111827;">{total_sources}</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 9px; text-transform: uppercase; letter-spacing: 0.2em; color: #9CA3AF; margin-top: 4px;">Sources</div>
              </td>
              <td style="text-align: center; padding: 16px;" width="33%">
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 24px; font-weight: 600; color: #EA580C;">{claims_count}</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 9px; text-transform: uppercase; letter-spacing: 0.2em; color: #9CA3AF; margin-top: 4px;">Total Claims</div>
              </td>
            </tr>
          </table>

          {claims_section}

          <!-- CTA Button -->
          <div style="text-align: center; padding-top: 8px;">
            <a href="{frontend_url}/dashboard/check/{check_id}" style="display: inline-block; background: #18181B; color: #FFFFFF; text-decoration: none; padding: 14px 32px; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.2em;">
              View Evidence Landscape &rarr;
            </a>
          </div>
        </div>

        <!-- Footer -->
        <div style="text-align: center; margin-top: 24px; padding-top: 24px; border-top: 1px solid #E5E7EB;">
          <p style="font-family: 'JetBrains Mono', monospace; font-size: 10px; text-transform: uppercase; letter-spacing: 0.2em; color: #9CA3AF; margin: 0 0 8px 0;">
            We organise &middot; You decide
          </p>
          <p style="color: #9CA3AF; font-size: 12px; margin: 0;">
            <a href="{frontend_url}/dashboard/settings?tab=notifications" style="color: #6B7280; text-decoration: none;">Manage preferences</a>
          </p>
        </div>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    def _render_check_failed_template(self, check_id: str, error_message: str) -> str:
        """Render check failed email HTML"""
        frontend_url = settings.FRONTEND_URL

        # Sanitize and truncate error message
        safe_error = error_message[:200].replace("<", "&lt;").replace(">", "&gt;")

        return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #F9FAFB; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; padding: 32px 16px;">
    <tr>
      <td>
        <!-- Header: Logo -->
        <div style="text-align: center; margin-bottom: 32px; padding-bottom: 24px; border-bottom: 1px solid #E5E7EB;">
          <img src="{frontend_url}/icon-192.png" alt="Tru8" width="48" height="48" style="display: inline-block;" />
        </div>

        <!-- Main Card -->
        <div style="background: #FFFFFF; border: 1px solid #E5E7EB; padding: 32px;">

          <!-- Mono label -->
          <div style="font-family: 'JetBrains Mono', 'SF Mono', Monaco, monospace; font-size: 10px; text-transform: uppercase; letter-spacing: 0.25em; color: #9CA3AF; margin-bottom: 16px;">
            Analysis Incomplete
          </div>

          <h2 style="color: #111827; font-size: 18px; font-weight: 600; margin: 0 0 12px 0; line-height: 1.4;">
            We weren&rsquo;t able to complete your analysis.
          </h2>

          <p style="color: #6B7280; font-size: 14px; line-height: 1.6; margin: 0 0 20px 0;">
            Something went wrong during evidence gathering. Your credit has been returned &mdash; no charge.
          </p>

          <!-- Error detail -->
          <div style="border-left: 3px solid #DC2626; padding: 12px 16px; margin-bottom: 24px; background: #FAFAFA;">
            <p style="font-family: 'JetBrains Mono', monospace; color: #991B1B; margin: 0; font-size: 12px;">{safe_error}</p>
          </div>

          <p style="color: #6B7280; font-size: 13px; line-height: 1.6; margin: 0 0 8px 0;">
            This usually happens when:
          </p>
          <ul style="color: #6B7280; margin: 0 0 24px 0; padding-left: 20px; font-size: 13px; line-height: 1.8;">
            <li>The URL is behind a paywall or login wall</li>
            <li>The content is too short to extract claims from</li>
            <li>The website blocked automated access</li>
          </ul>

          <!-- CTA Button -->
          <div style="text-align: center; padding-top: 8px;">
            <a href="{frontend_url}/dashboard/new-check" style="display: inline-block; background: #18181B; color: #FFFFFF; text-decoration: none; padding: 14px 32px; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.2em;">
              Try Another Source &rarr;
            </a>
          </div>
        </div>

        <!-- Footer -->
        <div style="text-align: center; margin-top: 24px; padding-top: 24px; border-top: 1px solid #E5E7EB;">
          <p style="color: #9CA3AF; font-size: 12px; margin: 0 0 8px 0;">
            Questions? <a href="mailto:hello@trueight.com" style="color: #6B7280; text-decoration: none;">hello@trueight.com</a>
          </p>
          <p style="color: #9CA3AF; font-size: 12px; margin: 0;">
            <a href="{frontend_url}/dashboard/settings?tab=notifications" style="color: #6B7280; text-decoration: none;">Manage preferences</a>
          </p>
        </div>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    # ---------- Lifecycle templates ----------
    #
    # House terminology: "evidence research" not "fact-checking", "analysis"
    # not "verification", UK spelling, and no verdict language anywhere —
    # Tru8 organises evidence, it does not adjudicate.

    def _render_welcome_template(self, name: Optional[str] = None) -> str:
        """Render the welcome email HTML."""
        frontend_url = settings.FRONTEND_URL
        sample_path = "/r/2484b9da-4c94-4042-9fac-61919b93e008"

        # Names come from the auth provider — escape before interpolating.
        first = (name or "").strip().split(" ")[0]
        greeting = f"Welcome, {html.escape(first)}." if first else "Welcome."

        return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #F9FAFB; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; padding: 32px 16px;">
    <tr>
      <td>
        <!-- Header: Logo -->
        <div style="text-align: center; margin-bottom: 32px; padding-bottom: 24px; border-bottom: 1px solid #E5E7EB;">
          <img src="{frontend_url}/icon-192.png" alt="Tru8" width="48" height="48" style="display: inline-block;" />
        </div>

        <!-- Main Card -->
        <div style="background: #FFFFFF; border: 1px solid #E5E7EB; padding: 32px;">

          <div style="font-family: 'JetBrains Mono', 'SF Mono', Monaco, monospace; font-size: 10px; text-transform: uppercase; letter-spacing: 0.25em; color: #9CA3AF; margin-bottom: 16px;">
            Three Free Checks
          </div>

          <h2 style="color: #111827; font-size: 18px; font-weight: 600; margin: 0 0 12px 0; line-height: 1.4;">
            {greeting}
          </h2>

          <p style="color: #6B7280; font-size: 14px; line-height: 1.6; margin: 0 0 16px 0;">
            Give Tru8 a claim or a link. It breaks the argument into its parts, gathers
            evidence from the open web and around twenty specialist sources, and lays out
            what it found &mdash; each source labelled by tier and type, with a receipt for
            anything left out.
          </p>

          <p style="color: #6B7280; font-size: 14px; line-height: 1.6; margin: 0 0 24px 0;">
            It won&rsquo;t tell you who is right. That part is yours.
          </p>

          <!-- How it works -->
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px; border: 1px solid #E5E7EB;">
            <tr>
              <td style="padding: 16px; border-right: 1px solid #E5E7EB;" width="33%">
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #D1D5DB; margin-bottom: 6px;">01</div>
                <div style="color: #111827; font-size: 13px; font-weight: 500;">Submit</div>
                <div style="color: #9CA3AF; font-size: 12px; line-height: 1.5; margin-top: 4px;">A claim, a question, or a URL.</div>
              </td>
              <td style="padding: 16px; border-right: 1px solid #E5E7EB;" width="34%">
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #D1D5DB; margin-bottom: 6px;">02</div>
                <div style="color: #111827; font-size: 13px; font-weight: 500;">Choose</div>
                <div style="color: #9CA3AF; font-size: 12px; line-height: 1.5; margin-top: 4px;">Pick which claims matter to you.</div>
              </td>
              <td style="padding: 16px;" width="33%">
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #D1D5DB; margin-bottom: 6px;">03</div>
                <div style="color: #111827; font-size: 13px; font-weight: 500;">Read</div>
                <div style="color: #9CA3AF; font-size: 12px; line-height: 1.5; margin-top: 4px;">Six views onto the same evidence.</div>
              </td>
            </tr>
          </table>

          <!-- CTA Button -->
          <div style="text-align: center; padding-top: 8px;">
            <a href="{frontend_url}/dashboard/new-check" style="display: inline-block; background: #18181B; color: #FFFFFF; text-decoration: none; padding: 14px 32px; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.2em;">
              Run Your First Check &rarr;
            </a>
          </div>

          <p style="color: #9CA3AF; font-size: 13px; line-height: 1.6; margin: 20px 0 0 0; text-align: center;">
            Or <a href="{frontend_url}{sample_path}" style="color: #6B7280; text-decoration: underline;">look at a finished report</a> first &mdash; no credit spent.
          </p>
        </div>

        <!-- Footer -->
        <div style="text-align: center; margin-top: 24px; padding-top: 24px; border-top: 1px solid #E5E7EB;">
          <p style="font-family: 'JetBrains Mono', monospace; font-size: 10px; text-transform: uppercase; letter-spacing: 0.2em; color: #9CA3AF; margin: 0 0 8px 0;">
            We organise &middot; You decide
          </p>
          <p style="color: #9CA3AF; font-size: 12px; margin: 0;">
            <a href="{frontend_url}/dashboard/settings?tab=notifications" style="color: #6B7280; text-decoration: none;">Manage preferences</a>
          </p>
        </div>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    def _render_trial_exhausted_template(
        self, checks_run: int = 0, sources_organised: int = 0
    ) -> str:
        """Render the trial-exhausted email HTML.

        Console figures are mirrored from web/lib/tiers.ts (£20/month,
        £200/year, 200 checks per month). If pricing moves, both move.
        """
        frontend_url = settings.FRONTEND_URL

        # Only show the tally when we actually have one — a proud "0 sources
        # organised" would be worse than saying nothing.
        stats_section = ""
        if checks_run > 0 or sources_organised > 0:
            stats_section = f"""
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 24px; border: 1px solid #E5E7EB;">
            <tr>
              <td style="text-align: center; padding: 16px; border-right: 1px solid #E5E7EB;" width="50%">
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 24px; font-weight: 600; color: #111827;">{checks_run}</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 9px; text-transform: uppercase; letter-spacing: 0.2em; color: #9CA3AF; margin-top: 4px;">Checks Run</div>
              </td>
              <td style="text-align: center; padding: 16px;" width="50%">
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 24px; font-weight: 600; color: #111827;">{sources_organised}</div>
                <div style="font-family: 'JetBrains Mono', monospace; font-size: 9px; text-transform: uppercase; letter-spacing: 0.2em; color: #9CA3AF; margin-top: 4px;">Sources Organised</div>
              </td>
            </tr>
          </table>
"""

        return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #F9FAFB; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; padding: 32px 16px;">
    <tr>
      <td>
        <!-- Header: Logo -->
        <div style="text-align: center; margin-bottom: 32px; padding-bottom: 24px; border-bottom: 1px solid #E5E7EB;">
          <img src="{frontend_url}/icon-192.png" alt="Tru8" width="48" height="48" style="display: inline-block;" />
        </div>

        <!-- Main Card -->
        <div style="background: #FFFFFF; border: 1px solid #E5E7EB; padding: 32px;">

          <div style="font-family: 'JetBrains Mono', 'SF Mono', Monaco, monospace; font-size: 10px; text-transform: uppercase; letter-spacing: 0.25em; color: #9CA3AF; margin-bottom: 16px;">
            Free Checks Used
          </div>

          <h2 style="color: #111827; font-size: 18px; font-weight: 600; margin: 0 0 12px 0; line-height: 1.4;">
            That&rsquo;s your three free checks.
          </h2>

          <p style="color: #6B7280; font-size: 14px; line-height: 1.6; margin: 0 0 24px 0;">
            Your reports stay where they are &mdash; nothing expires and nothing is deleted.
            To run more, Tru8 Console gives you 200 checks a month.
          </p>

          {stats_section}

          <!-- Console -->
          <div style="border: 1px solid #E5E7EB; padding: 20px; margin-bottom: 24px;">
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 9px; text-transform: uppercase; letter-spacing: 0.2em; color: #9CA3AF; margin-bottom: 8px;">Tru8 Console</div>
            <div style="color: #111827; font-size: 20px; font-weight: 600; margin-bottom: 4px;">&pound;20<span style="color: #9CA3AF; font-size: 14px; font-weight: 400;">/month</span></div>
            <div style="color: #9CA3AF; font-size: 12px; margin-bottom: 12px;">or &pound;200/year</div>
            <ul style="color: #6B7280; margin: 0; padding-left: 20px; font-size: 13px; line-height: 1.8;">
              <li>200 checks per month</li>
              <li>Full API &amp; MCP access</li>
              <li>Export reports</li>
            </ul>
          </div>

          <!-- CTA Button -->
          <div style="text-align: center; padding-top: 8px;">
            <a href="{frontend_url}/pricing" style="display: inline-block; background: #18181B; color: #FFFFFF; text-decoration: none; padding: 14px 32px; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.2em;">
              See Console &rarr;
            </a>
          </div>

          <p style="color: #9CA3AF; font-size: 13px; line-height: 1.6; margin: 20px 0 0 0; text-align: center;">
            Not the right fit? <a href="mailto:hello@trueight.com" style="color: #6B7280; text-decoration: underline;">Tell us why</a> &mdash; it genuinely helps.
          </p>
        </div>

        <!-- Footer -->
        <div style="text-align: center; margin-top: 24px; padding-top: 24px; border-top: 1px solid #E5E7EB;">
          <p style="font-family: 'JetBrains Mono', monospace; font-size: 10px; text-transform: uppercase; letter-spacing: 0.2em; color: #9CA3AF; margin: 0 0 8px 0;">
            We organise &middot; You decide
          </p>
          <p style="color: #9CA3AF; font-size: 12px; margin: 0;">
            <a href="{frontend_url}/dashboard/settings?tab=notifications" style="color: #6B7280; text-decoration: none;">Manage preferences</a>
          </p>
        </div>
      </td>
    </tr>
  </table>
</body>
</html>
"""


# Singleton instance
email_notification_service = EmailNotificationService()
