"""
Push notification service using Expo Push Notifications
"""
import logging
from typing import List, Optional, Dict, Any
from exponent_server_sdk import PushClient, PushMessage, PushServerError, PushTicketError
from app.core.database import async_session
from app.models.user import User

logger = logging.getLogger(__name__)

class PushNotificationService:
    def __init__(self):
        self.client = PushClient()
    
    async def send_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None
    ) -> bool:
        """
        Send a push notification to a specific user
        
        Args:
            user_id: The user's ID
            title: Notification title
            body: Notification body
            data: Additional data payload
            category: Notification category for action buttons
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            async with async_session() as session:
                user = await session.get(User, user_id)
                
                if not user or not user.push_token or not user.push_notifications_enabled:
                    logger.info(f"User {user_id} has no push token or notifications disabled")
                    return False
                
                return await self._send_push_message(
                    push_token=user.push_token,
                    title=title,
                    body=body,
                    data=data,
                    category=category
                )
        except Exception as e:
            logger.error(f"Failed to send notification to user {user_id}: {e}")
            return False
    
    async def send_bulk_notifications(
        self,
        user_ids: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None
    ) -> int:
        """
        Send push notifications to multiple users
        
        Returns:
            int: Number of successfully sent notifications
        """
        successful_sends = 0
        
        try:
            async with async_session() as session:
                from sqlmodel import select
                stmt = select(User).where(
                    User.id.in_(user_ids),
                    User.push_token != None,
                    User.push_notifications_enabled == True
                )
                result = await session.execute(stmt)
                users = result.scalars().all()
                
                messages = []
                for user in users:
                    message = PushMessage(
                        to=user.push_token,
                        title=title,
                        body=body,
                        data=data or {},
                        category_id=category,
                        sound='default',
                        badge=1
                    )
                    messages.append(message)
                
                if not messages:
                    logger.info(f"No valid push tokens found for {len(user_ids)} users")
                    return 0
                
                # Send in batches
                batch_size = 100
                for i in range(0, len(messages), batch_size):
                    batch = messages[i:i + batch_size]
                    try:
                        responses = self.client.publish_multiple(batch)
                        
                        for response in responses:
                            if response.is_success():
                                successful_sends += 1
                            else:
                                logger.warning(f"Push notification failed: {response.details}")
                                
                    except (PushTicketError, PushServerError) as e:
                        logger.error(f"Batch push notification failed: {e}")
                        
        except Exception as e:
            logger.error(f"Bulk notification send failed: {e}")
            
        return successful_sends
    
    async def _send_push_message(
        self,
        push_token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None
    ) -> bool:
        """
        Send a single push message
        """
        try:
            message = PushMessage(
                to=push_token,
                title=title,
                body=body,
                data=data or {},
                category_id=category,
                sound='default',
                badge=1,
                priority='high'
            )
            
            response = self.client.publish(message)
            
            if response.is_success():
                logger.info(f"Push notification sent successfully to token {push_token[:8]}...")
                return True
            else:
                logger.warning(f"Push notification failed: {response.details}")
                return False
                
        except (PushTicketError, PushServerError) as e:
            logger.error(f"Failed to send push message: {e}")
            return False
    
    async def send_check_completed_notification(
        self,
        user_id: str,
        check_id: str,
        claims_count: int
    ) -> bool:
        """
        Send a notification when a fact-check is completed
        """
        title = "Fact-check complete!"
        body = f"Found {claims_count} claim{'s' if claims_count != 1 else ''} to verify"
        
        data = {
            'type': 'check_complete',
            'checkId': check_id,
            'claimsCount': claims_count
        }
        
        return await self.send_notification(
            user_id=user_id,
            title=title,
            body=body,
            data=data,
            category='check_complete'
        )
    
    async def send_check_failed_notification(
        self,
        user_id: str,
        check_id: str,
        error_message: str
    ) -> bool:
        """
        Send a notification when a fact-check fails
        """
        title = "Fact-check failed"
        body = "Tap to try again"
        
        data = {
            'type': 'check_failed',
            'checkId': check_id,
            'error': error_message
        }
        
        return await self.send_notification(
            user_id=user_id,
            title=title,
            body=body,
            data=data,
            category='check_failed'
        )
    
    async def register_push_token(
        self,
        user_id: str,
        push_token: str,
        platform: str,
        device_id: Optional[str] = None
    ) -> bool:
        """
        Register a push token for a user
        """
        try:
            async with async_session() as session:
                user = await session.get(User, user_id)
                if not user:
                    logger.error(f"User {user_id} not found")
                    return False
                
                user.push_token = push_token
                user.platform = platform.lower()
                user.device_id = device_id
                user.push_notifications_enabled = True
                
                session.add(user)
                await session.commit()
                
                logger.info(f"Push token registered for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to register push token for user {user_id}: {e}")
            return False
    
    async def unregister_push_token(self, user_id: str) -> bool:
        """
        Remove push token for a user (when they sign out)
        """
        try:
            async with async_session() as session:
                user = await session.get(User, user_id)
                if not user:
                    return False
                
                user.push_token = None
                user.platform = None
                user.device_id = None
                
                session.add(user)
                await session.commit()
                
                logger.info(f"Push token unregistered for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to unregister push token for user {user_id}: {e}")
            return False
    
    async def update_notification_preferences(
        self,
        user_id: str,
        enabled: bool
    ) -> bool:
        """
        Update user's notification preferences
        """
        try:
            async with async_session() as session:
                user = await session.get(User, user_id)
                if not user:
                    return False
                
                user.push_notifications_enabled = enabled
                session.add(user)
                await session.commit()
                
                logger.info(f"Notification preferences updated for user {user_id}: {enabled}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update notification preferences for user {user_id}: {e}")
            return False

# Singleton instance
push_notification_service = PushNotificationService()