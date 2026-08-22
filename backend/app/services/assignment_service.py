import logging
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional
from app.db.tables import Seller, SellerSpecialty, Conversation, ConversationAssignment

logger = logging.getLogger("chatbot-api.services.assignment")

class AssignmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def assign_conversation_to_seller(
        self,
        conversation_id: str,
        specialty_needed: Optional[str] = None,
        sucursal: Optional[str] = None
    ) -> Optional[Seller]:
        """
        Executes atomic assignment of a conversation to a seller based on criteria:
        1. Seller active
        2. Within working hours
        3. Status is 'available'
        4. Below max concurrent chats limit (active_chats < max_chats)
        5. Belongs to sucursal (if specified)
        6. Matches specialty (prioritized)
        7. Least active chats
        8. Oldest last_assigned_at
        Uses row-level database locking (FOR UPDATE) to prevent race conditions.
        """
        logger.info(f"Running seller assignment for conversation {conversation_id} (Specialty needed: {specialty_needed}, Sucursal: {sucursal})")
        
        # Determine current time to filter working hours
        current_time = datetime.datetime.now().time()
        
        # We start a transaction block with SELECT FOR UPDATE on sellers
        # Since we use async pg, we execute a query for available sellers with FOR UPDATE
        try:
            # Query sellers who are active, available, and within working hours
            # To handle time bounds easily: work_start_time <= current_time <= work_end_time
            conditions = [
                Seller.is_active == True,
                Seller.status == "available",
                Seller.active_chats < Seller.max_chats,
                Seller.work_start_time <= current_time,
                Seller.work_end_time >= current_time
            ]
            if sucursal:
                conditions.append(Seller.team_zone == sucursal)

            stmt = (
                select(Seller)
                .where(*conditions)
                .with_for_update()  # PostgreSQL row lock
            )
            res = await self.db.execute(stmt)
            available_sellers = res.scalars().all()
            
            if not available_sellers:
                logger.warning("No sellers currently available for assignment.")
                return None
                
            # Filter and score sellers
            scored_sellers = []
            for seller in available_sellers:
                # Check specialty
                spec_stmt = select(SellerSpecialty.specialty).where(SellerSpecialty.seller_id == seller.id)
                spec_res = await self.db.execute(spec_stmt)
                specs = spec_res.scalars().all()
                
                has_specialty = specialty_needed in specs if specialty_needed else False
                specialty_score = 1 if has_specialty else 0
                
                # We want:
                # 1. Specialty matches first (specialty_score desc)
                # 2. Lowest active_chats (active_chats asc)
                # 3. Oldest last_assigned_at (NULL first, or oldest timestamp asc)
                # 4. Priority (priority desc)
                last_assigned = seller.last_assigned_at or datetime.datetime.min
                
                scored_sellers.append({
                    "seller": seller,
                    "specialty_score": specialty_score,
                    "active_chats": seller.active_chats,
                    "last_assigned": last_assigned,
                    "priority": seller.priority
                })
                
            # Sort sellers based on the rules:
            # - specialty_score (descending, so matches first)
            # - active_chats (ascending, so least load first)
            # - last_assigned (ascending, so oldest assignment first)
            # - priority (descending, higher priority first)
            scored_sellers.sort(
                key=lambda x: (
                    -x["specialty_score"],
                    x["active_chats"],
                    x["last_assigned"],
                    -x["priority"]
                )
            )
            
            selected_seller = scored_sellers[0]["seller"]
            logger.info(f"Seller selected: {selected_seller.name} ({selected_seller.email}) with active chats: {selected_seller.active_chats}")
            
            # Atomic update of seller and conversation inside transaction
            selected_seller.active_chats += 1
            selected_seller.last_assigned_at = datetime.datetime.utcnow()
            
            # Update Conversation status
            conv_stmt = select(Conversation).where(Conversation.id == conversation_id).with_for_update()
            conv_res = await self.db.execute(conv_stmt)
            conversation = conv_res.scalar_one_or_none()
            
            if conversation:
                conversation.status = "assigned"
                conversation.current_seller_id = selected_seller.id
                
            # Log assignment event
            assignment = ConversationAssignment(
                conversation_id=conversation_id,
                seller_id=selected_seller.id,
                status="accepted",  # Auto accepted for standard routing
                assigned_at=datetime.datetime.utcnow()
            )
            self.db.add(assignment)
            await self.db.commit()
            
            return selected_seller
            
        except Exception as e:
            logger.error(f"Error during seller allocation transaction: {str(e)}")
            await self.db.rollback()
            raise
