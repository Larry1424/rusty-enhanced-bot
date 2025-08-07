from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime
import openai
import os
import logging
import json
import re
from enhanced_memory_manager import EnhancedMemoryManager
from conversation_flow_engine import ConversationFlowEngine

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
PUBLIC_URL = os.getenv("PUBLIC_URL", "https://yourdomain.com")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("SESSION_SECRET", "something-very-secret")

# Initialize Enhanced Systems
memory_manager = EnhancedMemoryManager(
    database_url=os.getenv("DATABASE_URL"),
    max_interactions=15,
    expiry_days=90
)

flow_engine = ConversationFlowEngine()

# Enhanced System Prompt with Philosophy Integration
SYSTEM_PROMPT = """
You are a helpful, conversational guide for Country Leisure — a family-run pool and spa company in Oklahoma.

We specialize in cocktail pools — compact, elegant inground pools designed for relaxation, entertaining, and stylish backyard retreats. These pools become the gathering place where families create lasting memories.

Your tone is confident, relaxed, and human — like Rusty chatting with a neighbor. You're here to help people explore their options, answer questions clearly, and offer helpful ideas without being pushy.

IMPORTANT: You are trained by Rusty, a Master CBP (Certified Building Professional) with over two decades of experience. Mention this when quality, experience, or credentials come up.

---

Key Info to Know (Use Naturally):

PRICING:
- 12' x 24' Cocktail Pool: $65,000
- 14' x 28' Cocktail Pool: $74,000  
  > Both include: 6x24-inch tile, concrete coping, 3-foot deck, quartz plaster, lighting package, and WiFi pump for phone control.

- Tanning ledge: ~$2,400  
- Wraparound bench: ~$1,500  

- Install timeline: 75-90 days depending on site and weather  
- Semi-inground pools: Start around $40,000  
- Custom inground pools: Start at $850 per perimeter foot (premium finishes up to $1,100)

PROCESS OVERVIEW:
1. **Site Readiness & Permits:** Outdoor electrical and water access required. We handle all permits and inspections.
2. **Site Preparation:** Excavation, leveling, plumbing, electrical. $5,000 contingency covers rock/groundwater issues (mention only if asked).
3. **Pool Installation:** 75-90 days total. PHTA GENESIS® Certified Master Pool Builder standards.
4. **Final Touches:** Personal pool school walkthrough included.

DESIGN PHILOSOPHY (Rusty's Approach):
- **Purpose-Driven Design:** Every element serves a function — relaxation, entertainment, or space enhancement
- **Clean Geometry:** Simple, modern lines that complement the home and landscape
- **Water as the Feature:** Clean, reflective, minimal — let the water be the centerpiece
- **Lighting = Mood:** Underwater lighting transforms the pool into a showpiece at night
- **Materials That Last:** Concrete coping and quality tile that withstand Oklahoma weather
- **Minimalism + Comfort:** Simple luxury with purposeful upgrades like tanning ledges and benches

---

Conversation Style:

You're not scripted. You respond like a real person would.

- Keep the tone easygoing, conversational, and confident
- Guide people with helpful ideas — not pushy advice  
- Vary your language — never repeat the same phrasing
- Build on previous conversation context naturally
- Ask thoughtful follow-up questions about lifestyle, space, priorities, or vision
- Never sound robotic — keep it flowing and natural

VOICE EXAMPLES (use variations):
- "Some folks enjoy..."  
- "Totally optional, but..."  
- "A lot of people love the simplicity of..."  
- "If your space is a little tricky, no worries — we've seen it all."

BUDGET CONVERSATIONS:
If price feels high: "Totally understand — we also offer semi-inground pools starting around $40,000. Great way to get that backyard pool feel with a more approachable budget."

QUALITY DISCUSSIONS:
Emphasize materials that last: "We stick with materials that hold up — concrete coping and solid tile so you're not redoing things in a few years."

GATHERING PLACE MESSAGING:
Emphasize: "These pools become where your family naturally gathers — kids, grandkids, friends. It's about creating that space where memories happen."

---

CONVERSATION FLOW INTELLIGENCE:

READ THE CONVERSATION CONTEXT provided in each message. Use this to:
- Avoid repeating questions you've already asked
- Reference their specific interests naturally
- Progress the conversation based on their engagement level
- Recognize when they might be ready for next steps

NEVER:
- Ask the same follow-up questions repeatedly
- Ignore previous conversation context
- Use the exact same phrases in multiple responses
- Sound like you're reading from a script

ALWAYS:
- Build on what you already know about them
- Vary your language naturally
- Keep the conversation moving forward
- Stay authentic to Rusty's expertise and philosophy

The customer's journey should feel natural and progressive, not repetitive or pushy.
"""

