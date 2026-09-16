import base64
import cloudinary.uploader
from celery import shared_task
from celery.utils.log import get_task_logger

from sqlalchemy.orm import Session, joinedload
from .database import SessionLocal
# from .celery_worker import celery_app
from . import models
from .config import setup_cloudinary, settings

import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException


BREVO_API_KEY = settings.brevo_api_key
brevo_config = sib_api_v3_sdk.Configuration()
brevo_config.api_key['api-key'] = BREVO_API_KEY
company_email = "nwolisaodinaka5@gmail.com"




@shared_task(name="send_admin_email_task")
def send_admin_email(message_id: int):
    db = SessionLocal()
    try:
        contact_msg = db.query(models.ContactMessage).filter(models.ContactMessage.id == message_id).first()
        if not contact_msg:
            return

        # Format the enum value for the subject line and body (e.g., "bespoke_dress" -> "Bespoke Dress")
        inquiry_type_str = contact_msg.inquiry_type.name.replace('_', ' ').title()
        
        # HTML content designed for the admin to read
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                    <h2 style="color: #333;">New Inquiry: {inquiry_type_str}</h2>
                    <p>You have received a new contact message from the storefront.</p>
                    
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <tr>
                            <td style="padding: 8px 0; border-bottom: 1px solid #eee; width: 100px;"><strong>Name:</strong></td>
                            <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{contact_msg.first_name} {contact_msg.last_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Email:</strong></td>
                            <td style="padding: 8px 0; border-bottom: 1px solid #eee;"><a href="mailto:{contact_msg.email}" style="color: #000;">{contact_msg.email}</a></td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Type:</strong></td>
                            <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{inquiry_type_str}</td>
                        </tr>
                    </table>
                    
                    <p style="font-size: 0.9em; color: #555; margin-bottom: 5px;"><strong>Message:</strong></p>
                    <div style="background-color: #f9f9f9; padding: 15px; border-radius: 4px; white-space: pre-wrap; color: #333;">
                        {contact_msg.message}
                    </div>
                    
                    <p style="margin-top: 30px; font-size: 0.8em; color: #888;">
                        * You can reply directly to this email to respond to the customer.
                    </p>
                </div>
            </body>
        </html>
        """

        api_client = sib_api_v3_sdk.ApiClient(brevo_config)
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(api_client)
        
        # The admin's email
        # admin_email = "lorretanwolisa@gmail.com"
        admin_email = "lorretanwolisa@gmail.com"
        
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            # Send TO the admin
            to=[{"email": admin_email, "name": "Ogechukwu Nwolisa"}],
            
            # The sender should be your verified domain email (e.g., info@oggystitches.com)
            sender={"email": company_email, "name": "oggystitches Storefront"}, 
            
            # This is the magic line that makes "Reply" go to the customer instead of company_email
            reply_to={"email": contact_msg.email, "name": f"{contact_msg.first_name} {contact_msg.last_name}"}, 
            
            subject=f"New {inquiry_type_str} from {contact_msg.first_name} {contact_msg.last_name}",
            html_content=html_content
        )
        
        api_instance.send_transac_email(send_smtp_email)
        return f"Admin notification email sent for message {message_id}"
        
    except Exception as e:
        print(f"Error sending admin notification email: {str(e)}")
    finally:
        db.close()