"""
Email Notification Service
Sends automatic email notifications for bookings and handovers
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime


class EmailService:
    """Handle email notifications"""
    
    @staticmethod
    def send_email(to_email, subject, html_body, text_body=None):
        """
        Send email using SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email content
            text_body: Plain text fallback (optional)
        
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # Get email configuration from environment
            smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_user = os.getenv('SMTP_USER')
            smtp_password = os.getenv('SMTP_PASSWORD')
            from_email = os.getenv('FROM_EMAIL', smtp_user)
            
            if not smtp_user or not smtp_password:
                print("ERROR: SMTP credentials not configured in .env")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_email
            msg['To'] = to_email
            
            # Add text and HTML parts
            if text_body:
                part1 = MIMEText(text_body, 'plain')
                msg.attach(part1)
            
            part2 = MIMEText(html_body, 'html')
            msg.attach(part2)
            
            # Send email
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            print(f"✓ Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to send email: {str(e)}")
            return False
    
    @staticmethod
    def send_booking_notification(booking):
        """
        Send notification when new booking is created
        
        Args:
            booking: Booking model instance
        """
        staff_email = os.getenv('STAFF_EMAIL')
        if not staff_email:
            print("WARNING: STAFF_EMAIL not configured in .env")
            return False
        
        subject = f"🎉 New Booking Request #{booking.id}"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                .field {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #555; }}
                .value {{ color: #000; }}
                .footer {{ margin-top: 20px; padding: 15px; background: #f0f0f0; text-align: center; font-size: 12px; color: #666; }}
                .button {{ display: inline-block; padding: 10px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>New Booking Request</h2>
                    <p>Booking ID: #{booking.id}</p>
                </div>
                <div class="content">
                    <div class="field">
                        <span class="label">Customer Name:</span>
                        <span class="value">{booking.name}</span>
                    </div>
                    <div class="field">
                        <span class="label">Email:</span>
                        <span class="value">{booking.email}</span>
                    </div>
                    <div class="field">
                        <span class="label">Phone:</span>
                        <span class="value">{booking.phone}</span>
                    </div>
                    <div class="field">
                        <span class="label">Destination:</span>
                        <span class="value">{booking.destination or 'Not specified'}</span>
                    </div>
                    <div class="field">
                        <span class="label">Duration:</span>
                        <span class="value">{booking.days or 'Not specified'} days</span>
                    </div>
                    <div class="field">
                        <span class="label">Budget:</span>
                        <span class="value">${booking.budget or 'Not specified'}</span>
                    </div>
                    <div class="field">
                        <span class="label">Package:</span>
                        <span class="value">{booking.package or 'Not specified'}</span>
                    </div>
                    <div class="field">
                        <span class="label">Message:</span>
                        <span class="value">{booking.message or 'No message'}</span>
                    </div>
                    <div class="field">
                        <span class="label">Status:</span>
                        <span class="value">{booking.status}</span>
                    </div>
                    <div class="field">
                        <span class="label">Created:</span>
                        <span class="value">{booking.created_at.strftime('%Y-%m-%d %H:%M:%S')}</span>
                    </div>
                    
                    <div style="margin-top: 20px; text-align: center;">
                        <a href="mailto:{booking.email}?subject=Re:%20Your%20Uganda%20Booking%20Request%20%23{booking.id}" class="button">
                            Reply via Email
                        </a>
                    </div>
                </div>
                <div class="footer">
                    <p>This is an automated notification from Everything Uganda Chatbot</p>
                    <p>Session ID: {booking.session_id or 'N/A'}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        NEW BOOKING REQUEST #{booking.id}
        
        Customer: {booking.name}
        Email: {booking.email}
        Phone: {booking.phone}
        Destination: {booking.destination or 'Not specified'}
        Duration: {booking.days or 'Not specified'} days
        Budget: ${booking.budget or 'Not specified'}
        Package: {booking.package or 'Not specified'}
        Message: {booking.message or 'No message'}
        Status: {booking.status}
        Created: {booking.created_at.strftime('%Y-%m-%d %H:%M:%S')}
        
        Contact customer: {booking.phone}
        """
        
        return EmailService.send_email(staff_email, subject, html_body, text_body)
    
    @staticmethod
    def send_handover_notification(handover):
        """
        Send notification when human handover is requested
        
        Args:
            handover: Handover model instance
        """
        staff_email = os.getenv('STAFF_EMAIL')
        if not staff_email:
            print("WARNING: STAFF_EMAIL not configured in .env")
            return False
        
        priority_emoji = {
            'low': '🟢',
            'medium': '🟡',
            'high': '🟠',
            'urgent': '🔴'
        }
        
        emoji = priority_emoji.get(handover.priority, '⚪')
        
        subject = f"{emoji} Human Assistance Requested #{handover.id} - {handover.priority.upper()} Priority"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #FF9800; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                .field {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #555; }}
                .value {{ color: #000; }}
                .priority {{ display: inline-block; padding: 5px 10px; border-radius: 3px; font-weight: bold; }}
                .priority-low {{ background: #4CAF50; color: white; }}
                .priority-medium {{ background: #FFC107; color: black; }}
                .priority-high {{ background: #FF9800; color: white; }}
                .priority-urgent {{ background: #F44336; color: white; }}
                .footer {{ margin-top: 20px; padding: 15px; background: #f0f0f0; text-align: center; font-size: 12px; color: #666; }}
                .button {{ display: inline-block; padding: 10px 20px; background: #FF9800; color: white; text-decoration: none; border-radius: 5px; margin: 10px 5px; }}
                .message-box {{ background: white; padding: 15px; border-left: 4px solid #FF9800; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>🤝 Human Assistance Requested</h2>
                    <p>Handover ID: #{handover.id}</p>
                </div>
                <div class="content">
                    <div class="field">
                        <span class="label">Priority:</span>
                        <span class="priority priority-{handover.priority}">{handover.priority.upper()}</span>
                    </div>
                    <div class="field">
                        <span class="label">Session ID:</span>
                        <span class="value">{handover.session_id}</span>
                    </div>
                    <div class="field">
                        <span class="label">Customer Email:</span>
                        <span class="value">{handover.user_email or 'Not provided'}</span>
                    </div>
                    <div class="field">
                        <span class="label">Customer Phone:</span>
                        <span class="value">{handover.user_phone or 'Not provided'}</span>
                    </div>
                    <div class="field">
                        <span class="label">Itinerary ID:</span>
                        <span class="value">{handover.itinerary_id or 'None'}</span>
                    </div>
                    <div class="field">
                        <span class="label">Status:</span>
                        <span class="value">{handover.status}</span>
                    </div>
                    <div class="field">
                        <span class="label">Created:</span>
                        <span class="value">{handover.created_at.strftime('%Y-%m-%d %H:%M:%S')}</span>
                    </div>
                    
                    <div class="message-box">
                        <strong>Customer Message:</strong>
                        <p>{handover.user_message}</p>
                    </div>
                    
                    <div style="margin-top: 20px; text-align: center;">
                        {f'<a href="mailto:{handover.user_email}?subject=Re:%20Your%20Uganda%20Travel%20Request" class="button">Reply via Email</a>' if handover.user_email else ''}
                    </div>
                </div>
                <div class="footer">
                    <p>This is an automated notification from Everything Uganda Chatbot</p>
                    <p>Please respond within 1 hour for {handover.priority} priority requests</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        HUMAN ASSISTANCE REQUESTED #{handover.id}
        Priority: {handover.priority.upper()}
        
        Session ID: {handover.session_id}
        Customer Email: {handover.user_email or 'Not provided'}
        Customer Phone: {handover.user_phone or 'Not provided'}
        Itinerary ID: {handover.itinerary_id or 'None'}
        Status: {handover.status}
        Created: {handover.created_at.strftime('%Y-%m-%d %H:%M:%S')}
        
        Customer Message:
        {handover.user_message}
        
        Please respond promptly!
        """
        
        return EmailService.send_email(staff_email, subject, html_body, text_body)
    
    @staticmethod
    def send_booking_confirmation_to_customer(booking):
        """
        Send confirmation email to customer after booking
        
        Args:
            booking: Booking model instance
        """
        if not booking.email:
            return False
        
        subject = "✅ Booking Confirmation - Everything Uganda"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                .footer {{ margin-top: 20px; padding: 15px; background: #f0f0f0; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Thank You for Your Booking!</h2>
                </div>
                <div class="content">
                    <p>Dear {booking.name},</p>
                    <p>Thank you for choosing Everything Uganda! We have received your booking request.</p>
                    <p><strong>Booking Reference:</strong> #{booking.id}</p>
                    <p>Our travel experts will review your request and contact you within 24 hours to confirm your itinerary and finalize the details.</p>
                    <p>If you have any questions, feel free to reach out to us:</p>
                    <ul>
                        <li>Email: {os.getenv('STAFF_EMAIL', 'reservations@everythinguganda.co.uk')}</li>
                    </ul>
                    <p>We look forward to making your Uganda experience unforgettable!</p>
                </div>
                <div class="footer">
                    <p>Everything Uganda - Your Gateway to the Pearl of Africa</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService.send_email(booking.email, subject, html_body)
