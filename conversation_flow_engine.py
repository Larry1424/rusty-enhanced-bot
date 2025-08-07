"""
Conversation Flow Engine
=======================

Handles intelligent conversation management, CTA timing, 
phrase variations, and buyer journey progression.
"""

import random
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ConversationFlowEngine:
    def __init__(self):
        """Initialize conversation flow engine with phrase banks"""
        
        # CTA Phrase Variations - Consult
        self.consult_ctas = [
            "Sounds like you're getting close to wanting an in-home consult so we can walk the space and see your vision come together.",
            "I'm thinking it might be time to have someone come out and take a look at your space — we can walk through the possibilities together.",
            "You know what? It sounds like you're ready to have us come take a look at your backyard and talk through the details.",
            "Based on what you're telling me, I think you'd benefit from having one of our team members come out and see the space firsthand.",
            "It feels like we're at the point where seeing your actual space would help us give you better ideas — want to set up a time to walk through it?",
            "I'm getting the sense you're serious about this — maybe it's time to have someone come out and see what we're working with.",
            "Sounds like you've got a good handle on what you want — ready to have us come take a look at your backyard?",
            "I think we've covered enough that it would make sense to have one of our experts come see your space and talk specifics."
        ]
        
        # CTA Phrase Variations - Render Fallback
        self.render_fallback_ctas = [
            "If having someone come out isn't convenient right now, we could sketch up that {specific_item} for you — just need a photo of your backyard.",
            "No worries if you're not ready for a visit yet — we can actually render that {specific_item} you mentioned if you send us a quick photo.",
            "If you want to see it before we schedule anything, we can create a visual of that {specific_item} — just need a pic of your space.",
            "Totally understand if you want to see it first — we can sketch that {specific_item} for your yard if you send a photo.",
            "If a visit feels like too big a step right now, we can render what that {specific_item} would look like in your space.",
            "Want to visualize it first? We can create a concept of that {specific_item} — just need a photo of your backyard.",
            "If you're more comfortable starting with a visual, we can sketch up that {specific_item} for your space."
        ]
        
        # Follow-up Question Variations
        self.followup_variations = [
            "What's drawing you to the idea of a pool?",
            "Tell me about your backyard space situation.",
            "Are you leaning more toward relaxing or entertaining?", 
            "What's your vision for how you'd use the space?",
            "Is this more for family time or having friends over?",
            "How do you picture yourself using it most days?",
            "What got you thinking about pools in the first place?",
            "Any particular features catching your attention?",
            "What's your timeline looking like for this?",
            "Tell me about your outdoor setup right now.",
            "What kind of vibe are you going for back there?",
            "Are you thinking more intimate space or party central?",
            "What would make this pool perfect for your lifestyle?",
            "How do you imagine spending time in your backyard?",
            "What's the main thing you want from a pool?"
        ]
        
        # Re-engagement phrases for returning users
        self.re_engagement_phrases = [
            "Hey! Good to see you back — still thinking about that pool?",
            "Welcome back! How's the pool planning going?", 
            "Hey there! Still exploring pool options?",
            "Good to see you again — any new thoughts on the pool?",
            "Hey! Back for more pool talk?",
            "Welcome back! What's on your mind today?",
            "Hey there! Ready to dive deeper into pool options?"
        ]
        
        # Contact collection variations
        self.contact_collection_phrases = [
            "Perfect! To get that render started, I just need your name, email, phone, and a photo of your backyard.",
            "Great! I'll need a few quick things to create your render: name, email, phone number, and a backyard photo.", 
            "Awesome! For your personalized render, I'll need: your name, email, phone, and a pic of your space.",
            "Sounds good! To make this render specific to your space, I need your name, email, phone, and a backyard photo.",
            "Perfect! Let me get that render process started — I'll need your contact info and a photo of your yard."
        ]
        
        # Design philosophy integration phrases
        self.philosophy_phrases = {
            "purpose_driven": [
                "That {feature} isn't just pretty — it's your {purpose_function}.",
                "Every element should serve a purpose — that {feature} is perfect for {purpose_function}.",
                "I like that thinking — {feature} gives you real {purpose_function}, not just looks."
            ],
            "clean_geometry": [
                "We keep the lines clean and modern — nothing fussy, just elegant.",
                "Simple geometry works best — clean rectangles that complement your space.",
                "I prefer clean, modern lines that don't fight with your home's architecture."
            ],
            "materials_that_last": [
                "We stick with materials that hold up — concrete coping and solid tile so you're not redoing things in a few years.",
                "With Oklahoma weather, we don't cut corners on materials — it just means problems later.",
                "We build it once, right — concrete and quality tile that lasts decades, not years."
            ],
            "lighting_mood": [
                "Underwater lighting is non-negotiable — it turns a simple pool into a showpiece at night.",
                "The lighting completely changes the mood — makes the water almost meditative in the evenings.",
                "That lighting package isn't just for safety — it's what makes the pool stunning after dark."
            ],
            "water_feature": [
                "The water itself should be the star — clean, reflective, and peaceful.",
                "I let the water do the talking — simple, clean, and beautiful.",
                "Water is the feature — everything else just enhances what's naturally beautiful about it."
            ]
        }

    def get_opening_message(self, memory: Dict) -> Optional[str]:
        """Generate appropriate opening message for returning users"""
        interactions = memory.get("interactions", [])
        render_status = memory.get("render_status")
        
        # Handle render follow-up
        if render_status == "in_progress":
            return random.choice([
                "Hey! We're still working on that render you requested — should be ready in the next day or two. Anything change on your end?",
                "Good to see you back! Your render is in progress — we'll have it ready soon. Any new thoughts while you wait?",
                "Hey there! Still working on your visual concept — it's looking good so far. What's on your mind today?"
            ])
        
        # Returning user with history
        if len(interactions) > 2:
            return random.choice(self.re_engagement_phrases)
            
        return None

    def get_cta_message(self, memory: Dict, cta_type: str) -> str:
        """Generate contextual CTA message"""
        key_facts = memory.get("key_facts", {})
        
        if cta_type == "consult":
            # Add context about their interests
            base_cta = random.choice(self.consult_ctas)
            
            # Enhance with their specific interests
            if key_facts.get("focus") == "entertaining":
                base_cta += " We can talk through the layout for your gatherings."
            elif key_facts.get("focus") == "relaxation":
                base_cta += " We can explore how to make it your perfect retreat."
            elif key_facts.get("focus") == "family":
                base_cta += " We can design it with your family's needs in mind."
            
            return base_cta
            
        elif cta_type == "render":
            # Get specific item they mentioned
            specific_item = self._get_specific_render_item(key_facts)
            base_cta = random.choice(self.render_fallback_ctas)
            return base_cta.format(specific_item=specific_item)
            
        return ""

    def _get_specific_render_item(self, key_facts: Dict) -> str:
        """Get specific item to reference in render offer"""
        size = key_facts.get("preferred_size", "cocktail pool")
        features = key_facts.get("features", [])
        
        if size != "cocktail pool" and features:
            return f"{size} pool with {features[0]}"
        elif size != "cocktail pool":
            return f"{size} cocktail pool"
        elif features:
            return f"cocktail pool with {features[0]}"
        else:
            return "cocktail pool setup"

    def get_contact_collection_message(self, missing_fields: List[str]) -> str:
        """Generate message for collecting contact information"""
        if len(missing_fields) == 4:  # All fields missing
            return random.choice(self.contact_collection_phrases)
        
        # Specific field requests
        field_messages = {
            "name": "What name should I put this under?",
            "email": "What's the best email to send the render to?", 
            "phone": "And a phone number in case we need to clarify anything?",
            "photo": "Perfect! Last thing — just need a photo of your backyard space."
        }
        
        if len(missing_fields) == 1:
            return field_messages.get(missing_fields[0], "Just need one more thing!")
        else:
            return f"Great! I still need: {', '.join(missing_fields)}."

    def enhance_response_with_philosophy(self, response: str, memory: Dict) -> str:
        """Integrate Rusty's design philosophy naturally into responses"""
        key_facts = memory.get("key_facts", {})
        
        # Look for opportunities to add philosophy
        response_lower = response.lower()
        
        # Materials discussion
        if any(word in response_lower for word in ["cost", "price", "budget", "materials"]):
            if random.random() < 0.3:  # 30% chance to add philosophy
                philosophy = random.choice(self.philosophy_phrases["materials_that_last"])
                response += f" {philosophy}"
        
        # Feature discussions
        if "lighting" in response_lower:
            if random.random() < 0.4:
                philosophy = random.choice(self.philosophy_phrases["lighting_mood"])
                response += f" {philosophy}"
        
        # Tanning ledge or bench mentions
        if any(feature in response_lower for feature in ["tanning ledge", "bench", "seating"]):
            if random.random() < 0.3:
                focus = key_facts.get("focus", "gathering")
                purpose_function = {
                    "entertaining": "perfect gathering spot",
                    "relaxation": "personal retreat space", 
                    "family": "safe play area",
                    "both": "versatile space"
                }.get(focus, "gathering place")
                
                feature_name = "tanning ledge" if "ledge" in response_lower else "bench seating"
                philosophy = random.choice(self.philosophy_phrases["purpose_driven"])
                philosophy = philosophy.format(feature=feature_name, purpose_function=purpose_function)
                response += f" {philosophy}"
        
        return response

    def get_intelligent_followup(self, memory: Dict, last_response: str) -> Optional[str]:
        """Generate intelligent follow-up questions based on conversation context"""
        key_facts = memory.get("key_facts", {})
        buyer_stage = memory.get("buyer_stage", "browsing")
        interactions_count = len(memory.get("interactions", []))
        
        # Don't add follow-ups to every response
        if random.random() < 0.4:  # 40% chance of follow-up
            return None
        
        # Contextual follow-ups based on what we know
        if buyer_stage == "browsing" and interactions_count <= 3:
            # Early conversation - general exploration
            return random.choice([
                "What's drawing you to cocktail pools specifically?",
                "Tell me about your backyard space.",
                "Are you thinking more relaxing or entertaining?"
            ])
        
        elif buyer_stage == "interested":
            # They're engaged - get specific
            if not key_facts.get("preferred_size"):
                return random.choice([
                    "Are you leaning toward the 12x24 or thinking bigger with the 14x28?",
                    "What size feels right for your space?"
                ])
            elif not key_facts.get("focus"):
                return random.choice([
                    "How do you picture using it most — quiet evenings or having people over?",
                    "Is this more your personal retreat or the family gathering spot?"
                ])
            elif not key_facts.get("features"):
                return random.choice([
                    "Any features catching your eye? Tanning ledge, seating, lighting?",
                    "What would make this pool perfect for your lifestyle?"
                ])
        
        elif buyer_stage == "considering":
            # They're serious - focus on next steps
            if not key_facts.get("timeline_interest"):
                return random.choice([
                    "What's your timeline looking like for this?",
                    "Are you thinking this year or just planning ahead?"
                ])
        
        # Default to varied general follow-ups
        return random.choice(self.followup_variations)

    def should_add_credibility(self, user_message: str, memory: Dict) -> bool:
        """Determine if response should include Rusty's credentials"""
        message_lower = user_message.lower()
        
        # Add credentials when quality/experience is questioned
        quality_signals = [
            "experience", "qualified", "certified", "professional", "expertise", 
            "quality", "trust", "credentials", "builder", "years", "reputation"
        ]
        
        return any(signal in message_lower for signal in quality_signals)

    def get_credibility_statement(self) -> str:
        """Get Rusty's credibility statement"""
        statements = [
            "I should mention — I'm trained by Rusty, who's a Master CBP (Certified Building Professional) with over two decades of pool building experience.",
            "By the way, everything I'm sharing comes from Rusty's expertise — he's a Master Certified Building Professional with 20+ years in the business.",
            "Just so you know, I'm backed by Rusty's 20+ years as a Master CBP — he's built hundreds of pools across Oklahoma.",
            "Worth noting — I'm trained by Rusty, a Master Certified Building Professional who's been perfecting pool designs for over two decades."
        ]
        return random.choice(statements)

    def detect_conversation_stall(self, memory: Dict) -> bool:
        """Detect if conversation has stalled and needs intervention"""
        interactions = memory.get("interactions", [])
        
        if len(interactions) < 3:
            return False
        
        # Look at last few interactions for stall patterns
        recent_interactions = interactions[-3:]
        
        # Check for repeated short responses
        short_responses = [i for i in recent_interactions if len(i.get("user", "").split()) <= 3]
        if len(short_responses) >= 2:
            return True
        
        # Check for circular questions (asking same type of info)
        user_messages = [i.get("user", "").lower() for i in recent_interactions]
        if any(msg.count("?") == 0 for msg in user_messages):  # No questions = less engagement
            return True
        
        return False

    def get_conversation_restart(self, memory: Dict) -> str:
        """Generate conversation restart when stalled"""
        key_facts = memory.get("key_facts", {})
        
        restart_options = [
            "Let me approach this differently — what's the main thing you want to know about cocktail pools?",
            "Maybe I can help narrow this down — what's your biggest question or concern right now?",
            "Tell you what — what would make the biggest difference in helping you decide?",
            "Let me step back — what's the one thing you really need to understand about this process?"
        ]
        
        base_restart = random.choice(restart_options)
        
        # Add context if we know their interests
        if key_facts.get("budget_conscious"):
            base_restart += " Is it mainly about cost and value?"
        elif key_facts.get("space_concerns"):
            base_restart += " Is it about whether it'll work in your space?"
        elif not key_facts:
            base_restart += " I want to make sure I'm giving you the right information."
        
        return base_restart

    def generate_render_timeline_message(self) -> str:
        """Generate render timeline expectation message"""
        messages = [
            "It usually takes about 2 to 3 business days once we have your info and photo.",
            "Takes a couple business days on our side — we build the render manually and check the layout before we send it over.",
            "We'll have it ready in 2-3 business days. We review it internally to make sure it's a pool we'd actually build.",
            "Should be ready within 2-3 business days — we take time to make sure the layout works for your space."
        ]
        return random.choice(messages)

    def get_soft_contact_approach(self, memory: Dict) -> str:
        """Generate soft approach for contact collection"""
        approaches = [
            "The photo helps us design for your space, and the contact info just lets us loop back once the render's ready — we won't spam you.",
            "We keep it simple — just need to know where to send it and how to reach you when it's done.",
            "Contact info is just so we can get it back to you — we're not big on follow-up calls unless you want them.",
            "Just helps us personalize it and get it back to you when it's ready."
        ]
        return random.choice(approaches)

    def should_offer_partial_info(self, memory: Dict) -> bool:
        """Determine if we should offer partial information collection"""
        contact_info = memory.get("contact_info", {})
        
        # If they seem hesitant but engaged
        engagement_level = memory.get("engagement_level", 1)
        return engagement_level >= 2 and len(contact_info) == 0

    def get_partial_info_offer(self) -> str:
        """Generate offer for partial information collection"""
        offers = [
            "No worries — if you're more comfortable just starting with name and email, that works too. We can fill in the rest later.",
            "Want to start simple? Just name and email gets us started — we can grab the rest when you're ready.",
            "Tell you what — just give me your name and email for now. We can sort out the details later."
        ]
        return random.choice(offers)