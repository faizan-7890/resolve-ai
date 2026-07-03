import os
import sys
import json
import shutil
import sqlite3
import subprocess
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Override env settings for clean, isolated E2E tests
os.environ["DATABASE_URL"] = "sqlite:///./resolve_ai_test.db"
os.environ["QDRANT_HOST"] = ":memory:"
os.environ["SECRET_KEY"] = "testing-secret-key"

from alembic.config import Config
from alembic import command
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine, Base
from app.models.models import User, Problem, Clarification, Diagnosis, Solution, Task, Memory
from app.services.ai_service import ai_service
from app.services.qdrant_service import qdrant_service
from app.core.security import get_password_hash


def test_docker() -> bool:
    print("\n--- 1. Checking Docker Containers ---")
    try:
        # Check if docker command is available
        res = subprocess.run(["docker", "ps"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            print("[OK] Docker daemon is running and accessible.")
            return True
        else:
            print(f"[ERROR] Docker daemon error: {res.stderr.strip() or res.stdout.strip()}")
            return False
    except Exception as e:
        print(f"[ERROR] Docker daemon not running or not found: {e}")
        return False


def test_migrations() -> bool:
    print("\n--- 2. Applying Database Migrations ---")
    db_file = Path("./resolve_ai_test.db")
    if db_file.exists():
        try:
            db_file.unlink()
        except Exception:
            pass
        
    try:
        alembic_cfg = Config("alembic.ini")
        # Direct override to make sure it runs against our SQLite test DB
        alembic_cfg.set_main_option("sqlalchemy.url", "sqlite:///./resolve_ai_test.db")
        command.upgrade(alembic_cfg, "head")
        print("[OK] Alembic migrations applied successfully to resolve_ai_test.db.")
        return True
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        return False


def test_rag_pipeline() -> bool:
    print("\n--- 3. Testing RAG Pipeline ---")
    db = SessionLocal()
    try:
        # Create test user
        hashed_password = get_password_hash("testpassword")
        user = User(email="test_rag@resolveai.com", password_hash=hashed_password, name="Test RAG User")
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"[OK] Created test user: {user.email} (ID: {user.id})")

        # Step A: Verify Qdrant in-memory collection creation
        print("   - Verifying collection creation...")
        if qdrant_service.is_available:
            print("[OK] Qdrant in-memory client is ready and collection exists.")
        else:
            print("[ERROR] Qdrant client unavailable.")
            return False

        # Step B & C: Submit a resolved problem to vector memory
        print("   - Creating and indexing a solved problem (RAG Source)...")
        past_problem = Problem(
            user_id=user.id,
            title="SaaS User Growth Drop",
            description="Our primary marketing campaigns failed and organic traffic fell 40% last month.",
            category="Business",
            urgency="High",
            status="Resolved"
        )
        db.add(past_problem)
        db.commit()
        db.refresh(past_problem)

        selected_solution = Solution(
            problem_id=past_problem.id,
            title="Content Marketing Pivot",
            strategy_details="Shift budget from paid search to developer-focused content strategy and SEO optimizations.",
            score=8.5,
            impact=9.0,
            confidence=8.0,
            risk=3.0,
            selected=True
        )
        db.add(selected_solution)
        db.commit()

        summary_text = f"Problem: {past_problem.title}. Details: {past_problem.description}"
        sol_summary_text = f"Strategy: {selected_solution.title}. Details: {selected_solution.strategy_details}"
        
        emb = ai_service.get_embedding(summary_text)
        memory = Memory(
            user_id=user.id,
            problem_summary=summary_text,
            solution_summary=sol_summary_text,
            embedding_vector=json.dumps(emb)
        )
        db.add(memory)
        db.flush()

        upsert_ok = qdrant_service.upsert_memory(
            memory_id=memory.id,
            vector=emb,
            user_id=user.id,
            problem_summary=summary_text,
            solution_summary=sol_summary_text
        )
        db.commit()
        
        if upsert_ok:
            print(f"[OK] Upserted memory {memory.id} to Qdrant successfully.")
        else:
            print("[ERROR] Memory upsert failed.")
            return False

        # Step D: Submit new problem and query similar problems
        print("   - Submitting new problem and querying similar cases...")
        new_problem = Problem(
            user_id=user.id,
            title="Low website conversion rates",
            description="Signups are dropping because the homepage marketing messaging is unclear.",
            category="Business",
            urgency="High",
            status="Intake"
        )
        db.add(new_problem)
        db.commit()
        db.refresh(new_problem)

        new_summary = f"Problem: {new_problem.title}. Details: {new_problem.description}"
        new_emb = ai_service.get_embedding(new_summary)
        
        # Query similar resolved cases
        matches = qdrant_service.search_similar(new_emb, user.id, limit=3)
        print(f"[OK] Qdrant search returned {len(matches)} match(es).")
        for match in matches:
            print(f"     Match ID: {match['id']}, Score: {match['similarity']}, Title: {match['problem_summary'][:40]}...")

        if not matches:
            print("[ERROR] Query returned no matches.")
            return False

        # Step E & F: Inject retrieved context into diagnosis prompt and run diagnosis
        print("   - Running diagnosis with RAG context injection...")
        diag_data = ai_service.generate_diagnosis(
            new_problem.title, 
            new_problem.description, 
            q_and_a=[], 
            rag_context=matches
        )
        
        print("[OK] Diagnosis generation successful.")
        print(f"     Root Causes: {diag_data.get('root_causes', [])[:2]}")
        print(f"     SWOT strengths count: {len(diag_data.get('swot_analysis', {}).get('strengths', []))}")
        
        return True

    except Exception as e:
        print(f"[ERROR] RAG pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_fallback() -> bool:
    print("\n--- 4. Testing Fallback Behavior ---")
    db = SessionLocal()
    try:
        # Get user
        user = db.query(User).filter(User.email == "test_rag@resolveai.com").first()
        if not user:
            print("[ERROR] User not found.")
            return False

        # Force disable Qdrant service
        print("   - Stopping Qdrant client (mocking service down)...")
        qdrant_service._available = False

        # Check search similar handles it gracefully
        print("   - Running search similar...")
        query_vector = ai_service.get_embedding("Testing fallback behavior")
        results = qdrant_service.search_similar(query_vector, user.id, limit=3)
        print("[OK] search_similar returned gracefully when Qdrant was disabled.")
        
        # Check diagnosis still works
        print("   - Running diagnosis engine...")
        diag_data = ai_service.generate_diagnosis(
            "SaaS sales dropping",
            "Our subscription revenue is decreasing by 10% month-over-month.",
            q_and_a=[],
            rag_context=results
        )
        print("[OK] Diagnosis runs cleanly without crashing under Qdrant failure.")
        return True
    except Exception as e:
        print(f"[ERROR] Fallback test crashed: {e}")
        return False
    finally:
        db.close()


def clean_up():
    print("\n--- 5. Cleanup ---")
    engine.dispose()  # Release SQLite connection locks
    db_file = Path("./resolve_ai_test.db")
    if db_file.exists():
        try:
            db_file.unlink()
            print("[OK] Deleted test SQLite database.")
        except Exception as e:
            print(f"[WARNING] Could not delete SQLite database: {e}")


if __name__ == "__main__":
    docker_ok = test_docker()
    migrations_ok = test_migrations()
    
    if migrations_ok:
        rag_ok = test_rag_pipeline()
        fallback_ok = test_fallback()
    else:
        rag_ok = False
        fallback_ok = False
        
    clean_up()
    
    print("\n================ VERIFICATION SUMMARY ================")
    print(f"Docker Containers: {'WORKING' if docker_ok else 'FAILED (Error response from daemon)'}")
    print(f"Database Migrations: {'WORKING (SQLite override)' if migrations_ok else 'FAILED'}")
    print(f"Vector Collection Creation: {'WORKING' if (migrations_ok and qdrant_service.is_available) else 'FAILED'}")
    print(f"Full RAG Pipeline (Embed/Upsert/Query/Inject): {'WORKING' if rag_ok else 'FAILED'}")
    print(f"Fallback Behavior: {'WORKING' if fallback_ok else 'FAILED'}")
    print("======================================================")
