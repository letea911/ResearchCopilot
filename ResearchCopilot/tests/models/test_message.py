from models.message import Role, ChatMessage


def test_role_enum_values():
    assert Role.SYSTEM == "system"
    assert Role.USER == "user"
    assert Role.ASSISTANT == "assistant"


def test_chatmessage_creation():
    msg = ChatMessage(role=Role.USER, content="Hello")
    assert msg.role == Role.USER
    assert msg.content == "Hello"
    assert msg.metadata == {}


def test_chatmessage_with_metadata():
    msg = ChatMessage(
        role=Role.ASSISTANT,
        content="The answer is 42.",
        metadata={"citations": ["doc_1"]},
    )
    assert msg.metadata["citations"] == ["doc_1"]


def test_chatmessage_equality():
    a = ChatMessage(role=Role.USER, content="Hi")
    b = ChatMessage(role=Role.USER, content="Hi")
    assert a == b