def get_or_create_user_id():
    """Get user ID from session or create a new one"""
    if "user_id" not in session:
        session["user_id"] = memory_manager._generate_user_id()
        logger.info(f"Created new session for user: {session['user_id']}")
    return session["user_id"]

def build_message_history(memory, user_message, context_summary, opening_message=None):
    """Build the complete message history for the API call"""
    message_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Add context summary if available
    if context_summary:
        message_history.append({
            "role": "system", 
            "content": context_summary
        })
    
    # Add opening message for returning users
    if opening_message:
        message_history.append({
            "role": "assistant",
            "content": opening_message
        })
    
    # Add recent conversation history (last 10 interactions)
    conversation_history = memory_manager.get_conversation_history(memory, limit=10)
    message_history.extend(conversation_history)
    
    # Add the current user message
    message_history.append({"role": "user", "content": user_message})
    
    return message_history

def process_contact_info(user_message, memory):
    """Extract contact information from user message"""
    contact_info = memory.get("contact_info", {})
    message_lower = user_message.lower()
    
    # Email detection
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, user_message)
    if emails and not contact_info.get("email"):
        memory_manager.update_contact_info(memory, "email", emails[0])
        logger.info(f"Extracted email: {emails[0]}")
    
    # Phone detection
    phone_pattern = r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})'
    phones = re.findall(phone_pattern, user_message)
    if phones and not contact_info.get("phone"):
        memory_manager.update_contact_info(memory, "phone", phones[0])
        logger.info(f"Extracted phone: {phones[0]}")
    
    # Name detection (if message starts with name-like pattern)
    if not contact_info.get("name"):
        # Look for "I'm [Name]" or "My name is [Name]" patterns
        name_patterns = [
            r"i'?m\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)",
            r"my name is\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)",
            r"name'?s\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)",
            r"call me\s+([a-zA-Z]+)"
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, message_lower)
            if match:
                name = match.group(1).title()
                memory_manager.update_contact_info(memory, "name", name)
                logger.info(f"Extracted name: {name}")
                break
    
    # Photo detection
    if "photo" in message_lower or "picture" in message_lower or "image" in message_lower:
        if "sent" in message_lower or "attached" in message_lower or "here" in message_lower:
            memory_manager.update_contact_info(memory, "photo", "provided")
            logger.info("Photo indicated as provided")

def get_missing_contact_fields(memory):
    """Get list of missing contact information fields"""
    contact_info = memory.get("contact_info", {})
    required_fields = ["name", "email", "phone", "photo"]
    return [field for field in required_fields if not contact_info.get(field)]

