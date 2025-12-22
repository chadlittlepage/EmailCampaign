"""
Brevo (Sendinblue) Integration - Sync contacts and manage campaigns
"""
import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException


@dataclass
class Contact:
    email: str
    first_name: str
    last_name: str
    company: Optional[str] = None
    position: Optional[str] = None
    linkedin_url: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None


@dataclass
class SyncResult:
    total: int
    created: int
    updated: int
    failed: int
    errors: List[str]


class BrevoClient:
    """Client for Brevo (Sendinblue) API operations"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Brevo client.

        Args:
            api_key: Brevo API key. If not provided, reads from BREVO_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("BREVO_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Brevo API key required. Set BREVO_API_KEY environment variable "
                "or pass api_key parameter."
            )

        # Configure API client
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = self.api_key
        self.api_client = sib_api_v3_sdk.ApiClient(configuration)

        # Initialize API instances
        self.contacts_api = sib_api_v3_sdk.ContactsApi(self.api_client)
        self.lists_api = sib_api_v3_sdk.ContactsApi(self.api_client)
        self.campaigns_api = sib_api_v3_sdk.EmailCampaignsApi(self.api_client)

    def get_or_create_list(self, list_name: str, folder_id: int = 1) -> int:
        """
        Get existing list by name or create new one.

        Args:
            list_name: Name of the contact list
            folder_id: Folder ID to create list in (default: 1)

        Returns:
            List ID
        """
        try:
            # Get all lists and find by name
            lists = self.contacts_api.get_lists(limit=50)
            for lst in lists.lists:
                if lst.name == list_name:
                    return lst.id

            # Create new list if not found
            create_list = sib_api_v3_sdk.CreateList(name=list_name, folder_id=folder_id)
            result = self.contacts_api.create_list(create_list)
            return result.id

        except ApiException as e:
            raise Exception(f"Failed to get/create list: {e}")

    def create_contact(self, contact: Contact, list_ids: Optional[List[int]] = None) -> bool:
        """
        Create or update a contact in Brevo.

        Args:
            contact: Contact data
            list_ids: Optional list IDs to add contact to

        Returns:
            True if successful
        """
        try:
            attributes = {
                "FIRSTNAME": contact.first_name,
                "LASTNAME": contact.last_name,
            }
            if contact.company:
                attributes["COMPANY"] = contact.company
            if contact.position:
                attributes["POSITION"] = contact.position
            if contact.linkedin_url:
                attributes["LINKEDIN_URL"] = contact.linkedin_url
            if contact.attributes:
                attributes.update(contact.attributes)

            create_contact = sib_api_v3_sdk.CreateContact(
                email=contact.email,
                attributes=attributes,
                list_ids=list_ids or [],
                update_enabled=True,  # Update if exists
            )

            self.contacts_api.create_contact(create_contact)
            return True

        except ApiException as e:
            if e.status == 400 and "already exist" in str(e.body).lower():
                # Contact exists, try to update
                return self._update_contact(contact, list_ids)
            raise

    def _update_contact(self, contact: Contact, list_ids: Optional[List[int]] = None) -> bool:
        """Update existing contact"""
        try:
            attributes = {
                "FIRSTNAME": contact.first_name,
                "LASTNAME": contact.last_name,
            }
            if contact.company:
                attributes["COMPANY"] = contact.company
            if contact.position:
                attributes["POSITION"] = contact.position
            if contact.linkedin_url:
                attributes["LINKEDIN_URL"] = contact.linkedin_url

            update_contact = sib_api_v3_sdk.UpdateContact(
                attributes=attributes,
                list_ids=list_ids or [],
            )

            self.contacts_api.update_contact(contact.email, update_contact)
            return True

        except ApiException:
            return False

    def sync_contacts(
        self,
        contacts: List[Contact],
        list_name: str = "LinkedIn Connections",
        batch_size: int = 100,
    ) -> SyncResult:
        """
        Sync multiple contacts to Brevo.

        Args:
            contacts: List of contacts to sync
            list_name: Name of list to add contacts to
            batch_size: Number of contacts per batch (for progress tracking)

        Returns:
            SyncResult with statistics
        """
        # Get or create the list
        list_id = self.get_or_create_list(list_name)

        result = SyncResult(
            total=len(contacts),
            created=0,
            updated=0,
            failed=0,
            errors=[],
        )

        for i, contact in enumerate(contacts):
            try:
                success = self.create_contact(contact, list_ids=[list_id])
                if success:
                    result.created += 1
            except ApiException as e:
                result.failed += 1
                result.errors.append(f"{contact.email}: {e.reason}")
            except Exception as e:
                result.failed += 1
                result.errors.append(f"{contact.email}: {str(e)}")

        return result

    def create_campaign(
        self,
        name: str,
        subject: str,
        html_content: str,
        list_ids: List[int],
        sender_name: str,
        sender_email: str,
        reply_to: Optional[str] = None,
    ) -> int:
        """
        Create an email campaign.

        Args:
            name: Campaign name
            subject: Email subject line
            html_content: HTML email content
            list_ids: List IDs to send to
            sender_name: Sender display name
            sender_email: Sender email address
            reply_to: Reply-to email (optional)

        Returns:
            Campaign ID
        """
        try:
            sender = sib_api_v3_sdk.CreateEmailCampaignSender(
                name=sender_name,
                email=sender_email,
            )

            recipients = sib_api_v3_sdk.CreateEmailCampaignRecipients(
                list_ids=list_ids,
            )

            campaign = sib_api_v3_sdk.CreateEmailCampaign(
                name=name,
                subject=subject,
                sender=sender,
                html_content=html_content,
                recipients=recipients,
                reply_to=reply_to or sender_email,
            )

            result = self.campaigns_api.create_email_campaign(campaign)
            return result.id

        except ApiException as e:
            raise Exception(f"Failed to create campaign: {e}")

    def get_account_info(self) -> Dict[str, Any]:
        """Get Brevo account information to verify API key"""
        try:
            account_api = sib_api_v3_sdk.AccountApi(self.api_client)
            account = account_api.get_account()
            return {
                "email": account.email,
                "first_name": account.first_name,
                "last_name": account.last_name,
                "company_name": account.company_name,
                "plan": [p.type for p in account.plan],
            }
        except ApiException as e:
            raise Exception(f"Failed to get account info: {e}")


# Convenience function
def sync_linkedin_to_brevo(
    csv_path: str,
    api_key: Optional[str] = None,
    list_name: str = "LinkedIn Connections",
) -> SyncResult:
    """
    Sync LinkedIn connections CSV (with found emails) to Brevo.

    Args:
        csv_path: Path to CSV file with 'Found Email' column
        api_key: Brevo API key (or set BREVO_API_KEY env var)
        list_name: Name of Brevo list to create/update

    Returns:
        SyncResult with statistics
    """
    import pandas as pd

    # Read CSV
    df = pd.read_csv(csv_path)

    # Filter to contacts with emails
    df_with_emails = df[df["Found Email"].notna() & (df["Found Email"] != "")]

    # Convert to Contact objects
    contacts = []
    for _, row in df_with_emails.iterrows():
        contacts.append(
            Contact(
                email=row["Found Email"],
                first_name=str(row.get("First Name", "")).strip(),
                last_name=str(row.get("Last Name", "")).strip(),
                company=str(row.get("Company", "")).strip() if pd.notna(row.get("Company")) else None,
                position=str(row.get("Position", "")).strip() if pd.notna(row.get("Position")) else None,
                linkedin_url=str(row.get("URL", "")).strip() if pd.notna(row.get("URL")) else None,
            )
        )

    # Sync to Brevo
    client = BrevoClient(api_key=api_key)
    return client.sync_contacts(contacts, list_name=list_name)


# Test
if __name__ == "__main__":
    # Verify API connection
    try:
        client = BrevoClient()
        info = client.get_account_info()
        print(f"Connected to Brevo as: {info['email']}")
        print(f"Account: {info['first_name']} {info['last_name']}")
        print(f"Company: {info['company_name']}")
    except Exception as e:
        print(f"Error: {e}")
        print("Set BREVO_API_KEY environment variable to test")
