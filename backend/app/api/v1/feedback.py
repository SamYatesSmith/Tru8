"""
Feedback API endpoint for beta testing period.
Receives user feedback and sends email notifications to admin.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.core.auth import get_current_user
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class FeedbackRequest(BaseModel):
    type: str  # fact-check, ui, bug, suggestion, other
    message: str
    checkId: Optional[str] = None
    claimPosition: Optional[int] = None
    claimText: Optional[str] = None
    pageUrl: str
    userEmail: Optional[str] = None


class FeedbackResponse(BaseModel):
    success: bool
    message: str


def _get_type_emoji(feedback_type: str) -> str:
    """Get emoji for feedback type"""
    type_emojis = {
        'fact-check': '📊',
        'ui': '🎨',
        'bug': '🐛',
        'suggestion': '💡',
        'other': '❓',
    }
    return type_emojis.get(feedback_type, '❓')


def _get_type_label(feedback_type: str) -> str:
    """Get human-readable label for feedback type"""
    type_labels = {
        'fact-check': 'Fact-Check Result',
        'ui': 'UI / Design',
        'bug': 'Bug Report',
        'suggestion': 'Feature Suggestion',
        'other': 'Other',
    }
    return type_labels.get(feedback_type, 'Other')


def _send_feedback_email(feedback: FeedbackRequest, user_id: str) -> bool:
    """Send feedback notification email to admin"""
    try:
        import resend

        if not settings.RESEND_API_KEY:
            logger.warning("Resend API key not configured, skipping feedback email")
            return False

        resend.api_key = settings.RESEND_API_KEY

        type_emoji = _get_type_emoji(feedback.type)
        type_label = _get_type_label(feedback.type)

        # Build email content
        subject = f"[Tru8 Feedback] {type_emoji} {type_label}"
        if feedback.checkId:
            subject += f" - Check {feedback.checkId[:8]}"

        # Build HTML email
        claim_section = ""
        if feedback.claimPosition and feedback.claimText:
            claim_section = f"""
            <tr>
                <td style="padding: 8px 0; color: #94a3b8; font-size: 14px;">Claim #{feedback.claimPosition}</td>
                <td style="padding: 8px 0; color: #e2e8f0; font-size: 14px;">"{feedback.claimText[:100]}{'...' if len(feedback.claimText) > 100 else ''}"</td>
            </tr>
            """

        check_section = ""
        if feedback.checkId:
            check_url = f"https://tru8.com/dashboard/check/{feedback.checkId}"
            check_section = f"""
            <tr>
                <td style="padding: 8px 0; color: #94a3b8; font-size: 14px;">Check ID</td>
                <td style="padding: 8px 0; color: #e2e8f0; font-size: 14px;">
                    <a href="{check_url}" style="color: #f57a07;">{feedback.checkId}</a>
                </td>
            </tr>
            """

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0f172a; margin: 0; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #1e293b; border-radius: 12px; overflow: hidden; border: 1px solid #334155;">
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #f57a07 0%, #ea580c 100%); padding: 24px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 20px; font-weight: bold;">
                        {type_emoji} {type_label} Feedback
                    </h1>
                </div>

                <!-- Body -->
                <div style="padding: 24px;">
                    <!-- Message -->
                    <div style="background-color: #0f172a; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                        <p style="color: #e2e8f0; margin: 0; font-size: 15px; line-height: 1.6; white-space: pre-wrap;">{feedback.message}</p>
                    </div>

                    <!-- Metadata -->
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; color: #94a3b8; font-size: 14px; width: 100px;">From</td>
                            <td style="padding: 8px 0; color: #e2e8f0; font-size: 14px;">{feedback.userEmail or 'Unknown'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #94a3b8; font-size: 14px;">User ID</td>
                            <td style="padding: 8px 0; color: #e2e8f0; font-size: 14px; font-family: monospace; font-size: 12px;">{user_id}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; color: #94a3b8; font-size: 14px;">Page</td>
                            <td style="padding: 8px 0; color: #e2e8f0; font-size: 14px;">{feedback.pageUrl}</td>
                        </tr>
                        {check_section}
                        {claim_section}
                        <tr>
                            <td style="padding: 8px 0; color: #94a3b8; font-size: 14px;">Time</td>
                            <td style="padding: 8px 0; color: #e2e8f0; font-size: 14px;">{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</td>
                        </tr>
                    </table>
                </div>

                <!-- Footer -->
                <div style="padding: 16px 24px; background-color: #0f172a; border-top: 1px solid #334155;">
                    <p style="color: #64748b; font-size: 12px; margin: 0; text-align: center;">
                        Tru8 Beta Testing Feedback · This form will be removed in production
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        # Send to admin email
        admin_email = getattr(settings, 'FEEDBACK_EMAIL', None) or settings.EMAIL_FROM_ADDRESS

        params = {
            "from": f"Tru8 Feedback <{settings.EMAIL_FROM_ADDRESS}>",
            "to": [admin_email],
            "subject": subject,
            "html": html_content,
            "reply_to": feedback.userEmail if feedback.userEmail else None,
        }

        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        response = resend.Emails.send(params)
        email_id = response.get('id') if isinstance(response, dict) else getattr(response, 'id', 'unknown')
        logger.info(f"Feedback email sent successfully, id: {email_id}")
        return True

    except ImportError:
        logger.warning("Resend package not installed - feedback email skipped")
        return False
    except Exception as e:
        logger.error(f"Failed to send feedback email: {e}")
        return False


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Submit user feedback during beta testing period.
    Sends email notification to admin with feedback details.
    """
    user_id = current_user.get("id", "unknown")

    logger.info(
        f"Feedback received: type={feedback.type}, "
        f"user={feedback.userEmail}, "
        f"check={feedback.checkId}, "
        f"claim={feedback.claimPosition}"
    )

    # Log the feedback
    logger.info(f"[FEEDBACK] {feedback.type.upper()}: {feedback.message[:200]}...")

    # Send email notification
    email_sent = _send_feedback_email(feedback, user_id)

    if not email_sent:
        # Still return success - we logged it at least
        logger.warning("Feedback email not sent, but feedback logged")

    return FeedbackResponse(
        success=True,
        message="Thank you for your feedback!"
    )
