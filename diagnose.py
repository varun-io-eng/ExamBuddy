"""
DIAGNOSTIC SCRIPT - Check Why Analytics is Not Working
Run this script to diagnose the issue: python diagnose.py
"""

import sqlite3
import sys

print("=" * 60)
print("🔍 EXAM BUDDY ANALYTICS DIAGNOSTIC TOOL")
print("=" * 60)

# Connect to database
try:
    conn = sqlite3.connect('exam_buddy_pro.db')
    cursor = conn.cursor()
    print("✅ Database connected successfully")
except Exception as e:
    print(f"❌ Cannot connect to database: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("📊 DATABASE TABLES CHECK")
print("=" * 60)

# Check if tables exist
tables = ['users', 'attempts', 'knowledge_nodes', 'exams']
for table in tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"✅ {table}: {count} records")
    except Exception as e:
        print(f"❌ {table}: Table missing or error - {e}")

print("\n" + "=" * 60)
print("👤 USERS CHECK")
print("=" * 60)

# List all users
cursor.execute("SELECT user_id, username, created_at FROM users")
users = cursor.fetchall()

if users:
    print(f"Found {len(users)} user(s):")
    for user_id, username, created_at in users:
        print(f"  • {username} (ID: {user_id}) - Created: {created_at}")
else:
    print("⚠️ No users found in database")

print("\n" + "=" * 60)
print("📝 EXAMS CHECK")
print("=" * 60)

# Check exams taken
cursor.execute("""
    SELECT user_id, exam_name, total_questions, score, percentage, timestamp
    FROM exams
    ORDER BY timestamp DESC
    LIMIT 10
""")
exams = cursor.fetchall()

if exams:
    print(f"Found {len(exams)} recent exam(s):")
    for user_id, name, total, score, pct, ts in exams:
        print(f"  • {name}: {score} points ({pct:.1f}%) - {total} questions - {ts}")
else:
    print("⚠️ No exams found")

print("\n" + "=" * 60)
print("🎯 ATTEMPTS CHECK (CRITICAL FOR ANALYTICS)")
print("=" * 60)

# Check attempts
cursor.execute("SELECT COUNT(*) FROM attempts")
total_attempts = cursor.fetchone()[0]

if total_attempts > 0:
    print(f"✅ Total attempts: {total_attempts}")
    
    # Check attempts per user
    cursor.execute("""
        SELECT user_id, COUNT(*) as count
        FROM attempts
        GROUP BY user_id
    """)
    attempts_by_user = cursor.fetchall()
    
    print("\nAttempts by user:")
    for user_id, count in attempts_by_user:
        print(f"  • User {user_id}: {count} attempts")
    
    # Show recent attempts
    cursor.execute("""
        SELECT user_id, question, is_correct, difficulty, timestamp
        FROM attempts
        ORDER BY timestamp DESC
        LIMIT 5
    """)
    recent = cursor.fetchall()
    
    print("\nRecent attempts:")
    for user_id, q, correct, diff, ts in recent:
        status = "✅" if correct else "❌"
        print(f"  {status} [{diff}] {q[:60]}... - {ts}")
else:
    print("❌ NO ATTEMPTS FOUND - This is the problem!")
    print("\n⚠️ ANALYTICS REQUIRES INDIVIDUAL QUESTION ATTEMPTS")
    print("The exam was recorded but individual questions were NOT saved.")

print("\n" + "=" * 60)
print("🧩 KNOWLEDGE NODES CHECK")
print("=" * 60)

# Check knowledge nodes
cursor.execute("SELECT COUNT(*) FROM knowledge_nodes")
total_nodes = cursor.fetchone()[0]

if total_nodes > 0:
    print(f"✅ Total knowledge nodes: {total_nodes}")
    
    cursor.execute("""
        SELECT subject, topic, practice_count
        FROM knowledge_nodes
        ORDER BY practice_count DESC
        LIMIT 10
    """)
    nodes = cursor.fetchall()
    
    print("\nTop practiced topics:")
    for subject, topic, count in nodes:
        print(f"  • {subject} - {topic}: {count} practices")
else:
    print("⚠️ No knowledge nodes created")

print("\n" + "=" * 60)
print("🔗 ATTEMPTS WITH KNOWLEDGE NODES CHECK")
print("=" * 60)

# Check if attempts are linked to knowledge nodes
cursor.execute("""
    SELECT COUNT(*)
    FROM attempts a
    JOIN knowledge_nodes kn ON a.node_id = kn.node_id
""")
linked_attempts = cursor.fetchone()[0]

print(f"Attempts with valid knowledge node links: {linked_attempts}")

if linked_attempts == 0 and total_attempts > 0:
    print("⚠️ WARNING: Attempts exist but are NOT linked to knowledge nodes!")
    print("This will prevent analytics from working.")

print("\n" + "=" * 60)
print("🎯 DIAGNOSIS SUMMARY")
print("=" * 60)

issues = []
fixes = []

if total_attempts == 0:
    issues.append("❌ NO QUESTION ATTEMPTS SAVED")
    fixes.append("The save_question_attempts_to_db() function is not being called or is failing")
    fixes.append("Solution: Make sure you replaced app.py with the modified version")

if total_attempts > 0 and linked_attempts == 0:
    issues.append("❌ ATTEMPTS NOT LINKED TO KNOWLEDGE NODES")
    fixes.append("The get_or_create_node() function might be failing")
    fixes.append("Solution: Check if database.py has get_or_create_node() method at line 183")

if total_nodes == 0 and total_attempts > 0:
    issues.append("⚠️ NO KNOWLEDGE NODES CREATED")
    fixes.append("Knowledge nodes should be created when saving attempts")

if len(issues) == 0:
    print("✅ Everything looks good! Analytics should be working.")
    print("\nIf analytics still shows 'no data':")
    print("  1. Make sure you're logged in as the same user who took the exam")
    print("  2. Refresh the page (Ctrl+R)")
    print("  3. Check if user_id matches between attempts and current session")
else:
    print("ISSUES FOUND:")
    for issue in issues:
        print(f"  {issue}")
    
    print("\nRECOMMENDED FIXES:")
    for i, fix in enumerate(fixes, 1):
        print(f"  {i}. {fix}")

print("\n" + "=" * 60)
print("📋 DETAILED ATTEMPTS DATA (if any)")
print("=" * 60)

if total_attempts > 0:
    cursor.execute("""
        SELECT 
            a.user_id,
            a.question,
            a.user_answer,
            a.correct_answer,
            a.is_correct,
            a.difficulty,
            a.node_id,
            kn.subject,
            kn.topic,
            a.timestamp
        FROM attempts a
        LEFT JOIN knowledge_nodes kn ON a.node_id = kn.node_id
        ORDER BY a.timestamp DESC
        LIMIT 10
    """)
    
    attempts = cursor.fetchall()
    
    if attempts:
        for i, att in enumerate(attempts, 1):
            user_id, q, user_ans, correct_ans, is_correct, diff, node_id, subj, top, ts = att
            status = "✅" if is_correct else "❌"
            node_info = f"{subj}/{top}" if subj else f"Node ID: {node_id}"
            print(f"\n{i}. {status} [{diff}] User: {user_id}")
            print(f"   Q: {q[:80]}...")
            print(f"   Answer: {user_ans} (Correct: {correct_ans})")
            print(f"   Topic: {node_info}")
            print(f"   Time: {ts}")

conn.close()

print("\n" + "=" * 60)
print("✅ Diagnostic complete!")
print("=" * 60)