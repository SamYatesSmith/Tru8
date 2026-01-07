"""
Email notification service using Resend API
"""
import logging
from typing import Optional
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
                logger.warning("Resend package not installed - email notifications disabled")
                return None
        return self._resend

    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str
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

            response = resend.Emails.send(params)
            email_id = response.get('id') if isinstance(response, dict) else getattr(response, 'id', 'unknown')
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
        supported: int,
        contradicted: int,
        uncertain: int,
        credibility_score: int,
        # Enhanced parameters
        input_url: Optional[str] = None,
        input_title: Optional[str] = None,
        total_sources: int = 0,
        top_claims: Optional[list] = None,
        avg_confidence: int = 0
    ) -> bool:
        """
        Send email when a fact-check is completed (SYNC version for Celery workers).
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

                if not user.email_notifications_enabled or not user.email_check_completion:
                    logger.info(f"User {user_id} has check completion emails disabled")
                    return False

                subject = f"Your Tru8 fact-check is complete - {claims_count} claim{'s' if claims_count != 1 else ''} analyzed"

                html_content = self._render_check_completed_template(
                    check_id=check_id,
                    claims_count=claims_count,
                    supported=supported,
                    contradicted=contradicted,
                    uncertain=uncertain,
                    credibility_score=credibility_score,
                    input_url=input_url,
                    input_title=input_title,
                    total_sources=total_sources,
                    top_claims=top_claims or [],
                    avg_confidence=avg_confidence
                )

                return self._send_email(
                    to_email=user.email,
                    subject=subject,
                    html_content=html_content
                )

        except Exception as e:
            logger.error(f"Failed to send check completion email to user {user_id}: {e}")
            return False

    def send_check_failed_email_sync(
        self,
        user_id: str,
        check_id: str,
        error_message: str
    ) -> bool:
        """
        Send email when a fact-check fails (SYNC version for Celery workers).
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

                subject = "Your Tru8 fact-check encountered an issue"

                html_content = self._render_check_failed_template(
                    check_id=check_id,
                    error_message=error_message
                )

                return self._send_email(
                    to_email=user.email,
                    subject=subject,
                    html_content=html_content
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
        supported: int,
        contradicted: int,
        uncertain: int,
        credibility_score: int,
        # Enhanced parameters
        input_url: Optional[str] = None,
        input_title: Optional[str] = None,
        total_sources: int = 0,
        top_claims: Optional[list] = None,
        avg_confidence: int = 0
    ) -> bool:
        """Send email when a fact-check is completed (async wrapper)"""
        # For now, delegate to sync version - Resend SDK is synchronous
        return self.send_check_completed_email_sync(
            user_id=user_id,
            check_id=check_id,
            claims_count=claims_count,
            supported=supported,
            contradicted=contradicted,
            uncertain=uncertain,
            credibility_score=credibility_score,
            input_url=input_url,
            input_title=input_title,
            total_sources=total_sources,
            top_claims=top_claims,
            avg_confidence=avg_confidence
        )

    async def send_check_failed_email(
        self,
        user_id: str,
        check_id: str,
        error_message: str
    ) -> bool:
        """Send email when a fact-check fails (async wrapper)"""
        return self.send_check_failed_email_sync(
            user_id=user_id,
            check_id=check_id,
            error_message=error_message
        )

    # ========== EMAIL TEMPLATES ==========

    def _render_check_completed_template(
        self,
        check_id: str,
        claims_count: int,
        supported: int,
        contradicted: int,
        uncertain: int,
        credibility_score: int,
        input_url: Optional[str] = None,
        input_title: Optional[str] = None,
        total_sources: int = 0,
        top_claims: Optional[list] = None,
        avg_confidence: int = 0
    ) -> str:
        """Render check completion email HTML"""
        # Score-based color
        if credibility_score >= 70:
            score_color = "#059669"  # Emerald
        elif credibility_score >= 40:
            score_color = "#D97706"  # Amber
        else:
            score_color = "#DC2626"  # Red

        # Confidence color
        if avg_confidence >= 80:
            confidence_color = "#059669"
        elif avg_confidence >= 60:
            confidence_color = "#D97706"
        else:
            confidence_color = "#64748b"

        frontend_url = settings.FRONTEND_URL

        # Build source info section
        source_section = ""
        if input_url or input_title:
            display_title = input_title or input_url
            # No truncation - show full title, email layout will wrap naturally
            source_section = f"""
          <!-- Source Info -->
          <div style="background: #f8fafc; border-radius: 8px; padding: 12px 16px; margin-bottom: 20px;">
            <div style="color: #64748b; font-size: 12px; margin-bottom: 4px;">Content Analyzed</div>
            <div style="color: #1e293b; font-size: 14px; font-weight: 500;">{display_title}</div>
          </div>
"""

        # Build top claims section
        top_claims_section = ""
        if top_claims and len(top_claims) > 0:
            claims_html = ""
            for claim in top_claims[:2]:  # Max 2 claims
                verdict = claim.get("verdict", "uncertain")
                claim_text = claim.get("text", "")
                if len(claim_text) > 100:
                    claim_text = claim_text[:97] + "..."

                # Verdict colors and labels
                if verdict == "supported":
                    verdict_bg = "#dcfce7"
                    verdict_color = "#059669"
                    verdict_label = "✓ Supported"
                elif verdict == "contradicted":
                    verdict_bg = "#fee2e2"
                    verdict_color = "#DC2626"
                    verdict_label = "✗ Contradicted"
                else:
                    verdict_bg = "#fef3c7"
                    verdict_color = "#D97706"
                    verdict_label = "? Uncertain"

                claims_html += f"""
            <div style="background: #f8fafc; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;">
              <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div style="color: #1e293b; font-size: 13px; flex: 1; margin-right: 12px;">{claim_text}</div>
                <div style="background: {verdict_bg}; color: {verdict_color}; font-size: 11px; font-weight: 600; padding: 4px 8px; border-radius: 4px; white-space: nowrap;">{verdict_label}</div>
              </div>
            </div>
"""

            top_claims_section = f"""
          <!-- Key Claims -->
          <div style="margin-bottom: 20px;">
            <div style="color: #64748b; font-size: 12px; margin-bottom: 8px; font-weight: 600;">KEY CLAIMS</div>
            {claims_html}
          </div>
"""

        return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; padding: 24px;">
    <tr>
      <td>
        <!-- Header -->
        <div style="text-align: center; margin-bottom: 24px;">
          <h1 style="color: #1E40AF; font-size: 28px; font-weight: bold; margin: 0;">TRU8</h1>
        </div>

        <!-- Main Card -->
        <div style="background: white; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
          <h2 style="color: #1e293b; font-size: 20px; margin: 0 0 16px 0;">Your fact-check is complete!</h2>

          {source_section}

          <p style="color: #64748b; margin: 0 0 20px 0;">
            We analyzed <strong>{claims_count} claim{'s' if claims_count != 1 else ''}</strong> against <strong>{total_sources} sources</strong>.
          </p>

          <!-- Confidence Badge (Primary Metric) -->
          <div style="text-align: center; margin-bottom: 24px;">
            <div style="display: inline-block; background: {confidence_color}20; border-radius: 12px; padding: 16px 32px;">
              <div style="font-size: 48px; font-weight: bold; color: {confidence_color};">{avg_confidence}%</div>
              <div style="color: #64748b; font-size: 14px;">Average Confidence</div>
            </div>
          </div>

          <!-- Stats Table -->
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 20px;">
            <tr>
              <td style="text-align: center; padding: 8px;">
                <div style="font-size: 24px; font-weight: bold; color: #059669;">{supported}</div>
                <div style="color: #64748b; font-size: 12px;">Supported</div>
              </td>
              <td style="text-align: center; padding: 8px;">
                <div style="font-size: 24px; font-weight: bold; color: #DC2626;">{contradicted}</div>
                <div style="color: #64748b; font-size: 12px;">Contradicted</div>
              </td>
              <td style="text-align: center; padding: 8px;">
                <div style="font-size: 24px; font-weight: bold; color: #D97706;">{uncertain}</div>
                <div style="color: #64748b; font-size: 12px;">Uncertain</div>
              </td>
            </tr>
          </table>

          <!-- Credibility Score (Secondary) -->
          <div style="text-align: center; margin-bottom: 24px;">
            <span style="color: #64748b; font-size: 13px;">Credibility Score: </span>
            <span style="color: {score_color}; font-size: 13px; font-weight: 600;">{credibility_score}/100</span>
          </div>

          {top_claims_section}

          <!-- CTA Button -->
          <div style="text-align: center;">
            <a href="{frontend_url}/dashboard/check/{check_id}" style="display: inline-block; background: linear-gradient(135deg, #1E40AF 0%, #7C3AED 100%); color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: bold;">
              View Full Results
            </a>
          </div>
        </div>

        <!-- Footer -->
        <div style="text-align: center; margin-top: 24px; color: #94a3b8; font-size: 12px;">
          <p style="margin: 0 0 8px 0;">Tru8 - Thorough fact-checking with credible sources</p>
          <p style="margin: 0;">
            <a href="{frontend_url}/dashboard/settings?tab=notifications" style="color: #64748b;">Manage notification preferences</a>
          </p>
        </div>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    def _render_check_failed_template(
        self,
        check_id: str,
        error_message: str
    ) -> str:
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
<body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 600px; margin: 0 auto; padding: 24px;">
    <tr>
      <td>
        <!-- Header -->
        <div style="text-align: center; margin-bottom: 24px;">
          <h1 style="color: #1E40AF; font-size: 28px; font-weight: bold; margin: 0;">TRU8</h1>
        </div>

        <!-- Main Card -->
        <div style="background: white; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
          <h2 style="color: #1e293b; font-size: 20px; margin: 0 0 16px 0;">Your fact-check encountered an issue</h2>

          <p style="color: #64748b; margin: 0 0 16px 0;">
            We weren't able to complete your fact-check. Don't worry - your credit has been returned.
          </p>

          <div style="background: #fef2f2; border-left: 4px solid #DC2626; padding: 12px 16px; margin-bottom: 24px;">
            <p style="color: #991b1b; margin: 0; font-size: 14px;">{safe_error}</p>
          </div>

          <p style="color: #64748b; margin: 0 0 12px 0; font-size: 14px;">
            Common reasons this might happen:
          </p>
          <ul style="color: #64748b; margin: 0 0 24px 0; padding-left: 20px; font-size: 14px;">
            <li>The URL might be behind a paywall</li>
            <li>The content might be too short to extract claims</li>
            <li>The website might have blocked our access</li>
          </ul>

          <!-- CTA Button -->
          <div style="text-align: center;">
            <a href="{frontend_url}/dashboard" style="display: inline-block; background: linear-gradient(135deg, #1E40AF 0%, #7C3AED 100%); color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: bold;">
              Try Again
            </a>
          </div>
        </div>

        <!-- Footer -->
        <div style="text-align: center; margin-top: 24px; color: #94a3b8; font-size: 12px;">
          <p style="margin: 0 0 8px 0;">Need help? Contact us at hello@trueight.com</p>
          <p style="margin: 0;">
            <a href="{frontend_url}/dashboard/settings?tab=notifications" style="color: #64748b;">Manage notification preferences</a>
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