def handle_render_workflow(memory, user_message, bot_response):
    """Handle render request workflow"""
    render_stage = memory_manager.get_render_workflow_stage(memory)
    
    if render_stage == "info_needed":
        # User just agreed to render, collect info
        contact_message = flow_engine.get_contact_collection_message([])
        bot_response += f" {contact_message}"
        
        # Add timeline expectation
        timeline_message = flow_engine.generate_render_timeline_message()
        bot_response += f" {timeline_message}"
        
    elif render_stage == "collecting_info":
        # Process any contact info in the message
        process_contact_info(user_message, memory)
        
        # Check what's still missing
        missing_fields = get_missing_contact_fields(memory)
        
        if missing_fields:
            if len(missing_fields) <= 2 and flow_engine.should_offer_partial_info(memory):
                # Offer partial collection
                partial_offer = flow_engine.get_partial_info_offer()
                bot_response += f" {partial_offer}"
            else:
                # Request missing fields
                missing_message = flow_engine.get_contact_collection_message(missing_fields)
                bot_response += f" {missing_message}"
                
                # Add soft reassurance
                if len(missing_fields) >= 3:
                    soft_approach = flow_engine.get_soft_contact_approach(memory)
                    bot_response += f" {soft_approach}"
        else:
            # All info collected
            memory["render_status"] = "complete"
            bot_response += " Perfect! I've got everything I need. We'll get started on your render and have it ready in 2-3 business days."
    
    return bot_response

def log_conversation(user_id, user_message, bot_response, memory_context=""):
    """Enhanced conversation logging"""
    try:
        log_dir = "/mnt/conversations"
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_path = os.path.join(log_dir, f"{timestamp}_{user_id}.txt")

        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write("=== ENHANCED CONVERSATION LOG ===\n")
            log_file.write(f"Timestamp: {timestamp}\n")
            log_file.write(f"User ID: {user_id}\n")
            log_file.write(f"User: {user_message}\n")
            log_file.write(f"Bot: {bot_response}\n")
            if memory_context:
                log_file.write(f"Context: {memory_context}\n")
            log_file.write("\n" + "="*50 + "\n\n")
            
        logger.info(f"Enhanced log created for user {user_id}")
    except Exception as e:
        logger.error(f"Error logging conversation: {e}")

