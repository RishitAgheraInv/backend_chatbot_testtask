from sqlalchemy.orm import Session
from sqlalchemy import desc
from models import User, Conversation, Message
from schemas import UserCreate, ConversationCreate, MessageCreate
from typing import Optional, List


class UserCRUD:
    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:
        db_user = User(username=user.username, email=user.email)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()

    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()


class ConversationCRUD:
    @staticmethod
    def create_conversation(db: Session, user_id: int, title: Optional[str] = None) -> Conversation:
        db_conversation = Conversation(user_id=user_id, title=title)
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
        return db_conversation

    @staticmethod
    def get_conversation(db: Session, conversation_id: int) -> Optional[Conversation]:
        return db.query(Conversation).filter(Conversation.id == conversation_id).first()

    @staticmethod
    def get_user_conversations(db: Session, user_id: int) -> List[Conversation]:
        return db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(desc(Conversation.updated_at)).all()


class MessageCRUD:
    @staticmethod
    def create_message(db: Session, conversation_id: int, role: str, content: str) -> Message:
        db_message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content
        )
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        return db_message

    @staticmethod
    def get_conversation_messages(db: Session, conversation_id: int) -> List[Message]:
        return db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).all()

    @staticmethod
    def get_messages_as_dict(db: Session, conversation_id: int) -> List[dict]:
        messages = MessageCRUD.get_conversation_messages(db, conversation_id)
        return [{"role": msg.role, "content": msg.content} for msg in messages]