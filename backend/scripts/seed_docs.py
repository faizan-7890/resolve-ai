import sys
import os
from pathlib import Path

# Ensure the backend directory is in the path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.models.document import Document, DocumentChunk
from app.models.user import User
from app.services.chunking import chunk_text
from app.services.embedding_service import get_embeddings
from app.core.security import get_password_hash

POLICIES = [
    {
        "title": "Refund Policy",
        "content": (
            "Our refund policy allows customers to request a full refund within 30 days of purchase "
            "for standard monthly and annual subscriptions. To qualify, you must submit a refund request "
            "from your registered email address. This refund policy does not apply to custom enterprise contracts, "
            "setup fees, or professional services which are explicitly non-refundable. For any refund request "
            "past the 30-day window, tickets must be escalated to the Billing Manager for exception approval."
        )
    },
    {
        "title": "Subscription and Billing Plans",
        "content": (
            "ResolveAI offers three subscription tiers: 1. Basic Plan at $19/month, which includes access to "
            "standard reasoning pipelines and 100 ticket triages. 2. Pro Plan at $49/month, adding custom RAG datasets "
            "and 1000 ticket triages per month. 3. Enterprise Plan, starting at $299/month, offering dedicated NIM integrations "
            "and unlimited triages. Payments are processed monthly. If a payment fails, we will retry up to 3 times over a "
            "9-day period before suspending account access."
        )
    },
    {
        "title": "Account Cancellation and Suspending",
        "content": (
            "Customers can cancel their subscriptions at any time via the billing portal. Cancellations must be "
            "initiated at least 24 hours prior to the next scheduled billing date to avoid being charged for the next cycle. "
            "Upon cancellation, your access will continue until the end of the current paid billing period. We do not provide "
            "prorated refunds for mid-cycle cancellations. Suspended accounts due to payment failure can be reactivated by "
            "updating the credit card on file."
        )
    },
    {
        "title": "Shipping and Delivery FAQs",
        "content": (
            "We offer standard domestic shipping (3-5 business days) for $5.99, and express shipping (1-2 business days) "
            "for $14.99. Orders above $50 qualify for free standard shipping. International shipping options take 7-14 business days "
            "and cost $25.00 flat rate. All shipments include a tracking number sent via email once processed."
        )
    }
]

def seed():
    db = SessionLocal()
    try:
        # Clear old database records for clean state
        print("Clearing old knowledge base documents...")
        db.query(DocumentChunk).delete()
        db.query(Document).delete()
        db.commit()
        
        # Seed knowledge base
        print("Seeding new knowledge base policies...")
        for policy in POLICIES:
            doc = Document(title=policy["title"], content=policy["content"])
            db.add(doc)
            db.commit()
            db.refresh(doc)
            
            # Chunk the document and generate embeddings
            chunks = chunk_text(policy["content"], chunk_size=300, chunk_overlap=50)
            for chunk_content in chunks:
                emb = get_embeddings(chunk_content)
                db_chunk = DocumentChunk(
                    document_id=doc.id,
                    content=chunk_content,
                    embedding=emb
                )
                db.add(db_chunk)
            db.commit()
            print(f"Ingested policy: '{policy['title']}' with {len(chunks)} chunks.")
            
        # Seed test user accounts
        print("Checking user accounts...")
        admin = db.query(User).filter(User.email == "admin@resolve.ai").first()
        if not admin:
            admin = User(
                email="admin@resolve.ai",
                password_hash=get_password_hash("adminpassword123"),
                name="Admin User",
                role="admin"
            )
            db.add(admin)
            print("Admin user created: admin@resolve.ai / adminpassword123")
            
        test_user = db.query(User).filter(User.email == "test@resolve.ai").first()
        if not test_user:
            test_user = User(
                email="test@resolve.ai",
                password_hash=get_password_hash("testpassword123"),
                name="Test User",
                role="user"
            )
            db.add(test_user)
            print("Test user created: test@resolve.ai / testpassword123")
            
        db.commit()
        print("Seeding completed successfully.")
        
    finally:
        db.close()

if __name__ == "__main__":
    seed()