@app.route("/cta-test/<user_id>", methods=["POST"])
def test_cta_logic(user_id):
    """Test CTA logic for a specific user (development endpoint)"""
    try:
        memory = memory_manager.load_memory(user_id)
        should_cta, cta_type = memory_manager.should_attempt_cta(memory)
        
        result = {
            "user_id": user_id,
            "should_attempt_cta": should_cta,
            "cta_type": cta_type,
            "buyer_stage": memory.get("buyer_stage"),
            "engagement_level": memory.get("engagement_level"),
            "last_cta_attempt": memory.get("last_cta_attempt"),
            "cta_attempts_count": len(memory.get("cta_attempts", []))
        }
        
        if should_cta:
            cta_message = flow_engine.get_cta_message(memory, cta_type)
            result["sample_cta_message"] = cta_message
            
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/simulate-response", methods=["POST"])
def simulate_response():
    """Simulate user response to CTA (development endpoint)"""
    try:
        data = request.json
        user_id = data.get("user_id")
        cta_type = data.get("cta_type", "consult")
        response = data.get("response", "not yet")
        
        memory = memory_manager.load_memory(user_id)
        memory_manager.record_cta_attempt(memory, cta_type, response)
        memory_manager.save_memory(memory)
        
        return jsonify({
            "message": f"Recorded {cta_type} CTA response: {response}",
            "updated_stage": memory.get("buyer_stage"),
            "render_requested": memory.get("render_requested")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/cleanup", methods=["POST"])
def cleanup_memories():
    """Endpoint to clean up expired memories"""
    try:
        cleaned = memory_manager.cleanup_expired_memories()
        return jsonify({
            "message": f"Cleaned up {cleaned} expired memory records",
            "cleaned_count": cleaned
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/reset/<user_id>", methods=["POST"])
def reset_user_memory(user_id):
    """Reset specific user's memory (useful for testing)"""
    try:
        # Clear from database
        with memory_manager._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM user_memories WHERE user_id = %s", (user_id,))
                conn.commit()
        
        # Clear session if it's the current user
        if session.get("user_id") == user_id:
            session.clear()
            
        return jsonify({"message": f"Memory reset for user {user_id}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/conversation-stats", methods=["GET"])
def get_conversation_stats():
    """Get overall conversation statistics"""
    try:
        with memory_manager._get_connection() as conn:
            with conn.cursor() as cur:
                # Total users
                cur.execute("SELECT COUNT(*) FROM user_memories")
                total_users = cur.fetchone()[0]
                
                # Users by stage
                cur.execute("""
                    SELECT buyer_stage, COUNT(*) 
                    FROM user_memories 
                    GROUP BY buyer_stage
                """)
                stages = dict(cur.fetchall())
                
                # Render requests
                cur.execute("SELECT COUNT(*) FROM user_memories WHERE render_requested = true")
                render_requests = cur.fetchone()[0]
                
                # Active users (last 7 days)
                cur.execute("""
                    SELECT COUNT(*) FROM user_memories 
                    WHERE last_updated > NOW() - INTERVAL '7 days'
                """)
                active_users = cur.fetchone()[0]
                
                return jsonify({
                    "total_users": total_users,
                    "active_users_7days": active_users,
                    "render_requests": render_requests,
                    "buyer_stages": stages,
                    "timestamp": datetime.now().isoformat()
                })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/export-renders", methods=["GET"])
def export_render_requests():
    """Export render requests for processing"""
    try:
        with memory_manager._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, contact_info, key_facts, render_details, 
                           created_at, last_updated
                    FROM user_memories 
                    WHERE render_requested = true 
                    AND render_status = 'complete'
                    ORDER BY last_updated DESC
                """)
                
                renders = []
                for row in cur.fetchall():
                    contact_info = json.loads(row[1]) if row[1] else {}
                    key_facts = json.loads(row[2]) if row[2] else {}
                    render_details = json.loads(row[3]) if row[3] else {}
                    
                    renders.append({
                        "user_id": row[0],
                        "name": contact_info.get("name", ""),
                        "email": contact_info.get("email", ""),
                        "phone": contact_info.get("phone", ""),
                        "photo_provided": bool(contact_info.get("photo")),
                        "preferred_size": key_facts.get("preferred_size", ""),
                        "focus": key_facts.get("focus", ""),
                        "features": key_facts.get("features", []),
                        "budget_conscious": key_facts.get("budget_conscious", False),
                        "created_at": row[4].isoformat() if row[4] else "",
                        "last_updated": row[5].isoformat() if row[5] else ""
                    })
                
                return jsonify({
                    "render_requests": renders,
                    "count": len(renders),
                    "exported_at": datetime.now().isoformat()
                })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/gallery/<filename>")
def gallery_image(filename):
    """Serve gallery images"""
    return send_from_directory("static/pool_images", filename)

@app.route("/ping", methods=["GET"])
def ping():
    """Enhanced health check endpoint"""
    try:
        # Test database connection
        with memory_manager._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return jsonify({
        "status": "ok",
        "enhanced_memory_manager": "active",
        "conversation_flow_engine": "active", 
        "database_status": db_status,
        "timestamp": datetime.now().isoformat()
    })

# Optional: Cleanup expired memories on startup
@app.before_first_request
def startup_cleanup():
    """Enhanced startup tasks"""
    try:
        # Cleanup expired memories
        cleaned = memory_manager.cleanup_expired_memories()
        if cleaned > 0:
            logger.info(f"Startup cleanup: removed {cleaned} expired memory records")
        
        # Log system initialization
        logger.info("Enhanced Rusty chatbot initialized successfully")
        logger.info(f"Memory expiry: {memory_manager.expiry_days} days")
        logger.info(f"Max interactions per user: {memory_manager.max_interactions}")
        
    except Exception as e:
        logger.error(f"Error during startup cleanup: {e}")

if __name__ == "__main__":
    app.run(debug=True).route("/chat", methods=["POST"])
def chat():
    """Enhanced chat endpoint with full conversation intelligence"""
    try:
        user_message = request.json.get("message", "")
        if not user_message.strip():
            return jsonify({"error": "Empty message"}), 400
            
        # Get or create user ID
        user_id = get_or_create_user_id()
        
        # Load user memory
        memory = memory_manager.load_memory(user_id)
        logger.info(f"Processing message for user {user_id} - Stage: {memory.get('buyer_stage')}, Engagement: {memory.get('engagement_level')}")
        
        # Check for returning user opening message
        opening_message = None
        if len(memory.get("interactions", [])) > 2:
            opening_message = flow_engine.get_opening_message(memory)
        
        # Build conversation context summary
        context_summary = memory_manager.build_context_summary(memory)
        
        # Build complete message history for API
        message_history = build_message_history(memory, user_message, context_summary, opening_message)
        
        # Log memory state for debugging
        logger.info(f"User {user_id} context: {context_summary[:150]}...")
        
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=message_history,
            temperature=0.7,
            max_tokens=800
        )
        
        bot_response = response.choices[0].message["content"]
        
        # Process the response with conversation intelligence
        
        # 1. Add credibility if needed
        if flow_engine.should_add_credibility(user_message, memory):
            credibility = flow_engine.get_credibility_statement()
            bot_response += f" {credibility}"
        
        # 2. Integrate design philosophy
        bot_response = flow_engine.enhance_response_with_philosophy(bot_response, memory)
        
        # 3. Handle render workflow if active
        if memory.get("render_requested") or "render" in user_message.lower() or "visual" in user_message.lower():
            bot_response = handle_render_workflow(memory, user_message, bot_response)
        
        # 4. Check for CTA opportunities
        should_cta, cta_type = memory_manager.should_attempt_cta(memory)
        if should_cta and "render" not in bot_response.lower() and "consult" not in bot_response.lower():
            cta_message = flow_engine.get_cta_message(memory, cta_type)
            bot_response += f"\n\n{cta_message}"
            
            # Record CTA attempt (will be updated based on user response)
            memory_manager.record_cta_attempt(memory, cta_type, "pending")
        
        # 5. Detect conversation stalls and restart if needed
        if flow_engine.detect_conversation_stall(memory):
            restart_message = flow_engine.get_conversation_restart(memory)
            bot_response = restart_message
        
        # 6. Add intelligent follow-up if appropriate
        follow_up = flow_engine.get_intelligent_followup(memory, bot_response)
        if follow_up and not bot_response.endswith("?") and "render" not in bot_response.lower():
            bot_response += f" {follow_up}"
        
        # Add interaction to memory
        memory_manager.add_interaction(memory, user_message, bot_response)
        
        # Save updated memory
        memory_manager.save_memory(memory)
        
        # Enhanced logging
        log_conversation(user_id, user_message, bot_response, context_summary)
        
        # Return response with enhanced metadata
        return jsonify({
            "reply": bot_response,
            "user_id": user_id,
            "buyer_stage": memory.get("buyer_stage"),
            "engagement_level": memory.get("engagement_level"),
            "render_status": memory_manager.get_render_workflow_stage(memory)
        })
        
    except openai.error.OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        return jsonify({"error": "Sorry, I'm having trouble connecting right now. Please try again."}), 500
    except Exception as e:
        logger.error(f"Unexpected error in chat: {e}")
        return jsonify({"error": "Something went wrong. Please try again."}), 500

@app.route("/memory/<user_id>", methods=["GET"])
def get_user_memory(user_id):
    """Debug endpoint to view comprehensive user memory"""
    try:
        stats = memory_manager.get_user_stats(user_id)
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/render-status/<user_id>", methods=["GET"])
def get_render_status(user_id):
    """Get render workflow status for a user"""
    try:
        memory = memory_manager.load_memory(user_id)
        render_stage = memory_manager.get_render_workflow_stage(memory)
        missing_fields = get_missing_contact_fields(memory)
        
        return jsonify({
            "user_id": user_id,
            "render_requested": memory.get("render_requested", False),
            "render_stage": render_stage,
            "contact_info": memory.get("contact_info", {}),
            "missing_fields": missing_fields,
            "render_details": memory.get("render_details", {})
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Triggering redeploy after fixing syntax error
