import os
import logging
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail import EmailMultiAlternatives
import resend

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    """
    Custom email backend for Resend service
    """
    
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        # Set the API key from settings
        resend.api_key = getattr(settings, 'RESEND_API_KEY', None)
        if not resend.api_key:
            logger.warning("RESEND_API_KEY is not set. Email sending will fail.")
    
    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects and return the number of emails sent.
        """
        if not email_messages:
            return 0
        
        if not resend.api_key:
            if not self.fail_silently:
                raise ValueError("RESEND_API_KEY is not configured")
            return 0
        
        num_sent = 0
        for message in email_messages:
            if self._send_message(message):
                num_sent += 1
        
        return num_sent
    
    def _send_message(self, email_message):
        """
        Send a single email message via Resend
        """
        try:
            # Prepare the email data for Resend
            email_data = {
                "from": email_message.from_email or settings.DEFAULT_FROM_EMAIL,
                "to": email_message.to,
                "subject": email_message.subject,
            }
            
            # Handle CC and BCC
            if email_message.cc:
                email_data["cc"] = email_message.cc
            if email_message.bcc:
                email_data["bcc"] = email_message.bcc
            
            # Handle reply-to
            if email_message.reply_to:
                email_data["reply_to"] = email_message.reply_to[0]
            
            # Handle message body
            if isinstance(email_message, EmailMultiAlternatives):
                # Check for HTML alternative
                html_body = None
                for content, mimetype in email_message.alternatives:
                    if mimetype == 'text/html':
                        html_body = content
                        break
                
                if html_body:
                    email_data["html"] = html_body
                else:
                    email_data["text"] = email_message.body
            else:
                # Plain text email
                email_data["text"] = email_message.body
            
            # Add tags if configured
            tags = getattr(settings, 'RESEND_DEFAULT_TAGS', None)
            if tags:
                email_data["tags"] = tags
            
            # Send the email
            response = resend.Emails.send(email_data)
            
            # Check if response indicates success (either dict with 'id' key or object with 'id' attribute)
            response_id = None
            if response:
                if isinstance(response, dict) and 'id' in response:
                    response_id = response['id']
                elif hasattr(response, 'id'):
                    response_id = response.id
            
            if response_id:
                logger.info(f"Email sent successfully via Resend. ID: {response_id}")
                return True
            else:
                logger.error(f"Failed to send email via Resend. Response: {response}")
                if not self.fail_silently:
                    raise Exception(f"Resend API error: {response}")
                return False
        
        except Exception as e:
            logger.error(f"Error sending email via Resend: {str(e)}")
            if not self.fail_silently:
                raise
            return False
