"""
Enhanced Memory Manager with Buyer Journey Intelligence
=====================================================

Database-based memory system with smart conversation flow detection,
render tracking, and progressive engagement logic.
"""

import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import re

logger = logging.getLogger(__name__)

class EnhancedMemoryManager:
    def __init__(self, database_url: str = None, max_interactions: int = 15, expiry_days: int = 90):
        """
        Initialize Enhanced Memory Manager with buyer journey intelligence
        
        Args:
            database_url: PostgreSQL connection URL
            max_interactions: Maximum interactions to keep per user
            expiry_days: Days after which user memory expires
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.max_interactions = max_interactions
        self.expiry_days = expiry_days
        
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
            
        self._init_database()
        logger.info("EnhancedMemoryManager initialized successfully")

    def _get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.database_url)

    def _init_database(self):
        """Create necessary database tables"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Enhanced user_memories table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS user_memories (
                            user_id VARCHAR(50) PRIMARY KEY,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            interactions JSONB DEFAULT '[]',
                            key_facts JSONB DEFAULT '{}',
                            conversation_summary TEXT DEFAULT '',
                            preferences JSONB DEFAULT '{}',
                            buyer_stage VARCHAR(50) DEFAULT 'browsing',
                            engagement_level INT DEFAULT 1,
                            render_requested BOOLEAN DEFAULT FALSE,
                            render_status VARCHAR(50) DEFAULT NULL,
                            render_details JSONB DEFAULT '{}',
                            contact_info JSONB DEFAULT '{}',
                            cta_attempts JSONB DEFAULT '[]',
                            last_cta_attempt TIMESTAMP DEFAULT NULL
                        )
                    """)
                    
                    # Create indexes
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_user_memories_last_updated 
                        ON user_memories(last_updated)
                    """)
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_user_memories_buyer_stage 
                        ON user_memories(buyer_stage)
                    """)
                    
                conn.commit()
                logger.info("Enhanced database tables initialized")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def _generate_user_id(self) -> str:
        """Generate a unique user ID"""
        return str(uuid.uuid4())[:8]

    def load_memory(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Load enhanced user memory from database"""
        if not user_id:
            user_id = self._generate_user_id()
            logger.info(f"Generated new user_id: {user_id}")

        default_memory = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "interactions": [],
            "key_facts": {},
            "conversation_summary": "",
            "preferences": {},
            "buyer_stage": "browsing",
            "engagement_level": 1,
            "render_requested": False,
            "render_status": None,
            "render_details": {},
            "contact_info": {},
            "cta_attempts": [],
            "last_cta_attempt": None
        }

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM user_memories WHERE user_id = %s", (user_id,))
                    result = cur.fetchone()
                    
                    if result:
                        # Check if memory has expired
                        if datetime.now() - result['last_updated'] > timedelta(days=self.expiry_days):
                            logger.info(f"Memory expired for user {user_id}")
                            return default_memory
                            
                        memory = dict(result)
                        # Convert datetime objects to ISO strings
                        for key in ['created_at', 'last_updated', 'last_cta_attempt']:
                            if memory[key]:
                                memory[key] = memory[key].isoformat() if isinstance(memory[key], datetime) else memory[key]
                        
                        # Ensure defaults for new fields
                        for key, default_value in default_memory.items():
                            if key not in memory or memory[key] is None:
                                memory[key] = default_value
                                
                        logger.info(f"Loaded memory for user {user_id}: stage={memory.get('buyer_stage')}, engagement={memory.get('engagement_level')}")
                        return memory
                    else:
                        return default_memory
                        
        except Exception as e:
            logger.error(f"Error loading memory for {user_id}: {e}")
            return default_memory

    def save_memory(self, memory: Dict[str, Any]) -> None:
        """Save enhanced user memory to database"""
        user_id = memory.get("user_id")
        if not user_id:
            logger.error("Cannot save memory without user_id")
            return

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO user_memories 
                        (user_id, last_updated, interactions, key_facts, conversation_summary, 
                         preferences, buyer_stage, engagement_level, render_requested, 
                         render_status, render_details, contact_info, cta_attempts, last_cta_attempt)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id) DO UPDATE SET
                            last_updated = EXCLUDED.last_updated,
                            interactions = EXCLUDED.interactions,
                            key_facts = EXCLUDED.key_facts,
                            conversation_summary = EXCLUDED.conversation_summary,
                            preferences = EXCLUDED.preferences,
                            buyer_stage = EXCLUDED.buyer_stage,
                            engagement_level = EXCLUDED.engagement_level,
                            render_requested = EXCLUDED.render_requested,
                            render_status = EXCLUDED.render_status,
                            render_details = EXCLUDED.render_details,
                            contact_info = EXCLUDED.contact_info,
                            cta_attempts = EXCLUDED.cta_attempts,
                            last_cta_attempt = EXCLUDED.last_cta_attempt
                    """, (
                        user_id,
                        datetime.now(),
                        json.dumps(memory.get("interactions", [])),
                        json.dumps(memory.get("key_facts", {})),
                        memory.get("conversation_summary", ""),
                        json.dumps(memory.get("preferences", {})),
                        memory.get("buyer_stage", "browsing"),
                        memory.get("engagement_level", 1),
                        memory.get("render_requested", False),
                        memory.get("render_status"),
                        json.dumps(memory.get("render_details", {})),
                        json.dumps(memory.get("contact_info", {})),
                        json.dumps(memory.get("cta_attempts", [])),
                        datetime.fromisoformat(memory["last_cta_attempt"]) if memory.get("last_cta_attempt") else None
                    ))
                conn.commit()
                logger.info(f"Saved memory for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error saving memory for {user_id}: {e}")

    def add_interaction(self, memory: Dict[str, Any], user_message: str, bot_response: str) -> None:
        """Add interaction and update buyer intelligence"""
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "user": user_message,
            "bot": bot_response
        }
        
        memory["interactions"].append(interaction)
        
        # Prune old interactions
        if len(memory["interactions"]) > self.max_interactions:
            memory["interactions"] = memory["interactions"][-self.max_interactions:]
        
        # Update key facts and buyer intelligence
        self._extract_key_facts(memory, user_message)
        self._update_buyer_stage(memory, user_message)
        self._update_engagement_level(memory, user_message)

    def _extract_key_facts(self, memory: Dict[str, Any], user_message: str) -> None:
        """Extract and update key facts with enhanced detection"""
        message_lower = user_message.lower()
        
        # Pool focus (enhanced detection)
        if any(word in message_lower for word in ["relax", "relaxing", "peaceful", "quiet", "unwind"]):
            memory["key_facts"]["focus"] = "relaxation"
        elif any(word in message_lower for word in ["entertain", "entertaining", "party", "friends", "gather", "host"]):
            memory["key_facts"]["focus"] = "entertaining"
        elif any(word in message_lower for word in ["family", "kids", "children", "grandkids"]):
            memory["key_facts"]["focus"] = "family"
        elif "both" in message_lower and any(word in message_lower for word in ["relax", "entertain"]):
            memory["key_facts"]["focus"] = "both"
            
        # Budget detection (enhanced)
        budget_signals = ["budget", "cost", "price", "expensive", "affordable", "cheap", "financing", "payment"]
        if any(signal in message_lower for signal in budget_signals) or "$" in user_message:
            memory["key_facts"]["budget_conscious"] = True
            
        # Pool type preferences
        if "cocktail pool" in message_lower or "cocktail" in message_lower:
            memory["key_facts"]["pool_type"] = "cocktail"
        elif "semi" in message_lower and "ground" in message_lower:
            memory["key_facts"]["pool_type"] = "semi-inground"
        elif "custom" in message_lower:
            memory["key_facts"]["pool_type"] = "custom"
            
        # Size preferences (enhanced)
        if re.search(r'12\s*x\s*24|12\'?\s*x\s*24\'?|12\s*by\s*24', user_message, re.IGNORECASE):
            memory["key_facts"]["preferred_size"] = "12x24"
        elif re.search(r'14\s*x\s*28|14\'?\s*x\s*28\'?|14\s*by\s*28', user_message, re.IGNORECASE):
            memory["key_facts"]["preferred_size"] = "14x28"
            
        # Features (enhanced detection)
        features = memory["key_facts"].setdefault("features", [])
        feature_map = {
            "tanning ledge": ["tanning ledge", "tanning shelf", "sun shelf", "ledge"],
            "wraparound bench": ["bench", "seating", "wraparound", "built-in seating"],
            "lighting": ["lighting", "lights", "underwater lights", "led"],
            "heating": ["heated", "heating", "heater", "warm", "year-round"],
            "jets": ["jets", "hydrotherapy", "massage", "spa jets"],
            "fountains": ["fountain", "water feature", "bubblers", "spillover"]
        }
        
        for feature_name, keywords in feature_map.items():
            if any(keyword in message_lower for keyword in keywords) and feature_name not in features:
                features.append(feature_name)
        
        # Timeline signals
        timeline_signals = ["timeline", "when", "how long", "schedule", "start", "soon", "ready"]
        if any(signal in message_lower for signal in timeline_signals):
            memory["key_facts"]["timeline_interest"] = True
            
        # Space/yard concerns
        space_signals = ["space", "yard", "backyard", "small", "tight", "fit", "room"]
        if any(signal in message_lower for signal in space_signals):
            memory["key_facts"]["space_concerns"] = True

    def _update_buyer_stage(self, memory: Dict[str, Any], user_message: str) -> None:
        """Update buyer stage based on conversation signals"""
        message_lower = user_message.lower()
        current_stage = memory.get("buyer_stage", "browsing")
        
        # Stage progression signals
        specific_signals = ["size", "cost", "price", "timeline", "process", "how long", "when", "schedule"]
        commitment_signals = ["ready", "interested", "want", "need", "planning", "thinking about"]
        
        if current_stage == "browsing":
            if any(signal in message_lower for signal in specific_signals):
                memory["buyer_stage"] = "interested"
            elif any(signal in message_lower for signal in commitment_signals):
                memory["buyer_stage"] = "interested"
                
        elif current_stage == "interested":
            if any(signal in message_lower for signal in ["timeline", "schedule", "when can", "how soon"]):
                memory["buyer_stage"] = "considering"
            elif len(memory.get("key_facts", {})) >= 3:  # Multiple preferences established
                memory["buyer_stage"] = "considering"
                
        elif current_stage == "considering":
            if any(signal in message_lower for signal in ["ready", "let's do", "schedule", "visit", "consult"]):
                memory["buyer_stage"] = "ready"

    def _update_engagement_level(self, memory: Dict[str, Any], user_message: str) -> None:
        """Update engagement level (1-5) based on conversation depth"""
        message_lower = user_message.lower()
        current_level = memory.get("engagement_level", 1)
        
        # Engagement indicators
        question_count = user_message.count("?")
        specific_terms = len([term for term in ["size", "cost", "feature", "timeline", "process"] if term in message_lower])
        message_length = len(user_message.split())
        
        # Calculate new engagement level
        engagement_score = 0
        engagement_score += min(question_count * 0.5, 1)  # Questions show interest
        engagement_score += min(specific_terms * 0.3, 1)  # Specific terms show focus
        engagement_score += min(message_length / 20, 1)   # Longer messages show engagement
        
        # Update level (gradual increase, can't decrease)
        new_level = min(5, max(current_level, int(current_level + engagement_score)))
        memory["engagement_level"] = new_level

    def should_attempt_cta(self, memory: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Determine if bot should attempt a CTA and what type
        
        Returns:
            (should_attempt, cta_type) where cta_type is 'consult' or 'render'
        """
        buyer_stage = memory.get("buyer_stage", "browsing")
        engagement_level = memory.get("engagement_level", 1)
        last_cta = memory.get("last_cta_attempt")
        cta_attempts = memory.get("cta_attempts", [])
        
        # Don't attempt CTA too frequently
        if last_cta:
            last_cta_time = datetime.fromisoformat(last_cta) if isinstance(last_cta, str) else last_cta
            if datetime.now() - last_cta_time < timedelta(minutes=5):
                return False, None
        
        # Don't attempt if too many recent attempts
        recent_attempts = [attempt for attempt in cta_attempts if 
                          datetime.now() - datetime.fromisoformat(attempt["timestamp"]) < timedelta(hours=1)]
        if len(recent_attempts) >= 2:
            return False, None
        
        # CTA logic based on stage and engagement
        if buyer_stage in ["considering", "ready"] and engagement_level >= 3:
            return True, "consult"
        elif buyer_stage == "interested" and engagement_level >= 2 and memory.get("key_facts", {}).get("space_concerns"):
            return True, "render"
        elif len(memory.get("interactions", [])) >= 4 and engagement_level >= 3:
            return True, "consult"
            
        return False, None

    def record_cta_attempt(self, memory: Dict[str, Any], cta_type: str, response: str) -> None:
        """Record a CTA attempt and user response"""
        attempt = {
            "timestamp": datetime.now().isoformat(),
            "type": cta_type,
            "response": response.lower()
        }
        
        memory["cta_attempts"].append(attempt)
        memory["last_cta_attempt"] = datetime.now().isoformat()
        
        # Update buyer stage based on response
        if "yes" in response.lower() or "sure" in response.lower() or "okay" in response.lower():
            if cta_type == "consult":
                memory["buyer_stage"] = "ready"
            elif cta_type == "render":
                memory["render_requested"] = True
                memory["render_status"] = "info_needed"

    def get_render_workflow_stage(self, memory: Dict[str, Any]) -> str:
        """
        Get current render workflow stage
        
        Returns:
            'not_requested', 'info_needed', 'collecting_info', 'complete', 'in_progress'
        """
        if not memory.get("render_requested"):
            return "not_requested"
            
        contact_info = memory.get("contact_info", {})
        required_fields = ["name", "email", "phone", "photo"]
        
        if memory.get("render_status") == "complete":
            return "complete"
        elif memory.get("render_status") == "in_progress":
            return "in_progress"
        elif all(contact_info.get(field) for field in required_fields):
            return "complete"
        elif any(contact_info.get(field) for field in required_fields):
            return "collecting_info"
        else:
            return "info_needed"

    def update_contact_info(self, memory: Dict[str, Any], field: str, value: str) -> None:
        """Update contact information for render workflow"""
        if "contact_info" not in memory:
            memory["contact_info"] = {}
        memory["contact_info"][field] = value
        
        # Check if workflow is complete
        required_fields = ["name", "email", "phone", "photo"]
        if all(memory["contact_info"].get(field) for field in required_fields):
            memory["render_status"] = "complete"

    def build_context_summary(self, memory: Dict[str, Any]) -> str:
        """Build intelligent context summary for conversation continuity"""
        if not memory.get("key_facts") and not memory.get("interactions"):
            return ""
            
        summary_parts = []
        key_facts = memory.get("key_facts", {})
        buyer_stage = memory.get("buyer_stage", "browsing")
        engagement_level = memory.get("engagement_level", 1)
        
        # Build key facts summary
        if key_facts.get("focus"):
            summary_parts.append(f"they're focused on {key_facts['focus']}")
            
        if key_facts.get("budget_conscious"):
            summary_parts.append("they're budget-conscious")
            
        if key_facts.get("pool_type"):
            summary_parts.append(f"they're interested in {key_facts['pool_type']} pools")
            
        if key_facts.get("preferred_size"):
            summary_parts.append(f"they prefer {key_facts['preferred_size']} size")
            
        if key_facts.get("features"):
            features = ", ".join(key_facts["features"])
            summary_parts.append(f"interested in features: {features}")
        
        # Add buyer stage context
        stage_context = {
            "browsing": "still exploring options",
            "interested": "showing specific interest",
            "considering": "seriously considering a pool",
            "ready": "ready to move forward"
        }
        
        if buyer_stage != "browsing":
            summary_parts.append(stage_context.get(buyer_stage, "engaged"))
        
        # Add render context
        if memory.get("render_requested"):
            render_stage = self.get_render_workflow_stage(memory)
            if render_stage == "in_progress":
                summary_parts.append("waiting for their render")
            elif render_stage == "collecting_info":
                summary_parts.append("providing info for render")
            elif render_stage == "complete":
                summary_parts.append("render info collected")
        
        if summary_parts:
            base_summary = "CONVERSATION CONTEXT: Customer " + ", ".join(summary_parts) + "."
            
            # Add intelligent suggestions
            suggestions = self._get_intelligent_suggestions(memory)
            if suggestions:
                base_summary += f" GUIDANCE: {suggestions}"
                
            return base_summary
            
        return ""

    def _get_intelligent_suggestions(self, memory: Dict[str, Any]) -> str:
        """Generate intelligent conversation guidance based on memory"""
        key_facts = memory.get("key_facts", {})
        buyer_stage = memory.get("buyer_stage", "browsing")
        engagement_level = memory.get("engagement_level", 1)
        
        suggestions = []
        
        # Stage-based suggestions
        if buyer_stage == "browsing" and engagement_level >= 2:
            suggestions.append("ask about their vision for the space")
        elif buyer_stage == "interested":
            if not key_facts.get("preferred_size"):
                suggestions.append("explore size preferences")
            if not key_facts.get("focus"):
                suggestions.append("understand their main use (relaxing vs entertaining)")
        elif buyer_stage == "considering":
            if self.should_attempt_cta(memory)[0]:
                cta_type = self.should_attempt_cta(memory)[1]
                suggestions.append(f"consider {cta_type} CTA")
        
        # Focus-based suggestions
        if key_facts.get("focus") == "entertaining":
            suggestions.extend(["discuss layout for gatherings", "mention lighting importance"])
        elif key_facts.get("focus") == "relaxation":
            suggestions.extend(["emphasize clean lines", "discuss peaceful features"])
        elif key_facts.get("focus") == "family":
            suggestions.extend(["highlight safety features", "discuss kid-friendly elements"])
        
        # Budget-conscious suggestions
        if key_facts.get("budget_conscious"):
            suggestions.append("emphasize value and materials that last")
        
        return ". ".join(suggestions[:3]) if suggestions else ""

    def get_conversation_history(self, memory: Dict[str, Any], limit: int = 10) -> List[Dict[str, str]]:
        """Get formatted conversation history for API calls"""
        interactions = memory.get("interactions", [])[-limit:]
        messages = []
        
        for interaction in interactions:
            messages.append({"role": "user", "content": interaction["user"]})
            messages.append({"role": "assistant", "content": interaction["bot"]})
            
        return messages

    def cleanup_expired_memories(self) -> int:
        """Clean up expired user memory records"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.expiry_days)
            
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM user_memories WHERE last_updated < %s", (cutoff_date,))
                    cleaned = cur.rowcount
                    conn.commit()
                    
                    if cleaned > 0:
                        logger.info(f"Cleaned {cleaned} expired memory records")
                        
                    return cleaned
                    
        except Exception as e:
            logger.error(f"Error cleaning up expired memories: {e}")
            return 0

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics about a user"""
        memory = self.load_memory(user_id)
        
        return {
            "user_id": user_id,
            "total_interactions": len(memory.get("interactions", [])),
            "key_facts": memory.get("key_facts", {}),
            "buyer_stage": memory.get("buyer_stage"),
            "engagement_level": memory.get("engagement_level"),
            "render_requested": memory.get("render_requested"),
            "render_status": memory.get("render_status"),
            "cta_attempts": len(memory.get("cta_attempts", [])),
            "last_active": memory.get("last_updated"),
            "context_summary": self.build_context_summary(memory)
        }